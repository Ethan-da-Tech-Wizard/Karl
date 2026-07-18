"""
Swarm Replay Manager — Karl Workbench
======================================
Reconstructs historical swarm runs for the interactive debugger/replay UI.

Reads structured cognition-graph JSON files that SwarmOrchestratorThread
writes per run (data/logs/swarm_cognition/run_<run_id>.json) — a step-by-step
log of architect plans, coder writes, drift alerts, and test outcomes — and
turns them into replay-friendly summaries and timelines. Diffs are computed
on demand from the swarm's own pre-edit backups
(<workspace>/.karl_swarm_backups/<run_id>/...) against the file's current
on-disk content, so they reflect what that run actually changed.
"""

from __future__ import annotations

import difflib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("karl.swarm_replay")

# Cognition node types that map onto a distinct replay step, and the replay
# step "type" bucket each one falls into.
_STEP_TYPE_BY_NODE_TYPE = {
    "architect_plan": "architect",
    "candidates_generated": "coder",
    "winner_selected": "coder",
    "file_written": "coder",
    "file_skipped": "coder",
    "drift_detected": "coder",
    "guidance_injected": "coder",
    "test_result": "tester",
    "layer_finished": "tester",
}


class SwarmReplayManager:
    """Reconstructs historical swarm execution logs and file-level edits."""

    def __init__(self, trace_dir: str = "data/logs/swarm_cognition"):
        # Kept the "trace_dir" name for interface compatibility with the
        # original scaffold, but this reads cognition-graph files, not raw
        # generation traces — those don't carry per-run structure.
        self.trace_dir = Path(trace_dir)

    def list_past_runs(self) -> list[dict[str, Any]]:
        """
        Scan cognition-graph files and return a list of unique swarm run summaries.

        Returns:
            List of dictionaries with run metadata:
            { "run_id": str, "timestamp": str, "objective": str, "steps_count": int, "success": bool }
        """
        logger.info("Scanning for past swarm runs in %s...", self.trace_dir)
        if not self.trace_dir.exists():
            return []

        runs: list[dict[str, Any]] = []
        for path in self.trace_dir.glob("run_*.json"):
            run_id = path.stem[len("run_"):]
            nodes = self._read_nodes(path)
            if nodes is None:
                continue
            runs.append(self._summarize(run_id, nodes, path))

        runs.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
        return runs

    def get_run_details(self, run_id: str) -> dict[str, Any]:
        """
        Retrieve full step-by-step state changes for a specific swarm execution.

        Args:
            run_id: Unique correlation/run ID of the swarm.

        Returns:
            Dictionary containing the reconstructed timeline of Architect and Coder turns:
            {
                "run_id": run_id,
                "objective": str,
                "steps": [
                    {
                        "step_index": int,
                        "type": "architect" | "coder" | "tester",
                        "filepath": str,
                        "prompt": str,
                        "diff": str,
                        "test_output": str,
                        "is_drift": bool
                    }
                ]
            }
        """
        logger.info("Retrieving details for swarm run ID '%s'...", run_id)
        path = self.trace_dir / f"run_{run_id}.json"
        nodes = self._read_nodes(path)
        if nodes is None:
            return {"run_id": run_id, "objective": "", "steps": []}

        objective = ""
        workspace_path: Optional[str] = None
        drifted_filepaths: set[str] = set()
        steps: list[dict[str, Any]] = []

        for index, node in enumerate(nodes):
            node_type = node.get("type")

            if node_type == "run_started":
                objective = str(node.get("objective", ""))
                workspace_path = node.get("workspace_path")
                continue
            if node_type == "architect_plan" and not objective:
                objective = str(node.get("explanation", ""))

            if node_type == "drift_detected":
                drifted_filepaths.add(str(node.get("filepath", "")))

            step_type = _STEP_TYPE_BY_NODE_TYPE.get(node_type)
            if step_type is None:
                continue

            filepath = str(node.get("filepath", ""))
            diff = ""
            if node_type == "file_written" and workspace_path:
                diff = self._compute_diff(workspace_path, filepath, node.get("backup_path", ""))

            prompt = ""
            if node_type == "architect_plan":
                prompt = str(node.get("explanation", ""))
            elif node_type == "guidance_injected":
                prompt = str(node.get("message", ""))

            test_output = ""
            if node_type == "test_result":
                test_output = str(node.get("trace", ""))
            elif node_type == "layer_finished":
                test_output = str(node.get("summary", ""))

            steps.append({
                "step_index": index,
                "type": step_type,
                "filepath": filepath,
                "prompt": prompt,
                "diff": diff,
                "test_output": test_output,
                "is_drift": node_type == "drift_detected" or filepath in drifted_filepaths,
            })

        return {"run_id": run_id, "objective": objective, "steps": steps}

    # ── internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _read_nodes(path: Path) -> Optional[list[dict]]:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read cognition graph %s: %s", path, exc)
            return None
        return data if isinstance(data, list) else None

    @staticmethod
    def _summarize(run_id: str, nodes: list[dict], path: Path) -> dict[str, Any]:
        objective = ""
        success = False
        finished = False
        earliest_ts: Optional[float] = None

        for node in nodes:
            ts = node.get("timestamp")
            if isinstance(ts, (int, float)) and (earliest_ts is None or ts < earliest_ts):
                earliest_ts = ts
            node_type = node.get("type")
            if node_type == "run_started" and node.get("objective"):
                objective = str(node["objective"])
            elif node_type == "architect_plan" and not objective:
                objective = str(node.get("explanation", ""))
            elif node_type == "swarm_finished":
                finished = True
                success = bool(node.get("success"))

        if earliest_ts is not None:
            timestamp = datetime.fromtimestamp(earliest_ts, tz=timezone.utc).isoformat()
        else:
            timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

        return {
            "run_id": run_id,
            "timestamp": timestamp,
            "objective": objective,
            "steps_count": len(nodes),
            "success": success if finished else False,
        }

    @staticmethod
    def _workspace_root_from_backup_path(backup_path: Path) -> Optional[Path]:
        for parent in backup_path.parents:
            if parent.name == ".karl_swarm_backups":
                return parent.parent
        return None

    def _compute_diff(self, workspace_path: str, filepath: str, backup_path: str) -> str:
        """Best-effort unified diff between the swarm's pre-edit backup and the
        file's current on-disk content. Returns "" if either side is unreadable
        (e.g. the workspace has since been cleaned up)."""
        if not filepath:
            return ""
        try:
            current_path = (Path(workspace_path) / filepath).resolve()
            new_text = current_path.read_text(encoding="utf-8", errors="ignore") if current_path.exists() else ""

            backup = Path(backup_path) if backup_path else None
            is_new_file = backup is None or backup.suffix == ".missing" or not backup.exists()
            old_text = "" if is_new_file else backup.read_text(encoding="utf-8", errors="ignore")

            if old_text == new_text:
                return ""

            diff = difflib.unified_diff(
                old_text.splitlines(),
                new_text.splitlines(),
                fromfile=f"a/{filepath}" if not is_new_file else "/dev/null",
                tofile=f"b/{filepath}",
                lineterm="",
            )
            return "\n".join(diff)
        except OSError as exc:
            logger.debug("Could not compute replay diff for %s: %s", filepath, exc)
            return ""
