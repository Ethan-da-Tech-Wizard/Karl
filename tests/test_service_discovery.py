"""
Tests for service-discovery: automatic port failover and ~/.karl/service_discovery.json
lifecycle (write on bind, remove on stop).

The WebSocketServerManager is heavily initialised so we patch:
  - RAGPipeline           — avoids SQLite / FAISS setup
  - InferenceService      — already safe with state=None but patch for speed
  - _seed_codex           — reads optional data files
  - _init_security        — reads/writes data/bridge_token.json; we set a stub token
  - _ensure_ssl_certs     — runs openssl; unnecessary in CI
  - _build_ssl_context    — returns None so websockets.serve runs without TLS

websockets.serve is patched per-test to simulate port conflicts at the TCP level.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.websocket]

import asyncio
import json
import socket
import threading
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _noop(self):
    """Replaces heavy __init__ helpers that touch the filesystem."""


def _stub_init_security(self):
    """Sets the minimal security state without touching data/bridge_token.json."""
    self.bridge_token = "test-discovery-token"
    self._token_created_at = 0.0
    self.blocked_paths: set[str] = set()


def _stub_start_loop(self):
    """Create the event loop and a bare run_forever thread — no auto _start_server.

    This lets the test set _DISCOVERY_PATH before manually triggering a bind,
    preventing the background-thread race that makes the path redirect arrive late.
    """
    self.loop = asyncio.new_event_loop()
    self.loop_thread = threading.Thread(target=self.loop.run_forever, daemon=True)
    self.loop_thread.start()


def _build_manager(port: int = 8080):
    """Instantiate a WebSocketServerManager with all side-effects patched out.

    The background loop thread is started but _start_server is NOT called
    automatically — tests trigger exactly one bind via _run_start_server().
    """
    from app.engine.websocket_server import WebSocketServerManager

    with (
        patch("app.engine.websocket_server.RAGPipeline", return_value=MagicMock()),
        patch("app.engine.websocket_server.InferenceService", return_value=MagicMock()),
        patch.object(WebSocketServerManager, "_seed_codex", _noop),
        patch.object(WebSocketServerManager, "_init_security", _stub_init_security),
        patch.object(WebSocketServerManager, "_ensure_ssl_certs", _noop),
        patch.object(WebSocketServerManager, "_build_ssl_context", return_value=None),
        patch.object(WebSocketServerManager, "_start_loop_thread", _stub_start_loop),
    ):
        mgr = WebSocketServerManager(port=port, state=None)
    return mgr


def _wait_started(mgr, timeout: float = 3.0) -> bool:
    """Return True when the manager's start event fires within *timeout* seconds."""
    return mgr.started_event.wait(timeout=timeout)


# ── Fake websockets.serve ─────────────────────────────────────────────────────

def _make_serve_factory(fail_ports: set[int]):
    """
    Return an async factory that raises OSError for ports in *fail_ports*
    and returns a usable mock server otherwise.
    """
    async def _serve(handler, host, port, ssl=None, **kwargs):
        if port in fail_ports:
            raise OSError(98, "Address already in use")
        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()
        return mock_server

    return _serve


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_server_binds_on_default_port_when_free(tmp_path):
    """When the default port is available, the server binds on it."""
    discovery_path = tmp_path / "service_discovery.json"

    with patch("websockets.serve", side_effect=_make_serve_factory(set())):
        mgr = _build_manager(port=8080)
        # Redirect discovery writes to tmp_path
        mgr._DISCOVERY_PATH = discovery_path
        # Trigger _write_service_discovery by running _start_server manually
        mgr.started_event.clear()
        asyncio.run_coroutine_threadsafe(
            _run_start_server(mgr), mgr.loop
        ).result(timeout=3.0)

    assert mgr.port == 8080
    assert mgr.server is not None

    data = json.loads(discovery_path.read_text())
    assert data["active_port"] == 8080
    assert data["token"] == "test-discovery-token"
    assert "bound_at" in data

    mgr.loop.call_soon_threadsafe(mgr.loop.stop)
    mgr.loop_thread.join(timeout=2.0)


async def _run_start_server(mgr):
    """Helper: run _start_server() and capture the result."""
    await mgr._start_server()


def test_port_failover_skips_occupied_port(tmp_path):
    """When port 8080 is in use, the server automatically binds on 8081."""
    discovery_path = tmp_path / "service_discovery.json"

    with patch("websockets.serve", side_effect=_make_serve_factory({8080})):
        mgr = _build_manager(port=8080)
        mgr._DISCOVERY_PATH = discovery_path
        mgr.started_event.clear()
        asyncio.run_coroutine_threadsafe(
            _run_start_server(mgr), mgr.loop
        ).result(timeout=3.0)

    assert mgr.port == 8081, f"Expected 8081, got {mgr.port}"
    assert mgr.server is not None

    data = json.loads(discovery_path.read_text())
    assert data["active_port"] == 8081

    mgr.loop.call_soon_threadsafe(mgr.loop.stop)
    mgr.loop_thread.join(timeout=2.0)


