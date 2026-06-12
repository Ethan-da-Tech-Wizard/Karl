import logging
import os
import json
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("karl.trace_logger")


_MAX_BYTES = 50 * 1024 * 1024  # 50 MB per file before rotation


class TraceLogger:
    def __init__(self, log_dir: str = "data/logs/traces"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self._session_id = str(uuid.uuid4())
        self._log_file: str | None = None
        self._refresh_path()
        self.prune_logs()

    def _get_max_bytes(self) -> int:
        global _MAX_BYTES
        if _MAX_BYTES != 50 * 1024 * 1024:
            return _MAX_BYTES
        try:
            from app.engine import config_store
            config = config_store.get_ui_config()
            size_mb = config.get("log_rotation_size_mb", 10)
            return size_mb * 1024 * 1024
        except Exception:
            return 10 * 1024 * 1024

    def prune_logs(self):
        """Delete trace log files older than log_retention_days."""
        try:
            from app.engine import config_store
            config = config_store.get_ui_config()
            retention_days = config.get("log_retention_days", 30)
        except Exception:
            retention_days = 30

        if not retention_days or retention_days <= 0:
            return

        now = datetime.now(timezone.utc)
        for f in os.listdir(self.log_dir):
            if f.startswith("trace_") and f.endswith(".jsonl"):
                path = os.path.join(self.log_dir, f)
                try:
                    mtime = os.path.getmtime(path)
                    mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                    age_days = (now - mtime_dt).days
                    if age_days > retention_days:
                        os.remove(path)
                except Exception as e:
                    logger.warning(f"Failed to prune log file {f}: {e}")

    def _refresh_path(self):
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base = os.path.join(self.log_dir, f"trace_{date_str}.jsonl")
        max_bytes = self._get_max_bytes()
        if not os.path.exists(base):
            self._log_file = base
            return
        # Rotate if file exceeds size limit
        if os.path.getsize(base) < max_bytes:
            self._log_file = base
            return
        i = 1
        while True:
            candidate = os.path.join(self.log_dir, f"trace_{date_str}_{i}.jsonl")
            if not os.path.exists(candidate) or os.path.getsize(candidate) < max_bytes:
                self._log_file = candidate
                return
            i += 1

    def log_generation(
        self,
        compiled_prompt: str,
        hyperparams: dict,
        raw_output: str,
        parsed_thought: str,
        parsed_response: str,
        execution_time: float,
        rag_context: list | None = None,
        workflow: str = "general_chat",
        template: str = "reasoning_minimal",
        feedback: str = "none",
        corrected_response: str | None = None,
        model_name: str | None = None,
        adapter_name: str | None = None,
        diagnostics: dict | None = None,
    ) -> str:
        """
        Logs one generation event. Returns the path of the log file written to.

        The JSONL schema is compatible with Unsloth SFT and DPO export.
        """
        self.prune_logs()
        self._refresh_path()

        timing = {
            "total_seconds": round(execution_time, 3),
        }
        if diagnostics:
            timing.update({
                "prefill_seconds": round(diagnostics.get("prefill_time", 0), 3),
                "prefill_tps": round(diagnostics.get("prefill_tps", 0), 1),
                "generation_seconds": round(diagnostics.get("generation_time", 0), 3),
                "generation_tps": round(diagnostics.get("generation_tps", 0), 1),
                "prompt_tokens": diagnostics.get("prompt_tokens", 0),
                "generation_tokens": diagnostics.get("generation_tokens", 0),
                "total_tps": round(diagnostics.get("total_tps", 0), 1),
            })

        entry = {
            "id": str(uuid.uuid4()),
            "session_id": self._session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timing": timing,
            "model": model_name or "unknown",
            "adapter": adapter_name,
            "workflow": workflow,
            "template": template,
            "hyperparams": hyperparams,
            "system_prompt": "",          # populated by caller if desired
            "compiled_prompt": compiled_prompt,
            "thinking": parsed_thought,
            "response": parsed_response,
            "raw_output": raw_output,
            "rag_chunks": rag_context or [],
            "feedback": feedback,          # none | thumbs_up | thumbs_down | corrected
            "corrected_response": corrected_response,
        }

        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return self._log_file

    def update_last_entry_feedback(self, feedback: str, corrected_response: str | None = None):
        """
        Rewrite the last line of the active jsonl file with the updated feedback
        and corrected response.
        """
        self._refresh_path()
        if not self._log_file or not os.path.exists(self._log_file):
            return

        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if not lines:
                return

            last_line = lines[-1].strip()
            if not last_line:
                return

            entry = json.loads(last_line)
            entry["feedback"] = feedback
            if corrected_response is not None:
                entry["corrected_response"] = corrected_response

            lines[-1] = json.dumps(entry, ensure_ascii=False) + "\n"

            with open(self._log_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            logger.warning(f"Error updating feedback: {e}")

