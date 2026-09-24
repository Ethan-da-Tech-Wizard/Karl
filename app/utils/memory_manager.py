import os
import re
from datetime import datetime
from app.repository.session_repository import SessionRepository

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class MemoryManager:
    def __init__(self, sessions_dir="data/sessions", repository=None):
        self.sessions_dir = sessions_dir
        self.autosave_filename = "autosave_active.json"
        self.repository = repository or SessionRepository(sessions_dir)

    @property
    def autosave_path(self) -> str:
        return os.path.join(self.sessions_dir, self.autosave_filename)

    def _serialize_history(self, chat_history):
        from app.utils.session_tree import SessionTree, SessionNode
        
        def _clean_node_dict(node: SessionNode) -> dict:
            content = node.content
            if node.role == "assistant":
                content = _THINK_RE.sub("", content).strip()
            return {
                "id": node.id,
                "role": node.role,
                "content": content,
                "thought": node.thought,
                "attachments": getattr(node, "attachments", []),
                "children": [_clean_node_dict(c) for c in node.children]
            }

        if isinstance(chat_history, SessionTree):
            return {
                "root": _clean_node_dict(chat_history.root),
                "current_id": chat_history.current_id
            }

        cleaned = []
        for msg in chat_history or []:
            if msg.get("role") == "assistant":
                content = _THINK_RE.sub("", msg.get("content", "")).strip()
                cleaned.append({**msg, "content": content})
            else:
                cleaned.append(msg)
        return cleaned

    def save_autosave_checkpoint(
        self,
        session_tree,
        active_workspace,
        model_settings: dict | None = None,
        active_tab_state: dict | None = None,
    ) -> str:
        """Atomically persist the active workspace and session tree for crash recovery."""
        now = datetime.now().isoformat()
        payload = {
            "checkpoint_type": "autosave_active",
            "timestamp": now,
            "updated_time": now,
            "active_workspace": active_workspace,
            "active_tab_state": active_tab_state or {},
            "model_settings": model_settings or {},
            "session_tree": self._serialize_history(session_tree),
        }
        self.repository.save(self.autosave_filename, payload)
        return self.autosave_path

    def load_autosave_checkpoint(self) -> dict | None:
        return self.repository.get(self.autosave_filename)

    def clear_autosave_checkpoint(self):
        self.repository.delete(self.autosave_filename)
        self.repository.delete(self.autosave_filename + ".tmp")

    def load_swarm_history(self):
        history = self.repository.get("../swarm_history.json")
        return history if isinstance(history, list) else []

    def save_swarm_history(self, history):
        self.repository.save("../swarm_history.json", history[:10])

