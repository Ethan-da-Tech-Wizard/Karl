from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_thoughts(node_dict: dict) -> dict:
    """Recursively strip reasoning content from a SessionNode dict before it's
    written to disk. AGENTS.md documents that saved sessions never persist the
    model's raw <think> trace (see memory_manager._serialize_history) -- this
    is the SessionTree-side equivalent, since SessionTree.save() is the path
    actual sessions are written through, not MemoryManager.
    """
    if node_dict.get("role") == "assistant":
        node_dict["content"] = _THINK_RE.sub("", node_dict.get("content") or "").strip()
        node_dict["thought"] = None
    for child in node_dict.get("children", []):
        _strip_thoughts(child)
    return node_dict


@dataclass(frozen=True)
class SessionTreeStats:
    total_nodes: int
    message_nodes: int
    leaf_count: int
    max_depth: int

class SessionNode:
    def __init__(
        self,
        role: str,
        content: str,
        node_id: str = None,
        children: list = None,
        parent: 'SessionNode' = None,
        thought: str = None,
        attachments: list | None = None,
    ):
        self.role = role
        self.content = content
        self.id = node_id or str(uuid.uuid4())
        self.children = children or []
        self.parent = parent
        self.thought = thought
        self.attachments = attachments or []

    def add_child(
        self,
        role: str,
        content: str,
        node_id: str = None,
        attachments: list | None = None,
        thought: str = None,
    ) -> 'SessionNode':
        child = SessionNode(role, content, node_id=node_id, parent=self, attachments=attachments, thought=thought)
        self.children.append(child)
        return child

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "thought": self.thought,
            "children": [c.to_dict() for c in self.children]
        }
        if self.attachments:
            data["attachments"] = self.attachments
        return data

    @classmethod
    def from_dict(cls, data: dict, parent: 'SessionNode' = None) -> 'SessionNode':
        node = cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            node_id=data.get("id"),
            thought=data.get("thought"),
            attachments=data.get("attachments", []),
            parent=parent
        )
        node.children = [cls.from_dict(c, parent=node) for c in data.get("children", [])]
        return node


