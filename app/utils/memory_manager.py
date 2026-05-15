import os
import json
import shutil
from datetime import datetime


class MemoryManager:
    def __init__(self, sessions_dir="data/sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)

    def save_session(self, chat_history, system_prompt, filename=None):
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{timestamp}.json"

        filepath = os.path.join(self.sessions_dir, filename)
        data = {
            "system_prompt": system_prompt,
            "chat_history": chat_history,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return filename

    def load_session(self, filename):
        filepath = os.path.join(self.sessions_dir, filename)
        if not os.path.exists(filepath):
            return None, []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("system_prompt", ""), data.get("chat_history", [])

    def list_sessions(self):
        return sorted(
            [f for f in os.listdir(self.sessions_dir) if f.endswith(".json")]
        )

    # ── M16: Session Branching ────────────────────────────────────────────────

    def fork_session(self, source_filename: str) -> str:
        """
        Copy source_filename to a new branch file.

        The fork inherits the full history up to the fork point, so the user
        can diverge without losing the original thread.

        Returns the new filename.
        """
        sys_prompt, history = self.load_session(source_filename)
        if sys_prompt is None:
            raise FileNotFoundError(f"Session not found: {source_filename}")

        base = source_filename.replace(".json", "")
        # Strip existing _fork_* suffix so chains don't grow unbounded
        if "_fork_" in base:
            base = base.rsplit("_fork_", 1)[0]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{base}_fork_{timestamp}.json"
        self.save_session(history, sys_prompt, new_filename)
        return new_filename

    def save_version(self, chat_history, system_prompt, base_filename: str | None, tag: str) -> str:
        """
        Snapshot the current state with a human-readable version tag.

        Example: save_version(history, sys, "session_20240501.json", "v2-with-rag")
        Returns the new filename.
        """
        if base_filename:
            stem = base_filename.replace(".json", "")
            if "_fork_" in stem:
                stem = stem.rsplit("_fork_", 1)[0]
        else:
            stem = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        safe_tag = tag.replace(" ", "_").replace("/", "-")[:32]
        new_filename = f"{stem}_v_{safe_tag}.json"
        return self.save_session(chat_history, system_prompt, new_filename)
