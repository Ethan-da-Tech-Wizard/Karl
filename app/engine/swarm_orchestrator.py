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
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.swarm_agents import ArchitectAgent, CoderAgent, TesterAgent


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
    file_edited = pyqtSignal(str, str)            # filepath, new_content
    test_result = pyqtSignal(bool, str)           # passed, error_traceback
    finished_swarm = pyqtSignal(bool, str)        # success, final_summary

    def __init__(self, workspace_path: str, objective: str, test_command: str, hyperparams: dict = None):
        super().__init__()
        self.state = SwarmSessionState(workspace_path, objective, test_command)
        self.architect = ArchitectAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent(workspace_path)
        self._stop_requested = False

        if hyperparams:
            temp = hyperparams.get("temperature")
            max_tok = hyperparams.get("max_tokens")
            if temp is not None:
                self.architect.temperature = temp
                self.coder.temperature = temp
            if max_tok is not None:
                self.architect.max_tokens = max_tok
                self.coder.max_tokens = max_tok

    def request_stop(self):
        self._stop_requested = True

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
                if f.endswith((".py", ".json", ".txt", ".md")) and f not in ("active_model.json", "model_registry.json"):
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

    def _run_single_coder(self, filepath: str, instructions: str, failure_trace: Optional[str] = None) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Runs CoderAgent on a single file. Returns (success, full_path_str, new_content, error_msg).
        This executes in a background thread inside a ThreadPoolExecutor.
        """
        try:
            resolved_filepath, full_path_obj = self._resolve_task_path(filepath)
        except ValueError as exc:
            return False, None, None, f"Refusing unsafe task path {filepath}: {exc}"
        
        full_path = str(full_path_obj)
        self.state.tasks_status[resolved_filepath] = "in_progress"
        self.status_update.emit(f"[Coder] Starting work on: {resolved_filepath}")

        # Read current content
        current_content = ""
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    current_content = f.read()
            except Exception as e:
                return False, full_path, None, f"Failed to read file: {e}"

        # Generate code edit
        coder = CoderAgent()
        coder.temperature = self.coder.temperature
        coder.max_tokens = self.coder.max_tokens

        new_content = coder.edit_file(resolved_filepath, current_content, instructions, failure_trace)

        # Syntax validation guards
        syntax_error = None
        if resolved_filepath.endswith(".py"):
            try:
                ast.parse(new_content)
            except SyntaxError as e:
                syntax_error = f"SyntaxError: {e.msg} at line {e.lineno}"
        elif resolved_filepath.endswith(".json"):
            try:
                json.loads(new_content)
            except json.JSONDecodeError as e:
                syntax_error = f"JSONDecodeError: {e.msg} at line {e.lineno} col {e.colno}"

        if syntax_error:
            return False, full_path, None, syntax_error

        return True, full_path, new_content, None

    def run(self):
        try:
            self.status_update.emit("[Swarm] Starting codebase analysis and file scanning...")
            context = self.scan_workspace()
            
            if self._stop_requested:
                self.finished_swarm.emit(False, "Execution stopped by user.")
                return

            # Phase 1: Architect Plan Generation
            self.status_update.emit("[Architect] Analyzing files and formulating implementation plan...")
            plan = self.architect.create_plan(self.state.objective, context)
            self.state.plan = plan
            self.task_plan_created.emit(plan)

            try:
                tasks = self._validate_tasks(plan.get("tasks", []))
            except ValueError as exc:
                self.status_update.emit(f"[Architect] Rejected unsafe task plan: {exc}")
                self.finished_swarm.emit(False, f"Unsafe task plan: {exc}")
                return

            if not tasks:
                self.status_update.emit("[Swarm] No coding tasks identified by the Architect.")
                self.finished_swarm.emit(True, "No actions needed.")
                return

            self.status_update.emit(f"[Swarm] Architect identified {len(tasks)} files to modify.")
            
            # Initialize tasks status
            for t in tasks:
                self.state.tasks_status[t["filepath"]] = "pending"
                self.task_status_changed.emit(t["filepath"], "pending", "Architect queued task")

            # Phase 2 & 3: Coder and Tester loop
            all_successful = True
            changed_files = []

            # 1. Group tasks into layers
            layers = self.build_dependency_layers(tasks)
            self.dependency_layers_built.emit(layers)
            self.status_update.emit(f"[Swarm] Divided {len(tasks)} tasks into {len(layers)} dependency layers.")

            import concurrent.futures

            for layer_idx, layer in enumerate(layers, 1):
                if self._stop_requested:
                    self.finished_swarm.emit(False, "Execution stopped by user.")
                    return

                self.status_update.emit(f"[Swarm] Starting execution of Layer {layer_idx}/{len(layers)} ({len(layer)} tasks)...")
                self.layer_started.emit(layer_idx, len(layers), layer)

                layer_success = False
                layer_retries = 0
                max_layer_retries = 3
                # We track the failure trace to pass to the coder agents
                layer_failure_traces = {t["filepath"]: None for t in layer}

                while not layer_success and layer_retries < max_layer_retries:
                    if self._stop_requested:
                        self.finished_swarm.emit(False, "Execution stopped by user.")
                        return

                    # Run coders in parallel
                    futures = {}
                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(layer)) as executor:
                        for task in layer:
                            filepath = task["filepath"]
                            instructions = task["instructions"]
                            trace = layer_failure_traces.get(filepath)
                            self.task_status_changed.emit(filepath, "in_progress", f"Layer {layer_idx} coder running")
                            
                            # Submit worker
                            futures[executor.submit(self._run_single_coder, filepath, instructions, trace)] = filepath

                    # Wait for all coders to finish and get results
                    layer_coder_results = {}
                    for future in concurrent.futures.as_completed(futures):
                        filepath = futures[future]
                        try:
                            success, file_path_written, new_content, error_msg = future.result()
                            layer_coder_results[filepath] = {
                                "success": success,
                                "file_path_written": file_path_written,
                                "new_content": new_content,
                                "error_msg": error_msg
                            }
                        except Exception as e:
                            layer_coder_results[filepath] = {
                                "success": False,
                                "file_path_written": None,
                                "new_content": None,
                                "error_msg": f"Thread exception: {e}"
                            }

                    # Check if all coders succeeded in generating syntax-valid files
                    all_coders_ok = True
                    for filepath, res in layer_coder_results.items():
                        if not res["success"]:
                            all_coders_ok = False
                            self.state.tasks_status[filepath] = "failed"
                            layer_failure_traces[filepath] = res["error_msg"]
                            self.status_update.emit(f"[Coder] Code generation failed for {filepath}: {res['error_msg']}")
                            self.task_status_changed.emit(filepath, "failed", res["error_msg"] or "Coder failed")
                            self.traceback_captured.emit(filepath, res["error_msg"] or "")
                            self.test_result.emit(False, res["error_msg"])
                        else:
                            self.state.tasks_status[filepath] = "in_progress"
                            self.task_status_changed.emit(filepath, "generated", "Coder produced syntax-valid content")
                            # Write changes to the file if they were successfully generated and validated
                            if res["file_path_written"] and res["new_content"] is not None:
                                try:
                                    os.makedirs(os.path.dirname(res["file_path_written"]), exist_ok=True)
                                    with open(res["file_path_written"], "w", encoding="utf-8") as f:
                                        f.write(res["new_content"])
                                    self.file_edited.emit(filepath, res["new_content"])
                                    self.task_status_changed.emit(filepath, "written", "File written; awaiting verification")
                                except Exception as exc:
                                    all_coders_ok = False
                                    layer_failure_traces[filepath] = f"Write error: {exc}"
                                    self.status_update.emit(f"[Error] Failed to write {filepath}: {exc}")
                                    self.task_status_changed.emit(filepath, "failed", f"Write error: {exc}")
                                    self.traceback_captured.emit(filepath, f"Write error: {exc}")

                    if not all_coders_ok:
                        layer_retries += 1
                        self.status_update.emit(f"[Swarm] Layer {layer_idx} had generation/validation failures. Retrying layer (Attempt {layer_retries + 1}/{max_layer_retries})...")
                        continue

                    # Run TesterAgent verification
                    self.status_update.emit(f"[Tester] Running tests: {self.state.test_command}...")
                    self.verification_started.emit(layer_idx, self.state.test_command)
                    test_res = self.tester.run_test_command(self.state.test_command)
                    self.state.test_runs.append(test_res)

                    if test_res["passed"]:
                        self.status_update.emit(f"[Tester] Verification PASSED for all tasks in Layer {layer_idx}!")
                        for task in layer:
                            self.state.tasks_status[task["filepath"]] = "completed"
                            self.task_status_changed.emit(task["filepath"], "completed", f"Layer {layer_idx} verified")
                            if task["filepath"] not in changed_files:
                                changed_files.append(task["filepath"])
                        self.test_result.emit(True, "")
                        layer_success = True
                        self.layer_finished.emit(layer_idx, True, f"Layer {layer_idx} verified")
                    else:
                        failure_trace = test_res["error_trace"]
                        self.status_update.emit(f"[Tester] Verification FAILED for Layer {layer_idx}!")
                        self.test_result.emit(False, failure_trace)
                        self.traceback_captured.emit(f"Layer {layer_idx}", failure_trace)
                        for task in layer:
                            layer_failure_traces[task["filepath"]] = failure_trace
                            self.task_status_changed.emit(task["filepath"], "verification_failed", failure_trace)
                        layer_retries += 1

                if not layer_success:
                    all_successful = False
                    self.status_update.emit(f"[Error] Failed to verify Layer {layer_idx} tasks after {max_layer_retries} attempts.")
                    for task in layer:
                        if self.state.tasks_status[task["filepath"]] != "completed":
                            self.state.tasks_status[task["filepath"]] = "failed"
                            self.task_status_changed.emit(task["filepath"], "failed", f"Layer {layer_idx} exhausted retries")
                    self.layer_finished.emit(layer_idx, False, f"Layer {layer_idx} exhausted retries")

            summary = f"Modified files: {', '.join(changed_files)}" if changed_files else "No files modified successfully."
            self.finished_swarm.emit(all_successful, summary)

        except Exception as e:
            self.status_update.emit(f"[Error] Swarm runtime exception: {e}")
            self.finished_swarm.emit(False, f"Exception: {e}")
