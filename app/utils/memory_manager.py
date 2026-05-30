import os
import re
import json
from datetime import datetime

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class MemoryManager:
    def __init__(self, sessions_dir="data/sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)

    def save_session(self, chat_history, system_prompt, filename=None):
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{timestamp}.json"
        
        filepath = os.path.join(self.sessions_dir, filename)
        
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
                "children": [_clean_node_dict(c) for c in node.children]
            }

        if isinstance(chat_history, SessionTree):
            serialized_history = {
                "root": _clean_node_dict(chat_history.root),
                "current_id": chat_history.current_id
            }
        else:
            # Strip <think>...</think> blocks from assistant messages (flat list fallback)
            cleaned = []
            for msg in chat_history:
                if msg.get("role") == "assistant":
                    content = _THINK_RE.sub("", msg.get("content", "")).strip()
                    cleaned.append({**msg, "content": content})
                else:
                    cleaned.append(msg)
            serialized_history = cleaned
        
        data = {
            "system_prompt": system_prompt,
            "chat_history": serialized_history
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        return filename

    def load_session(self, filename):
        filepath = os.path.join(self.sessions_dir, filename)
        if not os.path.exists(filepath):
            return None, None
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        sys_prompt = data.get("system_prompt", "")
        raw_history = data.get("chat_history", [])
        
        from app.utils.session_tree import SessionTree
        if isinstance(raw_history, dict) and "root" in raw_history:
            history = SessionTree.from_dict(raw_history)
        else:
            # Convert list of dicts to a SessionTree
            history = SessionTree()
            for msg in raw_history:
                history.add_message(msg.get("role", "user"), msg.get("content", ""))
                
        return sys_prompt, history

    def list_sessions(self):
        return [f for f in os.listdir(self.sessions_dir) if f.endswith(".json")]
