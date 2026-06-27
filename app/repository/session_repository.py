import os
import json


class SessionRepository:
    """Persistent store for session trees, one JSON file per session.

    Not thread-safe: callers must serialise concurrent saves to the same
    session_id if needed.
    """

    def __init__(self, sessions_dir="data/sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)

    def save(self, session_id: str, session_tree: dict) -> None:
        """Atomically persist *session_tree* to disk via a `.tmp` rename.

        The write goes to ``<filepath>.tmp`` first, then ``os.replace()``
        swaps it in place.  This guarantees the file is never half-written
        even if the process is killed mid-flush.

        Not thread-safe: concurrent saves for the same session_id will race.
        """
        filepath = os.path.join(self.sessions_dir, session_id)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        tmp_path = filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(session_tree, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, filepath)

    def get(self, session_id: str) -> dict | None:
        """Load and return a session dict, or None if missing or unparseable."""
        filepath = os.path.join(self.sessions_dir, session_id)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_all(self) -> list[dict]:
        """Return metadata for every session JSON file in the store.

        Each entry is ``{"filename": str, "data": dict, "mtime": float}``.
        ``autosave_active.json`` is excluded.  Parse failures are silently
        skipped.  Not thread-safe.
        """
        if not os.path.exists(self.sessions_dir):
            return []
        sessions = []
        for f in os.listdir(self.sessions_dir):
            if f.endswith(".json") and f != "autosave_active.json":
                filepath = os.path.join(self.sessions_dir, f)
                try:
                    mtime = os.path.getmtime(filepath)
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)
                    sessions.append({
                        "filename": f,
                        "data": data,
                        "mtime": mtime
                    })
                except Exception:
                    pass
        return sessions

    def delete(self, session_id: str) -> bool:
        """Remove the session file.  Returns True on success, False if absent."""
        filepath = os.path.join(self.sessions_dir, session_id)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception:
                pass
        return False
