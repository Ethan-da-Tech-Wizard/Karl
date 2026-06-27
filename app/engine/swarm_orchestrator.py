"""
Swarm Orchestrator — Karl Workbench
====================================
Coordinates the multi-agent planning, coding, and testing execution loop.
Runs in a background QThread to emit signals to PyQt6 and prevent GUI blocking.
"""

import os
import time
import ast
import json
import threading
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
from app.engine.swarm_agents import ArchitectAgent, CoderAgent, TesterAgent
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


class SwarmOrchestratorThread(QThread):
    status_update = pyqtSignal(str)              # General log message
    task_plan_created = pyqtSignal(dict)          # The Architect's JSON plan
    dependency_layers_built = pyqtSignal(list)    # list[list[task]]
    layer_started = pyqtSignal(int, int, list)     # layer_index, total_layers, tasks
    layer_finished = pyqtSignal(int, bool, str)    # layer_index, success, summary
    task_status_changed = pyqtSignal(str, str, str)  # filepath, status, detail
    verification_started = pyqtSignal(int, str)    # layer_index, command
    traceback_captured = pyqtSignal(str, str)      # filepath/layer, traceback
    verification_failed = pyqtSignal(str, str)    # context (filepath/layer), full traceback
    edits_proposed = pyqtSignal(list)             # list[{filepath, content}] — awaits commit_selected_edits()
    file_edited = pyqtSignal(str, str)            # filepath, new_content (emitted after write)
    test_result = pyqtSignal(bool, str)           # passed, error_traceback
    finished_swarm = pyqtSignal(bool, str)        # success, final_summary
    coder_token = pyqtSignal(str, str)            # (filepath, token)

    def __init__(self, workspace_path: str, objective: str, test_command: str, hyperparams: dict = None):
        super().__init__()
        self.state = SwarmSessionState(workspace_path, objective, test_command)
        self.architect = ArchitectAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent(workspace_path)
        self._stop_requested = False

        self._cherry_pick_event = threading.Event()
        self._cherry_pick_selected: list[str] = []

        if hyperparams:
            temp = hyperparams.get("temperature")
            max_tok = hyperparams.get("max_tokens")
            if temp is not None:
                self.architect.temperature = temp
                self.coder.temperature = temp
            if max_tok is not None:
                self.architect.max_tokens = max_tok
                self.coder.max_tokens = max_tok

    def _process_events_if_main_thread(self):
        import threading
        from PyQt6.QtWidgets import QApplication
        if threading.current_thread() is threading.main_thread():
            app = QApplication.instance()
            if app:
                app.processEvents()

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
        workspace_ctx = self.scan_workspace()
        max_workers = min(len(layer_tasks), 4)
        results: dict[str, tuple[bool, str]] = {}

        def _run_one(task: dict) -> tuple[str, bool, str]:
            """Generate and validate content only — does NOT write to disk."""
            if self._stop_requested:
                return task["filepath"], False, "stopped"
            filepath = task["filepath"]
            self.task_status_changed.emit(filepath, "in_progress", f"Layer {layer_index} coding")

            def _tok_cb(tok: str):
                self.coder_token.emit(filepath, tok)

            task_copy = dict(task)
            prior_trace = layer_failure_traces.get(filepath)
            if prior_trace:
                task_copy["instructions"] += (
                    f"\nWarning: Previous test failed with this trace:\n{prior_trace}\n"
                    "Correct the code to fix this."
                )

            try:
                content = self.coder.generate(
                    task_copy, workspace_ctx,
                    workspace_path=self.state.workspace_path,
                    token_callback=_tok_cb,
                )
                if content.startswith("# SYNTAX ERROR"):
                    self.task_status_changed.emit(filepath, "failed", content[:120])
                    self.traceback_captured.emit(filepath, content)
                    self.verification_failed.emit(filepath, content)
                    self.test_result.emit(False, content)
                    layer_failure_traces[filepath] = content
                    return filepath, False, content

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
                    return filepath, False, syntax_error

                return filepath, True, content
            except Exception as e:
                msg = str(e)
                self.task_status_changed.emit(filepath, "failed", msg[:120])
                self.traceback_captured.emit(filepath, msg)
                self.verification_failed.emit(filepath, msg)
                self.test_result.emit(False, msg)
                layer_failure_traces[filepath] = msg
                return filepath, False, msg

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
            self.layer_finished.emit(layer_index, False, f"Layer {layer_index} had coding failures")
            self._process_events_if_main_thread()
            return False

        if self._stop_requested:
            return False

        # ── Cherry-pick: surface proposed edits to the UI before touching disk ──
        proposals = [
            {"filepath": fp, "content": detail}
            for fp, (ok, detail) in results.items()
            if ok
        ]
        self._cherry_pick_event.clear()
        self._cherry_pick_selected = [p["filepath"] for p in proposals]  # default: all selected
        self.edits_proposed.emit(proposals)

        # Block until the UI calls commit_selected_edits() (or stop is requested)
        while not self._cherry_pick_event.wait(timeout=0.5):
            if self._stop_requested:
                return False

        if self._stop_requested:
            return False

        # ── Write only the files the developer approved ──
        for p in proposals:
            fp = p["filepath"]
            content = p["content"]
            if fp in self._cherry_pick_selected:
                try:
                    _, full_path = self._resolve_task_path(fp)
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    self.file_edited.emit(fp, content)
                    self.task_status_changed.emit(fp, "written", "File written")
                except Exception as e:
                    self.task_status_changed.emit(fp, "failed", str(e))
                    layer_failure_traces[fp] = str(e)
            else:
                self.task_status_changed.emit(fp, "skipped", "Cherry-picked out")
                self.state.tasks_status[fp] = "skipped"

        self._process_events_if_main_thread()

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
            self._process_events_if_main_thread()
            if not passed:
                self.traceback_captured.emit(f"Layer {layer_index}", trace)
                self.verification_failed.emit(f"Layer {layer_index}", trace)
                for task in layer_tasks:
                    layer_failure_traces[task["filepath"]] = trace
                    self.task_status_changed.emit(task["filepath"], "verification_failed", trace)
                self.layer_finished.emit(layer_index, False, f"Layer {layer_index} verification failed")
                self._process_events_if_main_thread()
                return False
            else:
                for task in layer_tasks:
                    fp = task["filepath"]
                    if fp in self._cherry_pick_selected:
                        self.state.tasks_status[fp] = "completed"
                        self.task_status_changed.emit(fp, "completed", f"Layer {layer_index} verified")
                self.layer_finished.emit(layer_index, True, f"Layer {layer_index} verified")
                self._process_events_if_main_thread()
                return True
        else:
            for task in layer_tasks:
                fp = task["filepath"]
                self.state.tasks_status[fp] = "completed"
                self.task_status_changed.emit(fp, "completed", f"Layer {layer_index} complete")
            self.layer_finished.emit(layer_index, True, f"Layer {layer_index} complete")
            self._process_events_if_main_thread()
            return True

    def run(self):
        with Span("Swarm Run", {
            "workspace_path": self.state.workspace_path,
            "objective": self.state.objective,
            "test_command": self.state.test_command,
        }) as swarm_span:
            try:
                self.status_update.emit("[Swarm] Starting codebase analysis and file scanning...")
                with Span("Retrieve Context", {"query": self.state.objective}) as retrieve_span:
                    context = self.scan_workspace()
                    retrieve_span.set_attribute("chunks", len(context))
                    retrieve_span.set_attribute("bytes", sum(len(v) for v in context.values()))
                
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
                self._process_events_if_main_thread()

                try:
                    tasks = self._validate_tasks(plan.get("tasks", []))
                except ValueError as exc:
                    swarm_span.set_attribute("success", False)
                    self.status_update.emit(f"[Architect] Rejected unsafe task plan: {exc}")
                    self.finished_swarm.emit(False, f"Unsafe task plan: {exc}")
                    self._process_events_if_main_thread()
                    return

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

                    self.status_update.emit(f"[Swarm] Starting execution of Layer {layer_idx}/{len(layers)} ({len(layer)} tasks)...")
                    
                    layer_success = False
                    layer_retries = 0
                    max_layer_retries = 3
                    layer_failure_traces = {t["filepath"]: None for t in layer}
                    
                    while not layer_success and layer_retries < max_layer_retries:
                        if self._stop_requested:
                            swarm_span.set_attribute("stopped", True)
                            self.finished_swarm.emit(False, "Execution stopped by user.")
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
