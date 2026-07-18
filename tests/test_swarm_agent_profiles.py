import json

import pytest

from app.engine.swarm_agents import get_tool_schema_block
from app.utils import swarm_agent_profiles as profiles


def test_load_agent_profiles_includes_normalized_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    loaded = profiles.load_agent_profiles()

    assert set(["architect", "coder", "tester"]).issubset(loaded)
    assert loaded["architect"]["builtin"] is True
    assert loaded["coder"]["tools"]["write_files"] is True
    assert loaded["tester"]["tools"]["execute_sandbox"] is True


def test_save_agent_profile_round_trips_and_clamps(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    saved = profiles.save_agent_profile(
        "security_reviewer",
        {
            "name": "Security Reviewer",
            "icon": "SR",
            "system_prompt": "Audit shell and file changes.",
            "temperature": 9.0,
            "context_limit": 64,
            "tools": {"read_files": True, "write_files": False},
        },
    )

    assert saved["temperature"] == 2.0
    assert saved["context_limit"] == 256
    assert saved["tools"]["read_files"] is True
    assert saved["tools"]["execute_sandbox"] is False

    data = json.loads((tmp_path / "data" / "agent_profiles.json").read_text(encoding="utf-8"))
    assert "security_reviewer" in data
    assert profiles.load_agent_profiles()["security_reviewer"]["name"] == "Security Reviewer"


def test_save_agent_profile_rejects_invalid_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError):
        profiles.save_agent_profile("../bad", {"name": "Bad"})


def test_active_profile_map_resolves_role_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profiles.save_agent_profile(
        "strict_coder",
        {
            "name": "Strict Coder",
            "system_prompt": "Only produce minimal edits.",
            "tools": {"read_files": True, "write_files": False},
        },
    )

    active = profiles.active_profile_map({"coder": "strict_coder"})

    assert active["coder"]["name"] == "Strict Coder"
    assert active["architect"]["name"] == "Architect"
    assert active["tester"]["name"] == "Tester"


def test_tool_schema_block_respects_allowed_tool_filter():
    schema = get_tool_schema_block({"read_file"})

    assert "name='read_file'" in schema
    assert "name='write_file'" not in schema
    assert "name='shell_run'" not in schema
