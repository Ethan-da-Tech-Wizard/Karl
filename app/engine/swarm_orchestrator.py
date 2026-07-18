"""
Swarm Orchestrator — Karl Workbench
====================================
Coordinates the multi-agent planning, coding, and testing execution loop.
Runs in a background QThread to emit signals to PyQt6 and prevent GUI blocking.
"""

import os
import shlex
import time
import ast
import hashlib
import json
import shutil
import tempfile
import threading
import sys
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
from app.engine.swarm_agents import ArchitectAgent, CoderAgent, TesterAgent
from app.engine.swarm_memory import SwarmMemory
from app.engine.swarm_judge import select_winner
from app.engine.swarm_specialists import (
    classify_task,
    SecurityAuditorAgent,
    PerformanceAuditorAgent,
    CriticAgent,
)
from app.engine.agent_memory import CodebaseMemory
from app.utils.tracing import Span


logger = logging.getLogger("karl.swarm_orchestrator")


def get_python_imports(content: str) -> List[str]:
    """Parse python imports from string content and return a list of module names."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


class SwarmSessionState:
    """The shared Blackboard container holding task queues and results."""
    def __init__(self, workspace_path: str, objective: str, test_command: str):
        self.workspace_path = workspace_path
        self.objective = objective
        self.test_command = test_command
        self.plan: Dict[str, Any] = {}
        self.tasks_status: Dict[str, str] = {}  # filepath -> pending | in_progress | completed | failed
        self.file_diffs: Dict[str, str] = {}
        self.test_runs: List[Dict[str, Any]] = []


def rollback_swarm_run(workspace_path: str, run_id: str | None = None) -> dict:
    """Restore files from a swarm run backup manifest."""
    workspace = Path(workspace_path).expanduser().resolve()
    backup_root = (workspace / ".karl_swarm_backups").resolve()
    if run_id:
        run_dir = (backup_root / run_id).resolve()
    else:
        manifests = sorted(
            backup_root.glob("*/manifest.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not manifests:
            return {"ok": False, "message": "No swarm backup manifests found.", "restored": [], "removed": []}
        run_dir = manifests[0].parent.resolve()

    try:
        run_dir.relative_to(backup_root)
    except ValueError:
        return {"ok": False, "message": "Invalid swarm backup run path.", "restored": [], "removed": []}

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "message": f"No manifest found for swarm run {run_dir.name}.", "restored": [], "removed": []}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored: list[str] = []
    removed: list[str] = []
    for entry in reversed(manifest.get("files", [])):
        relpath = str(entry.get("filepath", "")).replace("\\", "/")
        target = (workspace / relpath).resolve()
        try:
            target.relative_to(workspace)
        except ValueError:
            continue

        if entry.get("existed"):
            backup_path = Path(str(entry.get("backup_path", ""))).resolve()
            try:
                backup_path.relative_to(run_dir)
            except ValueError:
                continue
            if backup_path.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target)
                restored.append(relpath)
        else:
            if target.exists():
                target.unlink()
                removed.append(relpath)

    return {
        "ok": True,
        "run_id": manifest.get("run_id", run_dir.name),
        "restored": restored,
        "removed": removed,
        "message": f"Rolled back swarm run {manifest.get('run_id', run_dir.name)}.",
    }


class SwarmOrchestratorThread(QThread):
    status_update = pyqtSignal(str)              # General log message
    task_plan_created = pyqtSignal(dict)          # The Architect's JSON plan
    dependency_layers_built = pyqtSignal(list)    # list[list[task]]
    layer_started = pyqtSignal(int, int, list)     # layer_index, total_layers, tasks
    layer_finished = pyqtSignal(int, bool, str)    # layer_index, success, summary
    task_status_changed = pyqtSignal(str, str, str)  # filepath, status, detail
    verification_started = pyqtSignal(int, str)    # layer_index, command
    proposal_verification_finished = pyqtSignal(int, bool, str)  # layer_index, passed, trace
    traceback_captured = pyqtSignal(str, str)      # filepath/layer, traceback
    verification_failed = pyqtSignal(str, str)    # context (filepath/layer), full traceback
    edits_proposed = pyqtSignal(list)             # list[{filepath, content}] — awaits commit_selected_edits()
    file_edited = pyqtSignal(str, str)            # filepath, new_content (emitted after write)
    test_result = pyqtSignal(bool, str)           # passed, error_traceback
    finished_swarm = pyqtSignal(bool, str)        # success, final_summary
    coder_token = pyqtSignal(str, str)            # (filepath, token)

    # ── Swarm 2.0 signals ────────────────────────────────────────────────────
    candidates_generated = pyqtSignal(str, int)         # filepath, candidate_count
    candidate_scored = pyqtSignal(str, int, dict)       # filepath, candidate_index, score
    winner_selected = pyqtSignal(str, int, str)         # filepath, winner_index, reason
    memory_recalled = pyqtSignal(str, str)              # filepath, recalled_text
    specialist_review = pyqtSignal(str, str, dict)      # filepath, specialist_name, result
    concurrency_adjusted = pyqtSignal(int, str)         # worker_count, reason
    guidance_injected = pyqtSignal(str, str)            # filepath, message
    cognitive_node = pyqtSignal(dict)                   # structured trace-graph node
    drift_detected = pyqtSignal(str, str)               # filepath, corrective message

    # ── Interactive debugger signals ─────────────────────────────────────────
    swarm_paused = pyqtSignal(dict)                     # task_info awaiting resume()/step()
    telemetry_update = pyqtSignal(dict)                 # {tokens_per_second, cumulative_tokens, elapsed_seconds}

    def __init__(self, workspace_path: str, objective: str, test_command: str, hyperparams: dict = None):
        super().__init__()
        self.state = SwarmSessionState(workspace_path, objective, test_command)
        self.architect = ArchitectAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent(workspace_path)
        self._stop_requested = False

        self._cherry_pick_event = threading.Event()
        self._cherry_pick_selected: list[str] = []

        # ── Swarm 2.0 state ──────────────────────────────────────────────────
        self.memory = SwarmMemory(workspace_path)
        self.candidates_per_task = 1
        self.enable_memory = True
        self.enable_specialists = True
        self.enable_critic = True
        self.adaptive_concurrency = True
        self._guidance_lock = threading.Lock()
        self._guidance: dict[str, list[str]] = {}
        self._task_failure_fps: dict[str, list[str]] = {}
        self._cognition_nodes: list[dict] = []
        self._run_id = str(uuid.uuid4())[:8]
        self._known_names_cache: set[str] = set()
        self._backup_root = Path(workspace_path) / ".karl_swarm_backups" / self._run_id
        self._backup_manifest: list[dict] = []

        # ── Loop control & drift detection ──────────────────────────────────
        self.timeout_seconds = 600
        self.max_loops = 5
        self.auto_steering_enabled = True
        self._run_deadline: float | None = None
        self._drift_history: dict[str, dict[str, str | None]] = {}
        self._plan_filepaths: set[str] = set()

        # ── Interactive debugger: pause/step/resume + live telemetry ────────
        self.pause_on_step = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self._task_overrides: dict[str, str] = {}
        self._telemetry_lock = threading.Lock()
        self._telemetry_start_time: float | None = None
        self._cumulative_tokens = 0

        if hyperparams:
            temp = hyperparams.get("temperature")
            max_tok = hyperparams.get("max_tokens")
            if temp is not None:
                self.architect.temperature = temp
                self.coder.temperature = temp
            if max_tok is not None:
                self.architect.max_tokens = max_tok
                self.coder.max_tokens = max_tok
            self.candidates_per_task = max(1, int(hyperparams.get("candidates_per_task", 1) or 1))
            self.enable_memory = bool(hyperparams.get("enable_memory", True))
            self.enable_specialists = bool(hyperparams.get("enable_specialists", True))
            self.enable_critic = bool(hyperparams.get("enable_critic", True))
            self.adaptive_concurrency = bool(hyperparams.get("adaptive_concurrency", True))
            self.timeout_seconds = max(30, int(hyperparams.get("timeout_seconds", 600) or 600))
            self.max_loops = max(1, int(hyperparams.get("max_loops", 5) or 5))
            self.auto_steering_enabled = bool(hyperparams.get("auto_steering_enabled", True))
            self.pause_on_step = bool(hyperparams.get("pause_on_step", False))

    # ── Live steering ────────────────────────────────────────────────────────

    def inject_guidance(self, filepath: str, message: str) -> None:
        """Queue a human correction to be woven into *filepath*'s next tool-loop
        turn. Safe to call from any thread (e.g. the UI thread or the WS bridge)
        while the orchestrator is mid-run.
        """
        if not filepath or not message or not message.strip():
            return
        with self._guidance_lock:
            self._guidance.setdefault(filepath, []).append(message.strip())
        self.guidance_injected.emit(filepath, message.strip())
        self._emit_cognition("guidance_injected", filepath=filepath, message=message.strip())

    def _drain_guidance(self, filepath: str) -> list[str]:
        with self._guidance_lock:
            return self._guidance.pop(filepath, [])

    # ── Interactive debugger: pause / step / resume ─────────────────────────

    def pause(self) -> None:
        """Enable step-pausing. Takes effect at the next task boundary — an
        in-flight coder generation is not interrupted mid-call."""
        self.pause_on_step = True

    def resume(self) -> None:
        """Disable step-pausing and unblock whatever task is currently waiting,
        so the run proceeds without further pausing."""
        self.pause_on_step = False
        self.pause_event.set()

    def step(self) -> None:
        """Let exactly one more task run, then automatically re-pause at the
        next task boundary (pause_on_step stays enabled)."""
        self.pause_event.set()

    def override_active_task(self, filepath: str, instructions: str) -> None:
        """Queue replacement instructions for *filepath*'s next coder attempt.
        Only takes effect if that task is currently paused awaiting resume()/step()."""
        if not filepath or not instructions or not instructions.strip():
            return
        with self._guidance_lock:
            self._task_overrides[filepath] = instructions.strip()

    def _apply_task_override(self, task: dict) -> dict:
        with self._guidance_lock:
            override = self._task_overrides.pop(task["filepath"], None)
        if not override:
            return task
        task = dict(task)
        task["instructions"] = override
        return task

    # ── Interactive debugger: live token telemetry ──────────────────────────

    def _record_token_telemetry(self) -> None:
        now = time.monotonic()
        with self._telemetry_lock:
            if self._telemetry_start_time is None:
                self._telemetry_start_time = now
            self._cumulative_tokens += 1
            elapsed = max(now - self._telemetry_start_time, 1e-6)
            cumulative = self._cumulative_tokens
            tps = cumulative / elapsed
        # Throttle emission so fast local models don't flood the Qt event queue.
        if cumulative == 1 or cumulative % 5 == 0:
            self.telemetry_update.emit({
                "tokens_per_second": round(tps, 2),
                "cumulative_tokens": cumulative,
                "elapsed_seconds": round(elapsed, 2),
            })

    def _record_memory_success(self, filepath: str, task: dict) -> None:
        """When a task's file finally passes verification, link whatever
        failure fingerprints it accumulated along the way to the instructions
        that resolved them, so future runs recall the fix, not just the bug.
        """
        fingerprints = self._task_failure_fps.pop(filepath, [])
        if not fingerprints:
            return
        try:
            self.memory.record_success(filepath, task.get("instructions", ""), fingerprints)
        except Exception as exc:
            logger.debug("SwarmMemory.record_success failed (non-fatal): %s", exc)

    def _verify_proposals_in_temp_workspace(
        self,
        proposals: list[dict],
        layer_index: int,
    ) -> tuple[bool, str]:
        """Apply proposed edits to a temporary copy and run verification there."""
        cmd = self.state.test_command

        source = Path(self.state.workspace_path).resolve()

        def ignore(_dir: str, names: list[str]) -> set[str]:
            blocked = {
                ".git",
                ".hg",
                ".svn",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "node_modules",
                "venv",
                ".venv",
                "dist",
                "build",
            }
            return {name for name in names if name in blocked}

        with tempfile.TemporaryDirectory(prefix="karl-swarm-dryrun-") as tmp:
            sandbox = Path(tmp) / source.name
            shutil.copytree(source, sandbox, ignore=ignore, symlinks=True)
            sandbox_root = sandbox.resolve()
            for proposal in proposals:
                rel = proposal.get("filepath", "")
                content = proposal.get("content", "")
                target = (sandbox / rel).resolve()
                try:
                    target.relative_to(sandbox_root)
                except ValueError:
                    return False, f"Dry-run blocked unsafe proposal path: {rel}"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            if not cmd:
                cmd = self._write_generated_smoke_suite(sandbox, proposals)
                self.status_update.emit(
                    "[Verifier] No verification command configured; generated a temporary smoke suite."
                )

            self.status_update.emit(
                f"[Verifier] Dry-running Layer {layer_index} in a temporary workspace before approval..."
            )
            tester = TesterAgent(str(sandbox))
            passed, trace = tester.run(cmd, str(sandbox))
            trace = trace or ("Dry-run verification passed." if passed else "Dry-run verification failed.")
            self.proposal_verification_finished.emit(layer_index, passed, trace)
            if not passed:
                self.test_result.emit(passed, trace)
            return passed, trace

    def _write_generated_smoke_suite(self, sandbox: Path, proposals: list[dict]) -> str:
        """Create a minimal generated smoke test for proposed files."""
        test_dir = sandbox / ".karl_swarm_dryrun"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "generated_smoke_test.py"
        relpaths = sorted({
            str(proposal.get("filepath", "")).replace("\\", "/")
            for proposal in proposals
            if proposal.get("filepath")
        })
        test_file.write_text(
            "\n".join([
                "import pathlib",
                "import py_compile",
                "import sys",
                "",
                "ROOT = pathlib.Path(__file__).resolve().parents[1]",
                f"FILES = {relpaths!r}",
                "",
                "def main():",
                "    failures = []",
                "    for rel in FILES:",
                "        path = (ROOT / rel).resolve()",
                "        try:",
                "            path.relative_to(ROOT)",
                "        except ValueError:",
                "            failures.append(f'unsafe path escaped workspace: {rel}')",
                "            continue",
                "        if not path.exists():",
                "            failures.append(f'missing proposed file: {rel}')",
                "            continue",
                "        if path.suffix == '.py':",
                "            try:",
                "                py_compile.compile(str(path), doraise=True)",
                "            except Exception as exc:",
                "                failures.append(f'python compile failed for {rel}: {exc}')",
                "    if failures:",
                "        print('GENERATED SMOKE TEST FAILED')",
                "        for failure in failures:",
                "            print(f'- {failure}')",
                "        return 1",
                "    print('GENERATED SMOKE TEST PASSED')",
                "    for rel in FILES:",
                "        print(f'- verified {rel}')",
                "    return 0",
                "",
                "if __name__ == '__main__':",
                "    raise SystemExit(main())",
                "",
            ]),
            encoding="utf-8",
        )
        return f"{shlex.quote(sys.executable)} {shlex.quote(str(test_file))}"

    def _backup_workspace_file(self, relpath: str, full_path: Path) -> str:
        """Back up an existing workspace file before writing an approved edit."""
        backup_root = self._backup_root.resolve()
        backup_path = (backup_root / relpath).resolve()
        try:
            backup_path.relative_to(backup_root)
        except ValueError:
            raise ValueError(f"backup path escaped backup root: {relpath}")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        if full_path.exists():
            shutil.copy2(full_path, backup_path)
            return str(backup_path)

        marker = backup_path.with_suffix(backup_path.suffix + ".missing")
        marker.write_text("file did not exist before this swarm run\n", encoding="utf-8")
        return str(marker)

    def _record_backup_manifest(self, relpath: str, backup_path: str, existed: bool) -> None:
        self._backup_manifest.append({
            "filepath": relpath,
            "backup_path": backup_path,
            "existed": existed,
        })
        manifest_path = self._backup_root / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({
                "run_id": self._run_id,
                "workspace_path": self.state.workspace_path,
                "files": self._backup_manifest,
            }, indent=2),
            encoding="utf-8",
        )

    # ── Drift detection ──────────────────────────────────────────────────────

    def _finish_coder_attempt(self, filepath: str, task: dict, ok: bool, detail: str) -> tuple[str, bool, str]:
        """Wrap a _run_one return value, recording it for drift comparison."""
        digest = hashlib.sha256((detail or "").encode("utf-8", "ignore")).hexdigest()
        self._record_drift_outcome(filepath, task, ok, digest, detail)
        return filepath, ok, detail

    def _record_drift_outcome(self, filepath: str, task: dict, ok: bool, digest: str, detail_text: str) -> None:
        """Compare this attempt's outcome against the last attempt of the same
        kind (success content vs. failure trace) for *filepath*. Two identical
        outcomes in a row means the coder is stuck, so inject corrective
        guidance rather than letting it repeat the same attempt indefinitely.
        """
        bucket = "success" if ok else "failure"
        history = self._drift_history.setdefault(filepath, {"success": None, "failure": None})
        if history[bucket] is not None and history[bucket] == digest:
            reason = "identical content" if ok else "identical failure trace"
            self._trigger_drift_alert(filepath, task, reason, detail_text)
        history[bucket] = digest

    def _trigger_drift_alert(self, filepath: str, task: dict, reason: str, trace_text: str) -> None:
        trace_lines = (trace_text or "").strip().splitlines()
        trace_snippet = trace_lines[-1].strip() if trace_lines else "unknown error"
        focus = (task.get("instructions", "") or "").strip()[:200] or f"the requirements for {filepath}"
        if reason == "identical failure trace":
            message = (
                f"Drift detected: You have repeatedly failed with trace '{trace_snippet}'. "
                f"Pivot approach and focus exclusively on: {focus}"
            )
        else:
            message = (
                f"Drift detected: You produced identical output twice for {filepath} without "
                f"resolving prior failures. Pivot approach and focus exclusively on: {focus}"
            )
        self._emit_cognition("drift_detected", filepath=filepath, reason=reason)
        if self.auto_steering_enabled:
            self.inject_guidance(filepath, message)
            self.drift_detected.emit(filepath, message)
            self.status_update.emit(f"[Drift] {filepath}: {reason} detected — corrective guidance injected.")
        else:
            self.status_update.emit(f"[Drift] {filepath}: {reason} detected — auto-steering disabled, no guidance injected.")

    # ── Cognitive trace graph ────────────────────────────────────────────────

    def _emit_cognition(self, node_type: str, **data) -> None:
        node = {"type": node_type, "timestamp": time.time(), **data}
        self._cognition_nodes.append(node)
        self.cognitive_node.emit(node)

    def _persist_cognition_graph(self) -> None:
        try:
            out_dir = Path("data/logs/swarm_cognition")
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"run_{self._run_id}.json"
            path.write_text(json.dumps(self._cognition_nodes, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logger.debug("Could not persist cognition graph (non-fatal): %s", exc)

    # ── Adaptive concurrency ─────────────────────────────────────────────────

    def _compute_max_workers(self, task_count: int) -> tuple[int, str]:
        """Pick a worker-pool size for this layer. Falls back to the historical
        fixed cap of 4 when adaptive_concurrency is off or hardware probing
        fails, so behavior is unchanged for callers that don't opt in.
        """
        if not self.adaptive_concurrency:
            return min(task_count, 4), "adaptive concurrency disabled (fixed cap)"
        try:
            from core.hardware_scout import get_hardware_profile
            profile = get_hardware_profile()
            budget = max(1, os.cpu_count() or 4)
            reasons = [f"{budget} logical cores"]

            gpu_temp = profile.get("gpu_temp_c")
            if gpu_temp is not None and gpu_temp >= 80:
                budget = max(1, budget // 2)
                reasons.append(f"GPU at {gpu_temp:.0f}C, halved for thermal headroom")

            vram_gb = profile.get("vram_gb")
            if vram_gb is not None and 0 < vram_gb < 1.0:
                budget = max(1, budget // 2)
                reasons.append(f"low free VRAM ({vram_gb:.2f}GB), halved")

            workers = max(1, min(task_count, budget, 8))
            return workers, "; ".join(reasons)
        except Exception as exc:
            return min(task_count, 4), f"hardware probe failed ({exc}), fixed cap"

    def _known_codebase_names(self) -> set[str]:
        """All function/class/method names the codebase already defines, used
        by the Judge to detect candidates that call hallucinated APIs.
        """
        try:
            mem = CodebaseMemory(self.state.workspace_path)
            index = mem.build_index()
            names: set[str] = set()
            for payload in index.values():
                for fn in payload.get("functions", []):
                    if fn.get("name"):
                        names.add(fn["name"])
                for cls in payload.get("classes", []):
                    if cls.get("name"):
                        names.add(cls["name"])
                    for m in cls.get("methods", []):
                        if m.get("name"):
                            names.add(m["name"])
            return names
        except Exception as exc:
            logger.debug("Could not build known-names index (non-fatal): %s", exc)
            return set()

    def _persona_temperature(self, index: int, total: int) -> float | None:
        """Vary temperature across multiverse candidates so they explore
        genuinely different solutions rather than re-sampling near-duplicates.
        Returns None (use the Coder's own default) when only one candidate is
        requested, so single-candidate runs are bit-for-bit unchanged.
        """
        if total <= 1:
            return None
        base = self.coder.temperature
        # Spread candidates from conservative (below base) to exploratory
        # (above base), evenly across the requested count.
        spread = [0.6, 1.0, 1.4, 1.7, 2.0]
        factor = spread[min(index, len(spread) - 1)]
        return max(0.05, min(1.2, round(base * factor, 3)))

    def _process_events_if_main_thread(self):
        import threading
        from PyQt6.QtWidgets import QApplication
        if threading.current_thread() is threading.main_thread():
            app = QApplication.instance()
            if app:
                app.processEvents()

    def _timed_out(self) -> bool:
        return self._run_deadline is not None and time.monotonic() >= self._run_deadline

    def request_stop(self):
        self._stop_requested = True
        # Unblock any pending cherry-pick wait so the thread can exit cleanly.
        self._cherry_pick_event.set()

    def commit_selected_edits(self, selected_filepaths: list[str]):
        """Called from the UI thread to confirm which proposed edits should be written to disk."""
        self._cherry_pick_selected = list(selected_filepaths)
        self._cherry_pick_event.set()

    def _workspace_root(self) -> Path:
        return Path(self.state.workspace_path).expanduser().resolve()

    def _resolve_task_path(self, filepath: str) -> tuple[str, Path]:
        if not isinstance(filepath, str) or not filepath.strip():
            raise ValueError("filepath must be a non-empty string")

        raw = filepath.strip().replace("\\", "/")
        rel = Path(raw)
        if rel.is_absolute():
            raise ValueError(f"absolute paths are not allowed: {filepath}")
        if any(part == ".." for part in rel.parts):
            raise ValueError(f"path traversal is not allowed: {filepath}")

        root = self._workspace_root()
        full_path = (root / rel).resolve()
        try:
            full_path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"path escapes workspace: {filepath}") from exc

        return full_path.relative_to(root).as_posix(), full_path

    def _validate_task(self, task: dict[str, Any]) -> dict[str, str]:
        if not isinstance(task, dict):
            raise ValueError("task must be an object")
        if not isinstance(task.get("instructions"), str) or not task["instructions"].strip():
            raise ValueError("task.instructions must be a non-empty string")

        filepath, _full_path = self._resolve_task_path(task.get("filepath", ""))
        return {
            "filepath": filepath,
            "instructions": task["instructions"].strip(),
        }

    def _validate_tasks(self, raw_tasks: Any) -> list[dict[str, str]]:
        if not isinstance(raw_tasks, list):
            raise ValueError("plan.tasks must be a list")

        validated = []
        seen = set()
        for index, task in enumerate(raw_tasks, start=1):
            try:
                item = self._validate_task(task)
            except ValueError as exc:
                raise ValueError(f"invalid task #{index}: {exc}") from exc
            if item["filepath"] in seen:
                raise ValueError(f"duplicate task filepath: {item['filepath']}")
            seen.add(item["filepath"])
            validated.append(item)
        return validated

    def scan_workspace(self) -> Dict[str, str]:
        """Scans the directory for code files, excluding build and git files."""
        context = {}
        exclude_dirs = {".git", ".venv", "venv", "__pycache__", "data", "scratch", "unsloth_compiled_cache"}
        
        for root, dirs, files in os.walk(self.state.workspace_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                # Target Python and core text files
                if f.endswith((".py", ".json", ".txt", ".md")) and f not in ("active_model.json", "model_registry.json", "run_tests.py"):
                    path = os.path.join(root, f)
                    rel_path = os.path.relpath(path, self.state.workspace_path)
                    try:
                        # Skip large binary or log files
                        if os.path.getsize(path) < 50000:
                            with open(path, "r", encoding="utf-8", errors="ignore") as file_obj:
                                context[rel_path] = file_obj.read()
                    except OSError as exc:
                        self.status_update.emit(f"[Scan] Skipped {rel_path}: {exc}")
        return context

    def build_dependency_layers(self, tasks: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """
        Groups tasks into execution layers based on Python file import dependencies.
        Tasks within the same layer do not import each other and can run in parallel.
        """
        stems = {Path(t["filepath"]).stem: t["filepath"] for t in tasks}
        dependencies = {t["filepath"]: set() for t in tasks}

        for t in tasks:
            fp = t["filepath"]
            full_path = self._workspace_root() / fp
            if fp.endswith(".py") and full_path.exists():
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    imports = get_python_imports(content)
                    for imp in imports:
                        for stem, task_fp in stems.items():
                            if task_fp != fp and (imp == stem or imp.startswith(stem + ".") or imp.endswith("." + stem)):
                                dependencies[fp].add(task_fp)
                except Exception as e:
                    self.status_update.emit(f"[Graph] Error parsing imports for {fp}: {e}")

        in_degree = {fp: len(deps) for fp, deps in dependencies.items()}
        adj = {t["filepath"]: [] for t in tasks}
        for fp, deps in dependencies.items():
            for dep in deps:
                adj[dep].append(fp)

        layers = []
        remaining = set(in_degree.keys())

        while remaining:
            zero_in = [fp for fp in remaining if in_degree[fp] == 0]
            if not zero_in:
                # Cycle detected. Break cycle by taking the first remaining node
                self.status_update.emit("[Graph] Cycle detected in task dependencies. Falling back to sequential grouping.")
                cycle_node = list(remaining)[0]
                zero_in = [cycle_node]
                in_degree[cycle_node] = 0

            layer_tasks = [t for t in tasks if t["filepath"] in zero_in]
            layers.append(layer_tasks)

            for fp in zero_in:
                remaining.remove(fp)
                for neighbor in adj[fp]:
                    if neighbor in remaining:
                        in_degree[neighbor] = max(0, in_degree[neighbor] - 1)

        return layers

    def _run_layer(self, layer_tasks: list, layer_index: int, total_layers: int, layer_failure_traces: dict) -> bool:
        self.layer_started.emit(layer_index, total_layers, layer_tasks)
        self._emit_cognition(
            "layer_started",
            layer_index=layer_index,
            total_layers=total_layers,
            tasks=[t["filepath"] for t in layer_tasks],
        )
        workspace_ctx = self.scan_workspace()
        max_workers, worker_reason = self._compute_max_workers(len(layer_tasks))
        if self.pause_on_step:
            # Serialize execution so pause/step semantics are unambiguous —
            # exactly one task waits on pause_event at a time.
            max_workers, worker_reason = 1, "serialized: pause_on_step debugging mode active"
        self.concurrency_adjusted.emit(max_workers, worker_reason)
        self._emit_cognition("concurrency_adjusted", workers=max_workers, reason=worker_reason, layer_index=layer_index)
        results: dict[str, tuple[bool, str]] = {}

        def _finish_layer(success: bool, summary: str) -> bool:
            self.layer_finished.emit(layer_index, success, summary)
            self._emit_cognition("layer_finished", layer_index=layer_index, success=success, summary=summary)
            self._process_events_if_main_thread()
            return success

        def _record_failure(filepath: str, task: dict, detail: str) -> None:
            try:
                fp_hash = self.memory.record_failure(filepath, task.get("instructions", ""), detail)
                self._task_failure_fps.setdefault(filepath, []).append(fp_hash)
            except Exception as exc:
                logger.debug("SwarmMemory.record_failure failed (non-fatal): %s", exc)

        def _run_one(task: dict) -> tuple[str, bool, str]:
            """Generate (possibly N candidates), score, validate — does NOT write to disk."""
            if self._stop_requested:
                return task["filepath"], False, "stopped"
            filepath = task["filepath"]

            if self.pause_on_step:
                task_info = {
                    "filepath": filepath,
                    "instructions": task.get("instructions", ""),
                    "layer_index": layer_index,
                }
                self.pause_event.clear()
                self.swarm_paused.emit(task_info)
                self._emit_cognition("swarm_paused", filepath=filepath, layer_index=layer_index)
                while not self.pause_event.wait(timeout=0.5):
                    if self._stop_requested:
                        return filepath, False, "stopped"
                task = self._apply_task_override(task)

            self.task_status_changed.emit(filepath, "in_progress", f"Layer {layer_index} coding")

            def _tok_cb(tok: str):
                self.coder_token.emit(filepath, tok)
                self._record_token_telemetry()

            tags = classify_task(task)

            task_copy = dict(task)
            prior_trace = layer_failure_traces.get(filepath)
            if prior_trace:
                task_copy["instructions"] += (
                    f"\nWarning: Previous test failed with this trace:\n{prior_trace}\n"
                    "Correct the code to fix this."
                )

            memory_hint = ""
            if self.enable_memory:
                try:
                    memory_hint = self.memory.recall(filepath, task_copy["instructions"])
                except Exception as exc:
                    logger.debug("SwarmMemory.recall failed (non-fatal): %s", exc)
                if memory_hint:
                    self.memory_recalled.emit(filepath, memory_hint)
                    self._emit_cognition("memory_recalled", filepath=filepath, text=memory_hint)

            guidance_getter = lambda fp=filepath: self._drain_guidance(fp)

            n = self.candidates_per_task
            candidates: list[str] = []
            try:
                for i in range(n):
                    content = self.coder.generate(
                        task_copy, workspace_ctx,
                        workspace_path=self.state.workspace_path,
                        token_callback=_tok_cb if i == 0 else None,
                        guidance_getter=guidance_getter,
                        memory_hint=memory_hint,
                        temperature_override=self._persona_temperature(i, n),
                        allowed_paths=self._plan_filepaths,
                    )
                    candidates.append(content)
            except Exception as e:
                msg = str(e)
                self.task_status_changed.emit(filepath, "failed", msg[:120])
                self.traceback_captured.emit(filepath, msg)
                self.verification_failed.emit(filepath, msg)
                self.test_result.emit(False, msg)
                layer_failure_traces[filepath] = msg
                _record_failure(filepath, task, msg)
                return self._finish_coder_attempt(filepath, task, False, msg)

            if n > 1:
                self.candidates_generated.emit(filepath, n)
                self._emit_cognition("candidates_generated", filepath=filepath, count=n)

            winner_idx, winner_score, all_scores = select_winner(
                filepath, candidates,
                original_content=workspace_ctx.get(filepath, ""),
                known_names=self._known_names_cache,
            )
            content = candidates[winner_idx]

            if n > 1:
                for i, sc in enumerate(all_scores):
                    self.candidate_scored.emit(filepath, i, sc)
                    self._emit_cognition("candidate_scored", filepath=filepath, index=i, score=sc)
                self.winner_selected.emit(filepath, winner_idx, f"total_score={winner_score['total_score']}")
                self._emit_cognition("winner_selected", filepath=filepath, index=winner_idx, score=winner_score)

            if content.startswith("# SYNTAX ERROR"):
                self.task_status_changed.emit(filepath, "failed", content[:120])
                self.traceback_captured.emit(filepath, content)
                self.verification_failed.emit(filepath, content)
                self.test_result.emit(False, content)
                layer_failure_traces[filepath] = content
                _record_failure(filepath, task, content)
                return self._finish_coder_attempt(filepath, task, False, content)

            syntax_error = None
            if filepath.endswith(".py"):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    syntax_error = f"SyntaxError: {e.msg} at line {e.lineno}"
            elif filepath.endswith(".json"):
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    syntax_error = f"JSONDecodeError: {e.msg} at line {e.lineno} col {e.colno}"

            if syntax_error:
                self.task_status_changed.emit(filepath, "failed", syntax_error)
                self.traceback_captured.emit(filepath, syntax_error)
                self.verification_failed.emit(filepath, syntax_error)
                self.test_result.emit(False, syntax_error)
                layer_failure_traces[filepath] = syntax_error
                _record_failure(filepath, task, syntax_error)
                return self._finish_coder_attempt(filepath, task, False, syntax_error)

            # ── Adaptive specialist review (LLM-free, gated by task classification) ──
            if self.enable_specialists and "security" in tags:
                sec = SecurityAuditorAgent().review(filepath, content)
                self.specialist_review.emit(filepath, "security", sec)
                self._emit_cognition("specialist_review", filepath=filepath, specialist="security", result=sec)
                if sec["verdict"] == "revise":
                    msg = "Security review flagged concerns: " + "; ".join(sec["concerns"])
                    self.task_status_changed.emit(filepath, "failed", msg[:160])
                    self.traceback_captured.emit(filepath, msg)
                    self.verification_failed.emit(filepath, msg)
                    self.test_result.emit(False, msg)
                    layer_failure_traces[filepath] = msg
                    _record_failure(filepath, task, msg)
                    return self._finish_coder_attempt(filepath, task, False, msg)

            if self.enable_specialists and "performance" in tags:
                perf = PerformanceAuditorAgent().review(filepath, content)
                self.specialist_review.emit(filepath, "performance", perf)
                self._emit_cognition("specialist_review", filepath=filepath, specialist="performance", result=perf)

            if self.enable_critic:
                crit = CriticAgent().review(filepath, content)
                self.specialist_review.emit(filepath, "critic", crit)
                self._emit_cognition("specialist_review", filepath=filepath, specialist="critic", result=crit)

            return self._finish_coder_attempt(filepath, task, True, content)

        if self.pause_on_step:
            # Run inline on this thread rather than via the pool: swarm_paused
            # is a request/response signal (the emit blocks on pause_event),
            # and a worker thread's emit isn't guaranteed synchronous delivery
            # without a live Qt event loop on that thread.
            for task in layer_tasks:
                fp, ok, detail = _run_one(task)
                results[fp] = (ok, detail)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_run_one, task): task for task in layer_tasks}
                for future in futures:
                    fp, ok, detail = future.result()
                    results[fp] = (ok, detail)

        self._process_events_if_main_thread()

        # Fail fast if any coder produced an invalid result
        all_ok = all(ok for ok, _ in results.values())
        if not all_ok:
            for task in layer_tasks:
                fp = task["filepath"]
                ok, detail = results.get(fp, (False, "Unknown failure"))
                if not ok:
                    self.state.tasks_status[fp] = "failed"
                    self.task_status_changed.emit(fp, "failed", detail)
            return _finish_layer(False, f"Layer {layer_index} had coding failures")

        if self._stop_requested:
            return False

        # ── Cherry-pick: surface proposed edits to the UI before touching disk ──
        proposals = [
            {"filepath": fp, "content": detail}
            for fp, (ok, detail) in results.items()
            if ok
        ]
        if not proposals:
            return _finish_layer(True, f"Layer {layer_index} had no file edits")

        dry_run_passed, dry_run_trace = self._verify_proposals_in_temp_workspace(proposals, layer_index)
        if not dry_run_passed:
            self.traceback_captured.emit(f"Layer {layer_index} dry-run", dry_run_trace)
            self.verification_failed.emit(f"Layer {layer_index} dry-run", dry_run_trace)
            for task in layer_tasks:
                fp = task["filepath"]
                layer_failure_traces[fp] = dry_run_trace
                self.task_status_changed.emit(fp, "dry_run_failed", dry_run_trace)
                try:
                    fp_hash = self.memory.record_failure(fp, task.get("instructions", ""), dry_run_trace)
                    self._task_failure_fps.setdefault(fp, []).append(fp_hash)
                except Exception as exc:
                    logger.debug("SwarmMemory.record_failure failed (non-fatal): %s", exc)
            return _finish_layer(False, f"Layer {layer_index} dry-run verification failed")

        self._cherry_pick_event.clear()
        self._cherry_pick_selected = [p["filepath"] for p in proposals]  # default: all selected
        self._emit_cognition(
            "edits_proposed",
            layer_index=layer_index,
            files=[p["filepath"] for p in proposals],
            dry_run_passed=True,
        )
        self.edits_proposed.emit(proposals)

        # Block until the UI calls commit_selected_edits() (or stop is requested)
        while not self._cherry_pick_event.wait(timeout=0.5):
            if self._stop_requested:
                return False

        if self._stop_requested:
            return False

        selected = set(self._cherry_pick_selected)
        self._emit_cognition(
            "edits_approved",
            layer_index=layer_index,
            approved=sorted(selected),
            rejected=sorted(p["filepath"] for p in proposals if p["filepath"] not in selected),
        )

        # ── Write only the files the developer approved ──
        write_failed = False
        for p in proposals:
            fp = p["filepath"]
            content = p["content"]
            if fp in selected:
                try:
                    _, full_path = self._resolve_task_path(fp)
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    existed_before = full_path.exists()
                    backup_path = self._backup_workspace_file(fp, full_path)
                    self._record_backup_manifest(fp, backup_path, existed_before)
                    full_path.write_text(content, encoding="utf-8")
                    self._emit_cognition(
                        "file_written",
                        layer_index=layer_index,
                        filepath=fp,
                        backup_path=backup_path,
                    )
                    self.file_edited.emit(fp, content)
                    self.task_status_changed.emit(fp, "written", f"File written; backup: {backup_path}")
                except Exception as e:
                    write_failed = True
                    self.task_status_changed.emit(fp, "failed", str(e))
                    layer_failure_traces[fp] = str(e)
            else:
                self._emit_cognition("file_skipped", layer_index=layer_index, filepath=fp)
                self.task_status_changed.emit(fp, "skipped", "Cherry-picked out")
                self.state.tasks_status[fp] = "skipped"

        self._process_events_if_main_thread()
        if write_failed:
            return _finish_layer(False, f"Layer {layer_index} had write failures")

        cmd = self.state.test_command
        if cmd:
            self.verification_started.emit(layer_index, cmd)
            self._process_events_if_main_thread()
            with Span("Test Execution", {
                "layer_index": layer_index,
                "command": cmd,
                "task_count": len(layer_tasks),
            }) as test_span:
                passed, trace = self.tester.run(cmd, self.state.workspace_path)
                test_span.set_attribute("success", passed)
                test_span.set_attribute("trace_length", len(trace or ""))
            self.test_result.emit(passed, trace)
            self._emit_cognition(
                "test_result", layer_index=layer_index, passed=passed, trace=(trace or "")[:2000],
            )
            self._process_events_if_main_thread()
            if not passed:
                self.traceback_captured.emit(f"Layer {layer_index}", trace)
                self.verification_failed.emit(f"Layer {layer_index}", trace)
                for task in layer_tasks:
                    fp = task["filepath"]
                    layer_failure_traces[fp] = trace
                    self.task_status_changed.emit(fp, "verification_failed", trace)
                    try:
                        fp_hash = self.memory.record_failure(fp, task.get("instructions", ""), trace)
                        self._task_failure_fps.setdefault(fp, []).append(fp_hash)
                    except Exception as exc:
                        logger.debug("SwarmMemory.record_failure failed (non-fatal): %s", exc)
                return _finish_layer(False, f"Layer {layer_index} verification failed")
            else:
                for task in layer_tasks:
                    fp = task["filepath"]
                    if fp in self._cherry_pick_selected:
                        self.state.tasks_status[fp] = "completed"
                        self.task_status_changed.emit(fp, "completed", f"Layer {layer_index} verified")
                    self._record_memory_success(fp, task)
                return _finish_layer(True, f"Layer {layer_index} verified")
        else:
            for task in layer_tasks:
                fp = task["filepath"]
                self.state.tasks_status[fp] = "completed"
                self.task_status_changed.emit(fp, "completed", f"Layer {layer_index} complete")
                self._record_memory_success(fp, task)
            return _finish_layer(True, f"Layer {layer_index} complete")

    def run(self):
        with Span("Swarm Run", {
            "workspace_path": self.state.workspace_path,
            "objective": self.state.objective,
            "test_command": self.state.test_command,
        }) as swarm_span:
            try:
                self._run_deadline = time.monotonic() + self.timeout_seconds
                self._emit_cognition(
                    "run_started",
                    objective=self.state.objective,
                    workspace_path=self.state.workspace_path,
                    test_command=self.state.test_command,
                )
                self.status_update.emit(
                    f"[Swarm] Starting codebase analysis and file scanning... "
                    f"(timeout {self.timeout_seconds}s, max {self.max_loops} loop(s) per layer)"
                )
                with Span("Retrieve Context", {"query": self.state.objective}) as retrieve_span:
                    context = self.scan_workspace()
                    retrieve_span.set_attribute("chunks", len(context))
                    retrieve_span.set_attribute("bytes", sum(len(v) for v in context.values()))

                self._known_names_cache = self._known_codebase_names()

                if self._stop_requested:
                    swarm_span.set_attribute("stopped", True)
                    self.finished_swarm.emit(False, "Execution stopped by user.")
                    return

                # Phase 1: Architect Plan Generation
                self.status_update.emit("[Architect] Analyzing files and formulating implementation plan...")
                prompt_size = len(self.state.objective) + sum(len(v) for v in context.values())
                token_count = len(self.state.objective.split()) + sum(len(v.split()) for v in context.values())
                with Span("Agent Reasoning", {
                    "agent": "architect",
                    "prompt_size": prompt_size,
                    "token_count": token_count,
                }) as reasoning_span:
                    plan = self.architect.create_plan(self.state.objective, context)
                    reasoning_span.set_attribute(
                        "task_count",
                        len(plan.get("tasks", [])) if isinstance(plan, dict) else 0,
                    )
                self.state.plan = plan
                self.task_plan_created.emit(plan)
                self._emit_cognition(
                    "architect_plan",
                    explanation=plan.get("explanation", "") if isinstance(plan, dict) else "",
                    tasks=plan.get("tasks", []) if isinstance(plan, dict) else [],
                )
                self._process_events_if_main_thread()

                try:
                    tasks = self._validate_tasks(plan.get("tasks", []))
                except ValueError as exc:
                    swarm_span.set_attribute("success", False)
                    self.status_update.emit(f"[Architect] Rejected unsafe task plan: {exc}")
                    self.finished_swarm.emit(False, f"Unsafe task plan: {exc}")
                    self._process_events_if_main_thread()
                    return

                self._plan_filepaths = {t["filepath"] for t in tasks}

                if not tasks:
                    swarm_span.set_attribute("success", True)
                    swarm_span.set_attribute("task_count", 0)
                    self.status_update.emit("[Swarm] No coding tasks identified by the Architect.")
                    self.finished_swarm.emit(True, "No actions needed.")
                    self._process_events_if_main_thread()
                    return

                self.status_update.emit(f"[Swarm] Architect identified {len(tasks)} files to modify.")
                self._process_events_if_main_thread()
                
                # Initialize tasks status
                for t in tasks:
                    self.state.tasks_status[t["filepath"]] = "pending"
                    self.task_status_changed.emit(t["filepath"], "pending", "Architect queued task")
                self._process_events_if_main_thread()
                
                all_successful = True
                changed_files = []

                # 1. Group tasks into layers
                layers = self.build_dependency_layers(tasks)
                self.dependency_layers_built.emit(layers)
                self._process_events_if_main_thread()
                self.status_update.emit(f"[Swarm] Divided {len(tasks)} tasks into {len(layers)} dependency layers.")

                for layer_idx, layer in enumerate(layers, 1):
                    if self._stop_requested:
                        swarm_span.set_attribute("stopped", True)
                        self.finished_swarm.emit(False, "Execution stopped by user.")
                        return

                    if self._timed_out():
                        swarm_span.set_attribute("timed_out", True)
                        self.status_update.emit(
                            f"[Swarm] Execution timeout ({self.timeout_seconds}s) reached before "
                            f"Layer {layer_idx}/{len(layers)}. Stopping gracefully."
                        )
                        self.finished_swarm.emit(False, f"Execution timed out after {self.timeout_seconds}s.")
                        self._process_events_if_main_thread()
                        return

                    self.status_update.emit(f"[Swarm] Starting execution of Layer {layer_idx}/{len(layers)} ({len(layer)} tasks)...")

                    layer_success = False
                    layer_retries = 0
                    max_layer_retries = self.max_loops
                    layer_failure_traces = {t["filepath"]: None for t in layer}

                    while not layer_success and layer_retries < max_layer_retries:
                        if self._stop_requested:
                            swarm_span.set_attribute("stopped", True)
                            self.finished_swarm.emit(False, "Execution stopped by user.")
                            return

                        if self._timed_out():
                            swarm_span.set_attribute("timed_out", True)
                            self.status_update.emit(
                                f"[Swarm] Execution timeout ({self.timeout_seconds}s) reached during "
                                f"Layer {layer_idx} retries. Stopping gracefully."
                            )
                            self.finished_swarm.emit(False, f"Execution timed out after {self.timeout_seconds}s.")
                            self._process_events_if_main_thread()
                            return

                        layer_success = self._run_layer(layer, layer_idx, len(layers), layer_failure_traces)
                        if not layer_success:
                            layer_retries += 1
                            if layer_retries < max_layer_retries:
                                with Span("Self Reflection", {
                                    "layer_index": layer_idx,
                                    "correction_loop": layer_retries,
                                    "max_correction_loops": max_layer_retries - 1,
                                    "failed_files": [
                                        fp for fp, trace in layer_failure_traces.items() if trace
                                    ],
                                }):
                                    self.status_update.emit(f"[Swarm] Layer {layer_idx} had failures. Retrying layer (Attempt {layer_retries + 1}/{max_layer_retries})...")

                    if layer_success:
                        for task in layer:
                            if task["filepath"] not in changed_files:
                                changed_files.append(task["filepath"])
                    else:
                        all_successful = False
                        self.status_update.emit(f"[Error] Failed to verify Layer {layer_idx} tasks after {max_layer_retries} attempts.")

                summary = f"Modified files: {', '.join(changed_files)}" if changed_files else "No files modified successfully."
                swarm_span.set_attribute("success", all_successful)
                swarm_span.set_attribute("changed_files", changed_files)
                swarm_span.set_attribute("task_count", len(tasks))
                swarm_span.set_attribute("layer_count", len(layers))
                self.finished_swarm.emit(all_successful, summary)
                self._emit_cognition("swarm_finished", success=all_successful, summary=summary)
                self._process_events_if_main_thread()

            except Exception as e:
                logger.exception("Swarm runtime exception")
                swarm_span.status = "ERROR"
                swarm_span.error = {
                    "type": type(e).__name__,
                    "message": str(e),
                }
                swarm_span.set_attribute("success", False)
                self.status_update.emit(f"[Error] Swarm runtime exception: {e}")
                self.finished_swarm.emit(False, f"Exception: {e}")
                self._process_events_if_main_thread()
            finally:
                self._persist_cognition_graph()
