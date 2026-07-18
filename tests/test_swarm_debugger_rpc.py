"""
Dispatch-level tests for the swarm interactive-debugger RPC endpoints:
swarm_pause / swarm_resume / swarm_step / swarm_override_task / swarm_get_history.

Uses the same MockWebSocket/manager pattern as test_websocket_contract.py to
exercise WebSocketServerManager._handler() directly instead of opening a real
socket — real end-to-end socket connections are unreliable in this sandbox
(the same failure reproduces on the pre-existing, unmodified
test_auto_train.py::test_websocket_start_auto_train_rpc).
"""

import asyncio
import json
import threading
import unittest

import tests.qt_test_helper  # noqa: F401

from app.engine.websocket_server import WebSocketServerManager


class MockWebSocket:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []
        self.remote_address = ("127.0.0.1", 50000)
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def send(self, payload):
        self.sent.append(payload)

    async def close(self, code=None, reason=None):
        self.closed = True
        self.close_code = code
        self.close_reason = reason


def make_manager():
    manager = WebSocketServerManager.__new__(WebSocketServerManager)
    manager.port = 19998
    manager.clients = set()
    manager.client_metadata = {}
    manager.client_histories = {}
    manager.loop = None
    manager.server = None
    manager.orchestrator = None
    manager.chat_thread = None
    manager.mini_train_thread = None
    manager.kb_ingest_thread = None
    manager._threads_lock = threading.Lock()
    manager._clients_lock = threading.Lock()
    manager._validate_token = lambda token: True
    return manager


async def _rpc(manager, message: dict) -> dict:
    websocket = MockWebSocket([json.dumps(message)])
    await manager._handler(websocket, path="/?token=test-token")
    assert websocket.sent, "handler produced no response"
    return json.loads(websocket.sent[-1])


class TestSwarmDebuggerRpc(unittest.TestCase):
    def test_swarm_pause_without_active_run_returns_error(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 1, "method": "swarm_pause", "params": {"run_id": "no-such-run"},
        }))
        self.assertIn("error", resp)
        self.assertIn("No swarm task", resp["error"]["message"])

    def test_swarm_resume_without_active_run_returns_error(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 2, "method": "swarm_resume", "params": {"run_id": "no-such-run"},
        }))
        self.assertIn("error", resp)

    def test_swarm_step_without_active_run_returns_error(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 3, "method": "swarm_step", "params": {"run_id": "no-such-run"},
        }))
        self.assertIn("error", resp)

    def test_swarm_override_task_without_active_run_returns_error(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 4, "method": "swarm_override_task",
            "params": {"run_id": "no-such-run", "filepath": "a.py", "instructions": "do X"},
        }))
        self.assertIn("error", resp)

    def test_swarm_pause_rejects_missing_run_id(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 5, "method": "swarm_pause", "params": {},
        }))
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)

    def test_swarm_override_task_rejects_missing_instructions(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 6, "method": "swarm_override_task",
            "params": {"run_id": "x", "filepath": "a.py"},
        }))
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)

    def test_swarm_get_history_without_run_id_lists_runs(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 7, "method": "swarm_get_history", "params": {},
        }))
        self.assertIn("result", resp)
        self.assertIn("runs", resp["result"])
        self.assertIsInstance(resp["result"]["runs"], list)

    def test_swarm_get_history_with_unknown_run_id_returns_empty_steps(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 8, "method": "swarm_get_history",
            "params": {"run_id": "definitely-not-a-real-run"},
        }))
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["steps"], [])

    def test_swarm_get_history_rejects_non_string_run_id(self):
        resp = asyncio.run(_rpc(make_manager(), {
            "jsonrpc": "2.0", "id": 9, "method": "swarm_get_history", "params": {"run_id": 123},
        }))
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
