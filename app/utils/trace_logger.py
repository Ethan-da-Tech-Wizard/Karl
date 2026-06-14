import logging
import os
import json
import uuid
import gzip
import shutil
import threading
from datetime import datetime, timezone

logger = logging.getLogger("karl.trace_logger")


_MAX_BYTES = 50 * 1024 * 1024  # 50 MB per file before rotation


class TraceLogger:
    def __init__(self, log_dir: str = "data/logs/traces", archive_dir: str = "data/logs/archive"):
        self.log_dir = log_dir
        self.archive_dir = archive_dir
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
        self._session_id = str(uuid.uuid4())
        self._log_file: str | None = None
        self._lock = threading.Lock()
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
        """Delete trace log files and archives older than log_retention_days."""
        try:
            from app.engine import config_store
            config = config_store.get_ui_config()
            retention_days = config.get("log_retention_days", 30)
        except Exception:
            retention_days = 30

        if not retention_days or retention_days <= 0:
            return

        now = datetime.now(timezone.utc)
        
        # Prune both live traces and compressed archives
        for directory in [self.log_dir, self.archive_dir]:
            if not os.path.exists(directory):
                continue
            for f in os.listdir(directory):
                if (f.startswith("trace_") and (f.endswith(".jsonl") or f.endswith(".jsonl.gz"))):
                    path = os.path.join(directory, f)
                    try:
                        mtime = os.path.getmtime(path)
                        mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        age_days = (now - mtime_dt).days
                        if age_days > retention_days:
                            os.remove(path)
                            logger.info(f"Pruned old log file: {f}")
                    except Exception as e:
                        logger.warning(f"Failed to prune log file {f}: {e}")

    def _archive_log(self, file_path: str):
        """Compresses a rotated log file to Gzip and moves it to the archive."""
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return

        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            filename = os.path.basename(file_path)
            archive_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.jsonl.gz"
            archive_path = os.path.join(self.archive_dir, archive_filename)

            logger.info(f"Archiving log {filename} to {archive_filename}...")
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Verify the archive exists and is non-empty before deleting original
            if os.path.exists(archive_path) and os.path.getsize(archive_path) > 0:
                os.remove(file_path)
                logger.info(f"Successfully archived and removed {filename}")
            else:
                logger.error(f"Failed to verify archive {archive_path}. Keeping original.")
        except Exception as e:
            logger.error(f"Failed to archive log file {file_path}: {e}")

    def _refresh_path(self):
        with self._lock:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            base = os.path.join(self.log_dir, f"trace_{date_str}.jsonl")
            max_bytes = self._get_max_bytes()
            
            # Check if base needs archival
            if os.path.exists(base) and os.path.getsize(base) >= max_bytes:
                self._archive_log(base)
            
            if not os.path.exists(base):
                self._log_file = base
                return

            # If base still exists (because size was < max or archive failed), use it
            if os.path.getsize(base) < max_bytes:
                self._log_file = base
                return
            
            # Fallback rotation if archival failed or file is somehow still too large
            i = 1
            while True:
                candidate = os.path.join(self.log_dir, f"trace_{date_str}_{i}.jsonl")
                if os.path.exists(candidate) and os.path.getsize(candidate) >= max_bytes:
                    self._archive_log(candidate)
                    
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
        
        # _refresh_path handles locking internally
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

        with self._lock:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return self._log_file

    def update_last_entry_feedback(self, feedback: str, corrected_response: str | None = None):
        """
        Rewrite the last line of the active jsonl file with the updated feedback
        and corrected response.
        """
        # _refresh_path handles locking internally
        self._refresh_path()
        
        with self._lock:
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

