import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.memory_manager import MemoryManager

class MockInMemoryRepository:
    def __init__(self):
        self.store = {}

    def save(self, session_id: str, session_tree: dict) -> None:
        self.store[session_id] = session_tree

    def get(self, session_id: str) -> dict | None:
        return self.store.get(session_id)

    def list_all(self) -> list[dict]:
        return [
            {"filename": sid, "data": data, "mtime": 123456789.0}
            for sid, data in self.store.items()
            if sid != "autosave_active.json"
        ]

    def delete(self, session_id: str) -> bool:
        if session_id in self.store:
            del self.store[session_id]
            return True
        return False

def test_memory_manager_autosave_with_mock_repository():
    # Session save/load/list moved entirely to SessionTree.save()/load()/
    # list_sessions() (see tests/test_session_tree.py) -- MemoryManager no
    # longer has its own copy of that logic, only the autosave checkpoint
    # and swarm-history helpers below.
    mock_repo = MockInMemoryRepository()
    manager = MemoryManager(sessions_dir="dummy/dir", repository=mock_repo)

    from app.utils.session_tree import SessionTree
    history = SessionTree()
    history.add_message("user", "hello")

    manager.save_autosave_checkpoint(history, "workbench")
    assert "autosave_active.json" in mock_repo.store

    checkpoint = manager.load_autosave_checkpoint()
    assert checkpoint["active_workspace"] == "workbench"

    manager.clear_autosave_checkpoint()
    assert "autosave_active.json" not in mock_repo.store