class SessionTree:
    def __init__(self, root: SessionNode = None, current_node_id: str = None):
        if root is None:
            self.root = SessionNode(role="system", content="Root", node_id="root")
            self.current_id = self.root.id
        else:
            self.root = root
            self.current_id = current_node_id or self.root.id
        
        self.nodes_map = {}
        self._rebuild_maps()

    def _rebuild_maps(self):
        self.nodes_map = {}
        def _walk(node):
            self.nodes_map[node.id] = node
            for child in node.children:
                child.parent = node
                _walk(child)
        _walk(self.root)

    def get_node(self, node_id: str) -> SessionNode | None:
        return self.nodes_map.get(node_id)

    @property
    def current_node(self) -> SessionNode:
        if self.current_id not in self.nodes_map:
            # Fallback if map out of sync
            self._rebuild_maps()
        return self.nodes_map.get(self.current_id, self.root)

    def add_message(self, role: str, content: str, attachments: list | None = None, thought: str = None) -> SessionNode:
        parent = self.current_node
        child = parent.add_child(role, content, attachments=attachments, thought=thought)
        self.nodes_map[child.id] = child
        self.current_id = child.id
        return child

    def branch_from(
        self,
        node_id: str,
        role: str | None = None,
        content: str = "",
        attachments: list | None = None,
        thought: str = None,
    ) -> SessionNode | None:
        """Move to node_id and optionally append a new child as a fresh branch."""
        if not self.set_current_node(node_id):
            return None
        if role is None:
            return self.current_node
        return self.add_message(role, content, attachments=attachments, thought=thought)

    def get_active_path(self) -> list[SessionNode]:
        path = []
        curr = self.current_node
        while curr is not None:
            if curr.id != self.root.id:  # Skip the dummy root
                path.append(curr)
            curr = curr.parent
        path.reverse()
        return path

    def get_active_path_dicts(self) -> list[dict]:
        items = []
        for n in self.get_active_path():
            item = {"role": n.role, "content": n.content, "id": n.id}
            if n.attachments:
                item["attachments"] = n.attachments
            items.append(item)
        return items

    def set_current_node(self, node_id: str) -> bool:
        # Make sure node_id exists, rebuilding maps if needed
        if node_id not in self.nodes_map:
            self._rebuild_maps()
        if node_id in self.nodes_map:
            self.current_id = node_id
            return True
        return False

    def update_current_node_content(self, text: str):
        self.current_node.content = text

    def update_node_content(self, node_id: str, text: str) -> bool:
        node = self.get_node(node_id)
        if node is None:
            return False
        node.content = text
        return True

    def node_depth(self, node_id: str | None = None) -> int:
        node = self.get_node(node_id or self.current_id)
        depth = 0
        while node is not None and node.id != self.root.id:
            depth += 1
            node = node.parent
        return depth

    def leaf_nodes(self) -> list[SessionNode]:
        leaves: list[SessionNode] = []

        def _walk(node: SessionNode):
            message_children = [child for child in node.children if child.id != self.root.id]
            if node.id != self.root.id and not message_children:
                leaves.append(node)
            for child in node.children:
                _walk(child)

        _walk(self.root)
        return leaves

    def stats(self) -> SessionTreeStats:
        total = 0
        message_nodes = 0
        max_depth = 0

        def _walk(node: SessionNode, depth: int):
            nonlocal total, message_nodes, max_depth
            total += 1
            if node.id != self.root.id:
                message_nodes += 1
                max_depth = max(max_depth, depth)
            for child in node.children:
                _walk(child, depth + 1)

        _walk(self.root, 0)
        return SessionTreeStats(
            total_nodes=total,
            message_nodes=message_nodes,
            leaf_count=len(self.leaf_nodes()),
            max_depth=max_depth,
        )

    def active_branch_label(self) -> str:
        path = self.get_active_path()
        if not path:
            return "root"
        leaf = path[-1]
        return f"{leaf.role}:{leaf.id[:8]}"

    def to_dict(self) -> dict:
        return {
            "root": self.root.to_dict(),
            "current_id": self.current_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SessionTree':
        if not data or "root" not in data:
            return cls()
        root = SessionNode.from_dict(data["root"])
        return cls(root, data.get("current_id"))

    def clear(self):
        self.root = SessionNode(role="system", content="Root", node_id="root")
        self.current_id = self.root.id
        self.nodes_map = {self.root.id: self.root}

    def copy(self) -> 'SessionTree':
        return SessionTree.from_dict(self.to_dict())

    # List interface duck-typing helpers
    def __len__(self):
        return len(self.get_active_path())

    def __getitem__(self, index):
        active = self.get_active_path_dicts()
        return active[index]

    def __iter__(self):
        return iter(self.get_active_path_dicts())

    def __bool__(self):
        return len(self.get_active_path()) > 0

    def append(self, msg: dict):
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            raise TypeError("Appended message must be a dict containing 'role' and 'content'")
        self.add_message(msg["role"], msg["content"], attachments=msg.get("attachments"))

    SESSIONS_DIR = "data/sessions"

    def save(self, session_id: str | None = None) -> str:
        """Write this tree to data/sessions/{session_id}.json. Returns the path."""
        import os, json
        os.makedirs(self.SESSIONS_DIR, exist_ok=True)
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())[:8]
        path = os.path.join(self.SESSIONS_DIR, f"{session_id}.json")
        payload = self.to_dict()
        _strip_thoughts(payload["root"])
        payload["session_id"] = session_id
        # Store first user message as preview
        for node_data in payload.get("root", {}).get("children", []):
            if node_data.get("role") == "user":
                payload["preview"] = node_data.get("content", "")[:80]
                break
        import tempfile, os as _os
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        _os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: str) -> tuple['SessionTree', str]:
        """Load a session from disk. Returns (tree, session_id)."""
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        session_id = data.get("session_id", "unknown")
        tree = cls.from_dict(data)
        return tree, session_id

    @classmethod
    def list_sessions(cls) -> list[dict]:
        """Return metadata for all saved sessions, newest first."""
        import os, json
        if not os.path.exists(cls.SESSIONS_DIR):
            return []
        sessions = []
        for fname in sorted(os.listdir(cls.SESSIONS_DIR), reverse=True):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(cls.SESSIONS_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append({
                    "path": path,
                    "session_id": data.get("session_id", fname[:-5]),
                    "preview": data.get("preview", "(empty)"),
                    "mtime": os.path.getmtime(path),
                })
            except Exception:
                pass
        sessions.sort(key=lambda x: x["mtime"], reverse=True)
        return sessions

    def delete_session_file(self, path: str):
        import os
        if os.path.exists(path):
            os.remove(path)
