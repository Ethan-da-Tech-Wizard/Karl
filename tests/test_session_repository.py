import os
import sys
import json
import pytest

# Ensure parent directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repository.session_repository import SessionRepository


def test_session_repository_lifecycle(tmp_path):
    sessions_dir = str(tmp_path / "sessions")
    repo = SessionRepository(sessions_dir=sessions_dir)

    # Verify that the sessions directory was created successfully
    assert os.path.exists(sessions_dir)

    # 1. Test GET on non-existent session
    assert repo.get("missing_session.json") is None

    # 2. Test SAVE and GET
    test_tree = {
        "root": {
            "id": "root",
            "role": "system",
            "content": "Root",
            "children": [
                {
                    "id": "node-1",
                    "role": "user",
                    "content": "hello world"
                }
            ]
        }
    }
    repo.save("session_1.json", test_tree)

    # Verify atomic file creation
    filepath = os.path.join(sessions_dir, "session_1.json")
    assert os.path.exists(filepath)

    # Verify contents retrieved match
    loaded = repo.get("session_1.json")
    assert loaded == test_tree

    # 3. Test LIST_ALL filters and error handling
    # Save a second valid session
    repo.save("session_2.json", {"key": "val"})

    # Save autosave_active.json which should be excluded from list_all
    repo.save("autosave_active.json", {"active_workspace": "workbench"})

    # Write a corrupted json file (should be ignored by list_all due to parse failure)
    corrupted_path = os.path.join(sessions_dir, "corrupted.json")
    with open(corrupted_path, "w", encoding="utf-8") as f:
        f.write("{invalid_json_data")

    all_sessions = repo.list_all()

    # Verify list contents
    filenames = [s["filename"] for s in all_sessions]
    assert "session_1.json" in filenames
    assert "session_2.json" in filenames
    assert "autosave_active.json" not in filenames
    assert "corrupted.json" not in filenames
    assert len(all_sessions) == 2

    # Check specific metadata structure
    s1_meta = next(s for s in all_sessions if s["filename"] == "session_1.json")
    assert s1_meta["data"] == test_tree
    assert isinstance(s1_meta["mtime"], float)

    # 4. Test DELETE
    # Delete existing session file
    assert repo.delete("session_1.json") is True
    assert repo.get("session_1.json") is None
    assert os.path.exists(filepath) is False

    # Delete non-existent session file
    assert repo.delete("session_1.json") is False


def test_session_repository_path_traversal(tmp_path):
    sessions_dir = str(tmp_path / "sessions")
    repo = SessionRepository(sessions_dir=sessions_dir)

    # 1. Traversal in save
    with pytest.raises(ValueError, match="Path traversal detected"):
        repo.save("../traversal.json", {"key": "val"})

    with pytest.raises(ValueError, match="Path traversal detected"):
        repo.save("/absolute/path/traversal.json", {"key": "val"})

    with pytest.raises(ValueError, match="invalid session ID"):
        repo.save("..", {"key": "val"})

    # 2. Traversal in get (returns None on ValueError)
    assert repo.get("../traversal.json") is None

    # 3. Traversal in delete (returns False on ValueError)
    assert repo.delete("../traversal.json") is False

