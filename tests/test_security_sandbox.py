"""
Security sandbox tests — Prompt E

Covers:
  1. Root/admin execution block in main._assert_not_privileged()
  2. Realpath-based sandbox in swarm_agents tool functions
  3. WebSocket _is_safe_path symlink resistance
"""

import os
import sys
import platform
import time
import pytest
from unittest.mock import patch


# ── 1. Root / Administrator Execution Block ───────────────────────────────────

# Importing main triggers torch/faiss loading; defer to the test body via
# import inside the function so collection is fast even if libs are absent.

@pytest.mark.skipif(platform.system() not in ("Linux", "Darwin"), reason="getuid not available on Windows")
def test_root_block_exits_on_getuid_zero():
    """_assert_not_privileged() must call sys.exit(1) when getuid() == 0."""
    with patch("platform.system", return_value="Linux"), \
         patch("os.getuid", return_value=0):
        with pytest.raises(SystemExit) as exc_info:
            from main import _assert_not_privileged
            _assert_not_privileged()
    assert exc_info.value.code == 1


@pytest.mark.skipif(platform.system() not in ("Linux", "Darwin"), reason="getuid not available on Windows")
def test_root_block_allows_normal_user():
    """_assert_not_privileged() must not exit when getuid() > 0."""
    with patch("platform.system", return_value="Linux"), \
         patch("os.getuid", return_value=1000):
        from main import _assert_not_privileged
        # Should complete without raising SystemExit
        _assert_not_privileged()


# ── 2. _safe_workspace_path unit tests ───────────────────────────────────────

from app.engine.swarm_agents import _safe_workspace_path, _SECURITY_BLOCK_MSG


def test_safe_workspace_path_empty_rel_blocked(tmp_path):
    assert _safe_workspace_path(str(tmp_path), "") is None


def test_safe_workspace_path_parent_traversal_blocked(tmp_path):
    result = _safe_workspace_path(str(tmp_path), "../../etc/passwd")
    assert result is None


def test_safe_workspace_path_absolute_injection_blocked(tmp_path):
    result = _safe_workspace_path(str(tmp_path), "/etc/passwd")
    assert result is None


def test_safe_workspace_path_normal_file_allowed(tmp_path):
    result = _safe_workspace_path(str(tmp_path), "src/app.py")
    assert result is not None
    assert result.startswith(str(tmp_path))
    assert result.endswith("src/app.py")


def test_safe_workspace_path_nested_allowed(tmp_path):
    result = _safe_workspace_path(str(tmp_path), "a/b/c/deep.txt")
    assert result is not None
    assert os.path.realpath(str(tmp_path)) in result


def test_safe_workspace_path_symlink_escape_blocked(tmp_path):
    """Symlink inside workspace pointing outside must be blocked."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    evil = workspace / "evil.txt"
    evil.symlink_to("/etc/passwd")

    result = _safe_workspace_path(str(workspace), "evil.txt")
    assert result is None


# ── 3. Tool Function: write_file ──────────────────────────────────────────────

from app.engine.swarm_agents import _tool_write_file, _tool_read_file, _tool_lint_python


def test_tool_write_file_symlink_escape_blocked(tmp_path):
    """write_file with a symlink that resolves outside the workspace must be blocked."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("original content", encoding="utf-8")

    evil = workspace / "evil_write.txt"
    evil.symlink_to(outside_file)

    result = _tool_write_file(str(workspace), {"path": "evil_write.txt", "content": "HACKED"})

    assert result == _SECURITY_BLOCK_MSG
    assert outside_file.read_text(encoding="utf-8") == "original content"


