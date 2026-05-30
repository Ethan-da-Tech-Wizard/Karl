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
        
        # Strip <think>...</think> blocks from assistant messages
        cleaned = []
        for msg in chat_history:
            if msg.get("role") == "assistant":
                content = _THINK_RE.sub("", msg.get("content", "")).strip()
                cleaned.append({**msg, "content": content})
            else:
                cleaned.append(msg)
        
        data = {
            "system_prompt": system_prompt,
            "chat_history": cleaned
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
        return [f for f in os.listdir(self.sessions_dir) if f.endswith(".json")]
