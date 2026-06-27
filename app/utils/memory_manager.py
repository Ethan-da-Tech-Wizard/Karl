import os
import re
import time
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

    def save_session(self, chat_history, system_prompt, filename=None, last_model="unknown", adapter_name=None, message_count=0):
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{timestamp}.json"
        
        serialized_history = self._serialize_history(chat_history)
        
        data = {
            "system_prompt": system_prompt,
            "chat_history": serialized_history,
            "metadata": {
                "last_model": last_model or "unknown",
                "adapter_name": adapter_name,
                "message_count": message_count,
                "updated_time": datetime.now().isoformat()
            }
        }
        
        self.repository.save(filename, data)
        return filename

    def load_session(self, filename):
        data = self.repository.get(filename)
        if not data:
            return None, None
            
        sys_prompt = data.get("system_prompt", "")
        raw_history = data.get("chat_history", [])
        
        from app.utils.session_tree import SessionTree
        if isinstance(raw_history, dict) and "root" in raw_history:
            history = SessionTree.from_dict(raw_history)
        else:
            # Convert list of dicts to a SessionTree
            history = SessionTree()
            for msg in raw_history:
                history.add_message(
                    msg.get("role", "user"),
                    msg.get("content", ""),
                    attachments=msg.get("attachments"),
                )
                
        return sys_prompt, history

    def list_sessions(self):
        return [session["filename"] for session in self.repository.list_all()]

    def list_sessions_with_metadata(self):
        sessions = []
        for session in self.repository.list_all():
            f = session["filename"]
            data = session["data"]
            mtime = session.get("mtime", time.time())
            
            try:
                meta = data.get("metadata", {})
                updated_time = meta.get("updated_time", datetime.fromtimestamp(mtime).isoformat())
                
                # Count messages
                msg_count = 0
                raw_history = data.get("chat_history", [])
                if isinstance(raw_history, dict) and "root" in raw_history:
                    def _count_nodes(node):
                        return 1 + sum(_count_nodes(c) for c in node.get("children", []))
                    # Subtract 1 to exclude system root node
                    msg_count = max(0, _count_nodes(raw_history["root"]) - 1)
                else:
                    msg_count = len(raw_history)
                    
                sessions.append({
                    "filename": f,
                    "last_model": meta.get("last_model", "unknown"),
                    "adapter_name": meta.get("adapter_name"),
                    "message_count": meta.get("message_count", msg_count),
                    "updated_time": updated_time
                })
            except Exception:
                try:
                    updated_time = datetime.fromtimestamp(mtime).isoformat()
                except Exception:
                    updated_time = datetime.now().isoformat()
                sessions.append({
                    "filename": f,
                    "last_model": "unknown",
                    "adapter_name": None,
                    "message_count": 0,
                    "updated_time": updated_time
                })
        return sorted(sessions, key=lambda x: x["updated_time"], reverse=True)

    def load_swarm_history(self):
        history = self.repository.get("../swarm_history.json")
        return history if isinstance(history, list) else []

    def save_swarm_history(self, history):
        self.repository.save("../swarm_history.json", history[:10])