def test_tool_write_file_parent_traversal_blocked(tmp_path):
    outside_file = tmp_path / "sensitive.txt"
    outside_file.write_text("safe", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = _tool_write_file(str(workspace), {"path": "../sensitive.txt", "content": "EVIL"})

    assert result == _SECURITY_BLOCK_MSG
    assert outside_file.read_text(encoding="utf-8") == "safe"


def test_tool_write_file_normal_path_works(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = _tool_write_file(str(workspace), {"path": "subdir/hello.txt", "content": "hello"})

    assert result.startswith("OK:")
    written = (workspace / "subdir" / "hello.txt").read_text(encoding="utf-8")
    assert written == "hello"


# ── 4. Tool Function: read_file ───────────────────────────────────────────────

def test_tool_read_file_symlink_escape_blocked(tmp_path):
    """read_file with a symlink to /etc/passwd must be blocked before any read."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    evil = workspace / "evil.txt"
    evil.symlink_to("/etc/passwd")

    result = _tool_read_file(str(workspace), {"path": "evil.txt"})

    assert result == _SECURITY_BLOCK_MSG


def test_tool_read_file_absolute_path_blocked(tmp_path):
    result = _tool_read_file(str(tmp_path), {"path": "/etc/passwd"})
    assert result == _SECURITY_BLOCK_MSG


def test_tool_read_file_parent_traversal_blocked(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    victim = tmp_path / "victim.txt"
    victim.write_text("secret", encoding="utf-8")

    result = _tool_read_file(str(workspace), {"path": "../victim.txt"})
    assert result == _SECURITY_BLOCK_MSG


def test_tool_read_file_normal_path_works(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "code.py").write_text("x = 1\n", encoding="utf-8")

    result = _tool_read_file(str(workspace), {"path": "code.py"})
    assert "x = 1" in result


# ── 5. Tool Function: lint_python ─────────────────────────────────────────────

def test_tool_lint_python_symlink_escape_blocked(tmp_path):
    """lint_python with a symlink escaping the workspace must be blocked."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    evil = workspace / "evil.py"
    evil.symlink_to("/etc/passwd")

    result = _tool_lint_python(str(workspace), {"path": "evil.py"})
    assert result == _SECURITY_BLOCK_MSG


def test_tool_lint_python_empty_path_blocked(tmp_path):
    result = _tool_lint_python(str(tmp_path), {"path": ""})
    assert result == _SECURITY_BLOCK_MSG


def test_tool_lint_python_normal_path_works(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "ok.py").write_text("x = 1\n", encoding="utf-8")

    result = _tool_lint_python(str(workspace), {"path": "ok.py"})
    # pyflakes returns nothing on clean files
    assert "Security Block" not in result


# ── 6. WebSocket _is_safe_path realpath tests ─────────────────────────────────

class _StubManager:
    """Minimal stub to test _is_safe_path without starting a WebSocket server."""

    from app.engine.websocket_server import WebSocketServerManager as _cls
    _is_safe_path = _cls._is_safe_path

    def __init__(self):
        self.blocked_paths = {"/", "/etc", "/bin", "/sbin", "/root", "/proc", "/sys"}
        user_home = os.path.expanduser("~")
        self.blocked_paths.add(user_home)
        self.blocked_paths.add(os.path.join(user_home, "Desktop"))
        self.blocked_paths.add(os.path.join(user_home, "Downloads"))


def test_is_safe_path_blocks_etc(tmp_path):
    mgr = _StubManager()
    assert mgr._is_safe_path("/etc/passwd") is False


def test_is_safe_path_blocks_empty():
    mgr = _StubManager()
    assert mgr._is_safe_path("") is False


def test_is_safe_path_blocks_symlink_pointing_to_etc(tmp_path):
    """A symlink that resolves to /etc must be blocked."""
    link = tmp_path / "evil_link"
    link.symlink_to("/etc")

    mgr = _StubManager()
    # /etc is in blocked_paths; real path of symlink is /etc → blocked
    assert mgr._is_safe_path(str(link)) is False


def test_is_safe_path_allows_tmp_path(tmp_path):
    """A path in /tmp (not in blocked_paths) should be allowed."""
    mgr = _StubManager()
    result = mgr._is_safe_path(str(tmp_path / "some_project"))
    assert result is True


def test_is_safe_path_allows_project_root():
    """The project's own working directory should always be allowed."""
    mgr = _StubManager()
    project_root = os.getcwd()
    assert mgr._is_safe_path(project_root) is True
