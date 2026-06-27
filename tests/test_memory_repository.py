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

def test_memory_manager_with_mock_repository():
    mock_repo = MockInMemoryRepository()
    manager = MemoryManager(sessions_dir="dummy/dir", repository=mock_repo)

    # 1. Test save_session
    flat_history = [
        {"role": "user", "content": "hello"}
    ]
    filename = manager.save_session(flat_history, "sys_prompt", filename="test_session.json")
    assert filename == "test_session.json"
    assert "test_session.json" in mock_repo.store

    # 2. Test list_sessions
    sessions = manager.list_sessions()
    assert "test_session.json" in sessions

    # 3. Test load_session
    sys_prompt, history = manager.load_session("test_session.json")
    assert sys_prompt == "sys_prompt"
    active_path = history.get_active_path()
    assert len(active_path) == 1
    assert active_path[0].content == "hello"

    # 4. Test autosave
    manager.save_autosave_checkpoint(history, "workbench")
    assert "autosave_active.json" in mock_repo.store
    
    checkpoint = manager.load_autosave_checkpoint()
    assert checkpoint["active_workspace"] == "workbench"

    # 5. Test clear autosave
    manager.clear_autosave_checkpoint()
    assert "autosave_active.json" not in mock_repo.store
