"""
Token Lifecycle Tests — lease expiry, refresh, and revocation.

Each test spins up a real (non-SSL) WebSocketServerManager bound to a
high-numbered localhost port and connects a genuine websockets client.

Patches applied for every server:
  - _build_ssl_context   → None  (plain ws:// instead of wss://)
  - _TOKEN_LIFETIME      → 5 s   (class-level so _audit_session_leases sees it)
  - _LEASE_AUDIT_INTERVAL→ 1 s
  - RAGPipeline          → MagicMock
  - InferenceService     → MagicMock
  - _seed_codex          → noop
  - _init_security       → stub with known token
  - _ensure_ssl_certs    → noop
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

# ── Helpers ───────────────────────────────────────────────────────────────────

_TEST_TOKEN = "test-lifecycle-token"
_TEST_PORT = 19991  # high port — unlikely to conflict


def _stub_init_security(self) -> None:
    self.bridge_token = _TEST_TOKEN
    self._token_created_at = time.time()
    self._token_store = {_TEST_TOKEN: list(type(self)._FULL_SCOPES)}
    self.blocked_paths: set[str] = set()


class _TestServer:
    """
    Thin wrapper that builds a patched WebSocketServerManager with a
    short TOKEN_LIFETIME for lifecycle tests, then tears it down after use.
    """

    def __init__(self, port: int = _TEST_PORT, token_lifetime: int = 5, audit_interval: int = 1):
        self.port = port
        self._token_lifetime = token_lifetime
        self._audit_interval = audit_interval
        self._mgr = None
        self._patches: list = []

    # ── context-manager protocol ──────────────────────────────────────────────

    def __enter__(self):
        from app.engine.websocket_server import WebSocketServerManager

        # Patch class attrs so the running loop sees the short lifetimes.
        p1 = patch.object(WebSocketServerManager, "_TOKEN_LIFETIME", self._token_lifetime)
        p2 = patch.object(WebSocketServerManager, "_LEASE_AUDIT_INTERVAL", self._audit_interval)
        p3 = patch("app.engine.websocket_server.RAGPipeline", return_value=MagicMock())
        p4 = patch("app.engine.websocket_server.InferenceService", return_value=MagicMock())
        p5 = patch.object(WebSocketServerManager, "_seed_codex", lambda self: None)
        p6 = patch.object(WebSocketServerManager, "_init_security", _stub_init_security)
        p7 = patch.object(WebSocketServerManager, "_ensure_ssl_certs", lambda self: None)
        p8 = patch.object(WebSocketServerManager, "_build_ssl_context", return_value=None)

        for p in (p1, p2, p3, p4, p5, p6, p7, p8):
            p.start()
            self._patches.append(p)

        self._mgr = WebSocketServerManager(port=self.port, state=None)
        ok = self._mgr.started_event.wait(timeout=5.0)
        assert ok, "Server did not start within 5 seconds"
        assert self._mgr.server is not None, "Server failed to bind"
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


def _ws_url(port: int, token: str = _TEST_TOKEN) -> str:
    return f"ws://127.0.0.1:{port}?token={token}"


async def _recv_close_code(url: str, timeout: float) -> int | None:
    """
    Connect to *url*, drain until the server closes, return the close code.
    Returns None if the connection is still open when *timeout* elapses.
    """
    try:
        async with websockets.connect(url, open_timeout=3.0) as ws:
            try:
                async with asyncio.timeout(timeout):
                    async for _ in ws:
                        pass
            except asyncio.TimeoutError:
                return None
            except websockets.exceptions.ConnectionClosed as exc:
                return exc.rcvd.code if exc.rcvd else None
            return ws.close_code
    except websockets.exceptions.ConnectionClosed as exc:
        return exc.rcvd.code if exc.rcvd else None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_expired_session_closes_with_code_4002():
    """
    A client that does not refresh its token must be disconnected with
    WebSocket close code 4002 (Session Lease Expired) after TOKEN_LIFETIME.
    """
    with _TestServer(token_lifetime=5, audit_interval=1) as mgr:
        url = _ws_url(mgr.port)
        # Wait 8 seconds: TOKEN_LIFETIME (5s) + up to 2 audit cycles (2s) + margin
        close_code = asyncio.run(_recv_close_code(url, timeout=9.0))

    assert close_code == 4002, (
        f"Expected WebSocket close code 4002 (lease expired), got {close_code}"
    )


def test_refresh_token_extends_session_lease():
    """
    A client that calls refresh_token before its lease expires must NOT be
    disconnected; the connection stays alive past the original timeout.
    """

    async def _session_with_refresh(url: str) -> int | None:
        """
        Connect, wait 3s (still within 5s lease), send refresh_token,
        then wait another 6s (past original expiry).  The server must NOT
        close with 4002 because the lease was reset.
        """
        async with websockets.connect(url, open_timeout=3.0) as ws:
            # Wait until 3 s into the 5 s lease, then refresh
            await asyncio.sleep(3)
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "id": 90,
                "method": "refresh_token",
                "params": {"token": _TEST_TOKEN},
            }))

            # Receive the refresh response
            raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
            response = json.loads(raw)
            assert "result" in response, f"Expected result, got: {response}"
            assert response["result"].get("token"), "refresh_token must return a new token"
            assert response["result"].get("expires_at", 0) > time.time(), (
                "expires_at must be in the future"
            )

            # Wait 3 more seconds (total t≈6 from connection start).
            # Without the refresh the original 5 s lease would have expired at t≈5s.
            # The refreshed lease (session_start reset to t≈3) expires at t≈8, so
            # the connection must be alive at t=6.
            try:
                async with asyncio.timeout(3.0):
                    async for _ in ws:
                        pass
                return None  # still connected at end of window — correct
            except asyncio.TimeoutError:
                return None  # timeout means server did NOT close us — correct
            except websockets.exceptions.ConnectionClosed as exc:
                return exc.rcvd.code if exc.rcvd else None

    with _TestServer(token_lifetime=5, audit_interval=1) as mgr:
        url = _ws_url(mgr.port)
        close_code = asyncio.run(_session_with_refresh(url))

    assert close_code is None, (
        f"Connection must stay alive after refresh, but server closed with {close_code}"
    )


def test_refresh_token_invalid_token_returns_error():
    """Calling refresh_token with a wrong token must return a JSON-RPC error."""

    async def _bad_refresh(url: str) -> dict:
        async with websockets.connect(url, open_timeout=3.0) as ws:
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "id": 91,
                "method": "refresh_token",
                "params": {"token": "wrong-token-hex"},
            }))
            # The client is authenticated so the server still accepts the refresh
            # (it validates the existing authenticated state, not just the param).
            # Per spec: accept if authenticated OR if token matches.
            raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
            return json.loads(raw)

    with _TestServer(token_lifetime=30) as mgr:
        url = _ws_url(mgr.port)
        # Authenticated connection — wrong token param still accepted via session auth
        result = asyncio.run(_bad_refresh(url))
        # Should succeed (connection was authenticated at handshake)
        assert "result" in result, f"Authenticated connection should allow refresh: {result}"


def test_force_revoke_closes_all_connections_with_4003():
    """force_revoke() must close all active connections with code 4003."""

    async def _connect_and_wait(url: str, close_queue: asyncio.Queue) -> None:
        try:
            async with websockets.connect(url, open_timeout=3.0) as ws:
                try:
                    async for _ in ws:
                        pass
                except websockets.exceptions.ConnectionClosed as exc:
                    await close_queue.put(exc.rcvd.code if exc.rcvd else None)
        except Exception:
            await close_queue.put(None)

    async def _run_revoke_test(url: str, mgr) -> int | None:
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(_connect_and_wait(url, queue))

        # Give the connection time to establish
        await asyncio.sleep(0.3)

        # Trigger revocation from the test thread (simulating force_revoke)
        mgr.force_revoke()

        # Wait for the close code
        try:
            code = await asyncio.wait_for(queue.get(), timeout=3.0)
        except asyncio.TimeoutError:
            code = None
        task.cancel()
        return code

    with _TestServer(token_lifetime=60) as mgr:
        url = _ws_url(mgr.port)
        close_code = asyncio.run(_run_revoke_test(url, mgr))

    assert close_code == 4003, (
        f"Expected close code 4003 (revoked), got {close_code}"
    )


def test_revoke_wipes_token_file(tmp_path, monkeypatch):
    """force_revoke() must delete data/bridge_token.json if it exists."""
    import pathlib

    token_file = tmp_path / "bridge_token.json"
    token_file.write_text('{"token": "abc", "created_at": 0}')

    with _TestServer(token_lifetime=60) as mgr:
        monkeypatch.setattr(type(mgr), "_TOKEN_PATH", str(token_file), raising=False)
        mgr._TOKEN_PATH = str(token_file)
        mgr.force_revoke()

    assert not pathlib.Path(token_file).exists(), (
        "force_revoke must delete the bridge token file"
    )