def test_two_concurrent_managers_land_on_different_ports(tmp_path):
    """
    Two WebSocketServerManager instances started concurrently both succeed,
    binding on adjacent ports (8080 and 8081), and the discovery file reflects
    the last successful bind.
    """
    bound: list[int] = []
    bound_lock = threading.Lock()

    async def _tracking_serve(handler, host, port, ssl=None, **kwargs):
        with bound_lock:
            # Simulate that if another instance already has a port, it's occupied
            if port in bound:
                raise OSError(98, "Address already in use")
            bound.append(port)
        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()
        return mock_server

    discovery_path = tmp_path / "service_discovery.json"

    with patch("websockets.serve", side_effect=_tracking_serve):
        mgr1 = _build_manager(port=8080)
        mgr1._DISCOVERY_PATH = discovery_path
        asyncio.run_coroutine_threadsafe(
            _run_start_server(mgr1), mgr1.loop
        ).result(timeout=3.0)

        mgr2 = _build_manager(port=8080)
        mgr2._DISCOVERY_PATH = discovery_path
        asyncio.run_coroutine_threadsafe(
            _run_start_server(mgr2), mgr2.loop
        ).result(timeout=3.0)

    assert mgr1.port == 8080, f"First manager should hold 8080, got {mgr1.port}"
    assert mgr2.port == 8081, f"Second manager should fall over to 8081, got {mgr2.port}"

    data = json.loads(discovery_path.read_text())
    assert data["active_port"] in (8080, 8081)

    for mgr in (mgr1, mgr2):
        mgr.loop.call_soon_threadsafe(mgr.loop.stop)
        mgr.loop_thread.join(timeout=2.0)


def test_discovery_file_removed_on_stop(tmp_path):
    """stop() cleans up the service-discovery file."""
    discovery_path = tmp_path / "service_discovery.json"

    with patch("websockets.serve", side_effect=_make_serve_factory(set())):
        mgr = _build_manager(port=8080)
        mgr._DISCOVERY_PATH = discovery_path
        asyncio.run_coroutine_threadsafe(
            _run_start_server(mgr), mgr.loop
        ).result(timeout=3.0)

    assert discovery_path.exists(), "Discovery file must exist after bind"

    # Call _remove_service_discovery directly (stop() has Qt thread dependencies)
    mgr._remove_service_discovery()

    assert not discovery_path.exists(), "Discovery file must be removed after stop"

    mgr.loop.call_soon_threadsafe(mgr.loop.stop)
    mgr.loop_thread.join(timeout=2.0)


def test_discovery_file_contains_expected_fields(tmp_path):
    """The discovery file must carry active_port, token, and bound_at."""
    discovery_path = tmp_path / "service_discovery.json"

    with patch("websockets.serve", side_effect=_make_serve_factory(set())):
        mgr = _build_manager(port=8083)
        mgr._DISCOVERY_PATH = discovery_path
        asyncio.run_coroutine_threadsafe(
            _run_start_server(mgr), mgr.loop
        ).result(timeout=3.0)

    data = json.loads(discovery_path.read_text())
    assert set(data.keys()) >= {"active_port", "token", "bound_at"}
    assert data["active_port"] == 8083
    assert data["token"] == "test-discovery-token"
    # bound_at must be a non-empty ISO-8601 string
    assert isinstance(data["bound_at"], str) and data["bound_at"]

    mgr.loop.call_soon_threadsafe(mgr.loop.stop)
    mgr.loop_thread.join(timeout=2.0)


def test_failover_exhausts_range_then_raises(tmp_path):
    """If all 10 ports in the range are occupied, the server logs a warning and sets started_event."""
    discovery_path = tmp_path / "service_discovery.json"
    all_ports = set(range(8080, 8090))

    with patch("websockets.serve", side_effect=_make_serve_factory(all_ports)):
        mgr = _build_manager(port=8080)
        mgr._DISCOVERY_PATH = discovery_path
        mgr.started_event.clear()
        asyncio.run_coroutine_threadsafe(
            _run_start_server(mgr), mgr.loop
        ).result(timeout=3.0)

    # started_event must still be set (so the caller is not blocked forever)
    assert mgr.started_event.is_set()
    # Server must not have bound
    assert mgr.server is None
    # Discovery file must not have been written
    assert not discovery_path.exists()

    mgr.loop.call_soon_threadsafe(mgr.loop.stop)
    mgr.loop_thread.join(timeout=2.0)


def test_real_socket_conflict_triggers_failover(tmp_path):
    """
    Occupy port 8080 with a real TCP socket; the server manager must bind on 8081.
    Uses a genuine OS-level OSError so the failover path is exercised end-to-end.
    """
    discovery_path = tmp_path / "service_discovery.json"

    # Grab port 8080 with a real socket so the OS rejects the bind attempt
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", 8080))
    blocker.listen(1)

    async def _serve_without_ssl(handler, host, port, ssl=None, **kwargs):
        """Bind a real TCP socket (no TLS) so we get a genuine OSError on 8080."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.close()
            raise
        sock.listen(1)

        mock_server = MagicMock()
        mock_server.close = MagicMock(side_effect=sock.close)
        mock_server.wait_closed = AsyncMock()
        mock_server._sock = sock
        return mock_server

    try:
        with patch("websockets.serve", side_effect=_serve_without_ssl):
            mgr = _build_manager(port=8080)
            mgr._DISCOVERY_PATH = discovery_path
            mgr.started_event.clear()
            asyncio.run_coroutine_threadsafe(
                _run_start_server(mgr), mgr.loop
            ).result(timeout=5.0)
    finally:
        blocker.close()
        if mgr.server and hasattr(mgr.server, "_sock"):
            mgr.server._sock.close()

    assert mgr.port == 8081, f"Expected failover to 8081, got {mgr.port}"
    data = json.loads(discovery_path.read_text())
    assert data["active_port"] == 8081

    mgr.loop.call_soon_threadsafe(mgr.loop.stop)
    mgr.loop_thread.join(timeout=2.0)
