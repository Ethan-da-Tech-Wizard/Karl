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

            # Phase 2 & 3: Coder and Tester loop
            all_successful = True
            changed_files = []

            for task in tasks:
                if self._stop_requested:
                    self.finished_swarm.emit(False, "Execution stopped by user.")
                    return

                filepath = task["filepath"]
                instructions = task["instructions"]
                try:
                    filepath, full_path_obj = self._resolve_task_path(filepath)
                except ValueError as exc:
                    self.state.tasks_status[filepath] = "failed"
                    self.status_update.emit(f"[Error] Refusing unsafe task path {filepath}: {exc}")
                    all_successful = False
                    continue
                full_path = str(full_path_obj)

                self.state.tasks_status[filepath] = "in_progress"
                self.status_update.emit(f"[Coder] Starting work on: {filepath}")

                # Read current content
                current_content = ""
                if os.path.exists(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            current_content = f.read()
                    except Exception as e:
                        self.status_update.emit(f"[Error] Failed to read {filepath}: {e}")

                success = False
                retries = 0
                max_retries = 3
                failure_trace = None

                while not success and retries < max_retries:
                    if self._stop_requested:
                        self.finished_swarm.emit(False, "Execution stopped by user.")
                        return

                    self.status_update.emit(f"[Coder] Generating code edit (Attempt {retries + 1}/{max_retries})...")
                    new_content = self.coder.edit_file(filepath, current_content, instructions, failure_trace)
                    
                    # Syntax validation guards (Phase 4)
                    syntax_error = None
                    if filepath.endswith(".py"):
                        try:
                            ast.parse(new_content)
                        except SyntaxError as e:
                            syntax_error = f"SyntaxError: {e.msg} at line {e.lineno}"
                    elif filepath.endswith(".json"):
                        try:
                            json.loads(new_content)
                        except json.JSONDecodeError as e:
                            syntax_error = f"JSONDecodeError: {e.msg} at line {e.lineno} col {e.colno}"

                    if syntax_error:
                        self.status_update.emit(f"[AST/JSON Guard] Blocked write due to syntax errors in {filepath}: {syntax_error}")
                        failure_trace = syntax_error
                        self.test_result.emit(False, failure_trace)
                        retries += 1
                        continue

                    # Write to file
                    try:
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        self.file_edited.emit(filepath, new_content)
                    except Exception as e:
                        self.status_update.emit(f"[Error] Failed to write {filepath}: {e}")
                        break

                    # Tester executes tests
                    self.status_update.emit(f"[Tester] Running tests: {self.state.test_command}...")
                    test_res = self.tester.run_test_command(self.state.test_command)
                    self.state.test_runs.append(test_res)

                    if test_res["passed"]:
                        self.status_update.emit(f"[Tester] Verification PASSED for: {filepath}!")
                        self.test_result.emit(True, "")
                        success = True
                    else:
                        failure_trace = test_res["error_trace"]
                        self.status_update.emit(f"[Tester] Verification FAILED for: {filepath}!")
                        self.test_result.emit(False, failure_trace)
                        retries += 1

                if success:
                    self.state.tasks_status[filepath] = "completed"
                    changed_files.append(filepath)
                else:
                    self.state.tasks_status[filepath] = "failed"
                    all_successful = False
                    self.status_update.emit(f"[Error] Failed to verify task {filepath} after {max_retries} attempts.")

            summary = f"Modified files: {', '.join(changed_files)}" if changed_files else "No files modified successfully."
            self.finished_swarm.emit(all_successful, summary)

        except Exception as e:
            self.status_update.emit(f"[Error] Swarm runtime exception: {e}")
            self.finished_swarm.emit(False, f"Exception: {e}")
