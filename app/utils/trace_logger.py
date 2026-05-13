import os
import json
from datetime import datetime, timezone

class TraceLogger:
    def __init__(self, log_dir="data/logs/traces"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        # We use a single JSONL file for the session or daily logs
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.log_file = os.path.join(self.log_dir, f"trace_{date_str}.jsonl")

    def log_generation(self, compiled_prompt, hyperparams, raw_output, parsed_thought, parsed_response, execution_time, rag_context=None):
        """
        Logs a single generation event to disk as a JSONL entry.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time_seconds": execution_time,
            "hyperparameters": hyperparams,
            "rag_context_used": rag_context or [],
            "compiled_prompt": compiled_prompt,
            "raw_output": raw_output,
            "parsed_thought": parsed_thought,
            "parsed_response": parsed_response
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        
        return self.log_file
