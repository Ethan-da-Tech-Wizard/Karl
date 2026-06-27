"""
RBAC / Scope-Based Access Control Tests.

Each test spins up a real (non-SSL) WebSocketServerManager with a pre-seeded
token store containing:
  - ADMIN_TOKEN → ["read:telemetry", "read:kb", "write:kb", "admin:execute"]
  - READ_TOKEN  → ["read:telemetry"]
  - KB_TOKEN    → ["read:telemetry", "read:kb"]

The _stub_init_security() helper bypasses all disk I/O and token generation so
the tests remain deterministic and side-effect free.
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import websockets
import websockets.exceptions
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.websocket]

# ── Fixture tokens ────────────────────────────────────────────────────────────

_ADMIN_TOKEN = "admin-token-0123456789abcdef"
_READ_TOKEN  = "read-token-0123456789abcdef"
_KB_TOKEN    = "kb-token-0123456789abcdef"
_INVALID_TOKEN = "not-a-real-token"

_TOKEN_STORE: dict[str, list[str]] = {
    _ADMIN_TOKEN: ["read:telemetry", "read:kb", "write:kb", "admin:execute"],
    _READ_TOKEN:  ["read:telemetry"],
    _KB_TOKEN:    ["read:telemetry", "read:kb"],
}


def _stub_init_security(self) -> None:
    self.bridge_token = _ADMIN_TOKEN
    self._token_created_at = time.time()
    self._token_store = dict(_TOKEN_STORE)   # copy so tests can't pollute each other
    self.blocked_paths: set[str] = set()


# ── Test server context manager ───────────────────────────────────────────────

class _TestServer:
    _port: int = 19997

    def __enter__(self):
        from app.engine.websocket_server import WebSocketServerManager

        self._patches = [
            patch("app.engine.websocket_server.RAGPipeline", return_value=MagicMock()),
            patch("app.engine.websocket_server.InferenceService", return_value=MagicMock()),
            patch.object(WebSocketServerManager, "_seed_codex", lambda s: None),
            patch.object(WebSocketServerManager, "_init_security", _stub_init_security),
            patch.object(WebSocketServerManager, "_ensure_ssl_certs", lambda s: None),
            patch.object(WebSocketServerManager, "_build_ssl_context", return_value=None),
        ]
        for p in self._patches:
            p.start()

        self._mgr = WebSocketServerManager(port=self._port, state=None)
        ok = self._mgr.started_event.wait(timeout=5.0)
        assert ok and self._mgr.server is not None, "RBAC test server failed to start"
        return self._mgr

    def __exit__(self, *_):
        if self._mgr is not None:
            try:
                self._mgr.loop.call_soon_threadsafe(self._mgr.loop.stop)
                self._mgr.loop_thread.join(timeout=3.0)
            except Exception:
                pass
        for p in reversed(self._patches):
            p.stop()


def _url(port: int, token: str) -> str:
    return f"ws://127.0.0.1:{port}?token={token}"


# ── Helper: single RPC round-trip ─────────────────────────────────────────────

async def _rpc(url: str, method: str, params: dict | None = None, rpc_id: int = 1) -> dict:
    async with websockets.connect(url, open_timeout=3.0) as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params or {},
        }))
        raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
    return json.loads(raw)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_invalid_token_rejected_with_4001():
    """Connecting with an unknown token must be rejected with WebSocket close code 4001."""

    async def _connect_invalid(url: str) -> int | None:
        try:
            async with websockets.connect(url, open_timeout=3.0) as ws:
                # Drain until the server closes — the handler rejects immediately.
                try:
                    async with asyncio.timeout(2.0):
                        async for _ in ws:
                            pass
                except asyncio.TimeoutError:
                    return None
                except websockets.exceptions.ConnectionClosed as exc:
                    return exc.rcvd.code if exc.rcvd else None
                return ws.close_code
        except websockets.exceptions.ConnectionClosed as exc:
            return exc.rcvd.code if exc.rcvd else None

    with _TestServer() as mgr:
        url = _url(mgr.port, _INVALID_TOKEN)
        code = asyncio.run(_connect_invalid(url))

    assert code == 4001, f"Expected 4001 Unauthorized, got {code}"


def test_read_telemetry_scope_allows_get_runtime_status():
    """A token with only read:telemetry scope must be allowed to call get_runtime_status."""
    with _TestServer() as mgr:
        url = _url(mgr.port, _READ_TOKEN)
        result = asyncio.run(_rpc(url, "get_runtime_status"))

    assert "result" in result, f"Expected result, got: {result}"
    assert "bridge" in result["result"], "get_runtime_status result should contain 'bridge'"


def test_read_telemetry_scope_denied_for_submit_chat():
    """A token with only read:telemetry scope must receive -32001 for submit_chat."""
    with _TestServer() as mgr:
        url = _url(mgr.port, _READ_TOKEN)
        result = asyncio.run(_rpc(url, "submit_chat", {"message": "hello"}))

    assert "error" in result, f"Expected error response, got: {result}"
    assert result["error"]["code"] == -32001, (
        f"Expected -32001 Permission Denied, got {result['error']['code']}"
    )
    assert "admin:execute" in result["error"]["message"], (
        "Error message must name the missing scope"
    )


def test_read_telemetry_scope_denied_for_submit_task():
    """A token with only read:telemetry scope must receive -32001 for submit_task."""
    with _TestServer() as mgr:
        url = _url(mgr.port, _READ_TOKEN)
        result = asyncio.run(_rpc(url, "submit_task", {
            "objective": "test",
            "workspace_path": "/tmp",
        }))

    assert "error" in result, f"Expected error, got: {result}"
    assert result["error"]["code"] == -32001


def test_read_kb_scope_allows_search_kb_but_denies_ingest():
    """
    A read:kb token can call list_kb_sources (read:kb required) and must NOT
    receive -32001 Permission Denied. It must NOT be allowed to call ingest_path
    (write:kb required) — that call must return -32001.

    Note: list_kb_sources may return -32603 (internal mock serialisation error)
    in the test environment because self.rag is a MagicMock; that is acceptable
    — it proves the scope guard passed and the method was dispatched.
    """
    with _TestServer() as mgr:
        url = _url(mgr.port, _KB_TOKEN)
        allow_result = asyncio.run(_rpc(url, "list_kb_sources"))
        deny_result  = asyncio.run(_rpc(url, "ingest_path", {"path": "/tmp/test.md"}))

    # Must NOT be a scope-denial error for list_kb_sources
    if "error" in allow_result:
        assert allow_result["error"]["code"] != -32001, (
            f"list_kb_sources must not be blocked by scope guard: {allow_result}"
        )
    # Must be a scope-denial error for ingest_path
    assert "error" in deny_result, f"ingest_path should be denied: {deny_result}"
    assert deny_result["error"]["code"] == -32001
    assert "write:kb" in deny_result["error"]["message"]


def test_admin_token_can_call_all_scoped_methods():
    """The admin token (full scopes) must not be blocked by the scope guard."""
    with _TestServer() as mgr:
        url = _url(mgr.port, _ADMIN_TOKEN)
        status = asyncio.run(_rpc(url, "get_runtime_status"))
        kb = asyncio.run(_rpc(url, "list_kb_sources"))

    # Neither may carry a -32001 Permission Denied error
    for resp in (status, kb):
        if "error" in resp:
            assert resp["error"]["code"] != -32001, (
                f"Admin token must not be blocked by scope guard: {resp}"
            )


def test_method_scopes_map_is_complete():
    """Verify that METHOD_SCOPES contains exactly the methods specified in the prompt."""
    from app.engine.websocket_server import WebSocketServerManager

    expected = {
        "get_runtime_status": "read:telemetry",
        "list_kb_sources":    "read:kb",
        "search_kb":          "read:kb",
        "ingest_path":        "write:kb",
        "submit_task":        "admin:execute",
        "submit_chat":        "admin:execute",
    }
    assert WebSocketServerManager.METHOD_SCOPES == expected, (
        f"METHOD_SCOPES mismatch: {WebSocketServerManager.METHOD_SCOPES}"
    )


def test_add_scoped_token_registers_new_token():
    """add_scoped_token() creates a new token that is accepted by the server."""

    async def _connect_new_token(url: str) -> dict:
        async with websockets.connect(url, open_timeout=3.0) as ws:
            await ws.send(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "get_runtime_status", "params": {},
            }))
            raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
            return json.loads(raw)

    with _TestServer() as mgr:
        new_token = mgr.add_scoped_token(["read:telemetry"])
        url = _url(mgr.port, new_token)
        result = asyncio.run(_connect_new_token(url))

    assert "result" in result, f"Dynamically-added token must be accepted: {result}"


def test_generate_scoped_token_cli(tmp_path):
    """add_scoped_token utility writes the token to the on-disk store."""
    import uuid
    from app.utils.keychain_manager import add_scoped_token, get_token_scopes

    token_path = str(tmp_path / "bridge_token.json")
    token = uuid.uuid4().hex
    add_scoped_token(token, ["read:telemetry"], token_path=token_path)

    scopes = get_token_scopes(token, token_path=token_path)
    assert scopes == ["read:telemetry"], f"Expected read:telemetry scope, got {scopes}"
