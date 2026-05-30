import os
import json
import uuid
from datetime import datetime, timezone

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB per file before rotation


class TraceLogger:
    def __init__(self, log_dir: str = "data/logs/traces"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self._session_id = str(uuid.uuid4())
        self._log_file: str | None = None
        self._refresh_path()

    def _refresh_path(self):
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base = os.path.join(self.log_dir, f"trace_{date_str}.jsonl")
        if not os.path.exists(base):
            self._log_file = base
            return
        # Rotate if file exceeds size limit
        if os.path.getsize(base) < _MAX_BYTES:
            self._log_file = base
            return
        i = 1
        while True:
            candidate = os.path.join(self.log_dir, f"trace_{date_str}_{i}.jsonl")
            if not os.path.exists(candidate) or os.path.getsize(candidate) < _MAX_BYTES:
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
    ) -> str:
        """
        Logs one generation event. Returns the path of the log file written to.

        The JSONL schema is compatible with Unsloth SFT and DPO export.
        """
        self._refresh_path()

        entry = {
            "id": str(uuid.uuid4()),
            "session_id": self._session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timing": {
                "total_seconds": round(execution_time, 3),
            },
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
