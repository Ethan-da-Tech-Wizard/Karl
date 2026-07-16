import asyncio
import json
import threading

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
    manager.port = 19999
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


async def run_handler_once(manager, message):
    websocket = MockWebSocket([message])
    await manager._handler(websocket, path="/?token=test-token")
    assert websocket.sent
    return json.loads(websocket.sent[-1])


def assert_rpc_error(response, code, req_id):
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == req_id
    assert response["error"]["code"] == code
    assert isinstance(response["error"]["message"], str)


def test_parse_error_returns_json_rpc_error():
    response = asyncio.run(run_handler_once(make_manager(), "{bad json"))
    assert_rpc_error(response, -32700, None)


def test_missing_jsonrpc_returns_invalid_request():
    response = asyncio.run(run_handler_once(
        make_manager(),
        json.dumps({"id": 10, "method": "get_runtime_status"}),
    ))
    assert_rpc_error(response, -32600, 10)


def test_unknown_method_returns_method_not_found():
    response = asyncio.run(run_handler_once(
        make_manager(),
        json.dumps({"jsonrpc": "2.0", "id": 11, "method": "no_such_method"}),
    ))
    assert_rpc_error(response, -32601, 11)


def test_missing_required_params_returns_invalid_params():
    response = asyncio.run(run_handler_once(
        make_manager(),
        json.dumps({"jsonrpc": "2.0", "id": 12, "method": "set_active_model", "params": {}}),
    ))
    assert_rpc_error(response, -32602, 12)


def test_handler_exception_returns_internal_error():
    manager = make_manager()

    def raise_runtime_error():
        raise ValueError("boom")

    manager._list_models = raise_runtime_error
    response = asyncio.run(run_handler_once(
        manager,
        json.dumps({"jsonrpc": "2.0", "id": 13, "method": "list_models"}),
    ))
    assert_rpc_error(response, -32603, 13)
    assert response["error"]["data"] == "boom"


def test_global_rate_limiter_exceeded():
    manager = make_manager()
    manager._list_models = lambda: {"models": []}

    # Global rate limit is capacity=20.0
    requests = [
        json.dumps({"jsonrpc": "2.0", "id": i, "method": "list_models"})
        for i in range(22)
    ]
    websocket = MockWebSocket(requests)
    
    asyncio.run(manager._handler(websocket, path="/?token=test-token"))
    
    assert len(websocket.sent) == 22
    for i in range(20):
        resp = json.loads(websocket.sent[i])
        if "error" in resp:
            assert resp["error"]["code"] != -32005
    
    for i in range(20, 22):
        resp = json.loads(websocket.sent[i])
        assert_rpc_error(resp, -32005, i)
        assert "global rate limit exceeded" in resp["error"]["message"]


def test_heavy_rate_limiter_exceeded():
    manager = make_manager()
    # Mock set_active_model which is a heavy method
    manager._set_active_model = lambda filename, adapter=None: {"active": {}}

    # Heavy limit capacity=3.0
    requests = [
        json.dumps({
            "jsonrpc": "2.0",
            "id": i,
            "method": "set_active_model",
            "params": {"filename": "model.gguf"}
        })
        for i in range(5)
    ]
    websocket = MockWebSocket(requests)
    
    asyncio.run(manager._handler(websocket, path="/?token=test-token"))
    
    assert len(websocket.sent) == 5
    for i in range(3):
        resp = json.loads(websocket.sent[i])
        if "error" in resp:
            assert resp["error"]["code"] != -32005
    
    for i in range(3, 5):
        resp = json.loads(websocket.sent[i])
        assert_rpc_error(resp, -32005, i)
        assert "rate limit exceeded for heavy method" in resp["error"]["message"]
