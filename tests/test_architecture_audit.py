import asyncio
import inspect
import threading
from pathlib import Path

import pytest


def test_model_loader_blocks_reset_during_active_inference(monkeypatch):
    pytest.importorskip("llama_cpp")
    from app.engine.model_loader import ModelLoader

    sentinel = object()

    def fake_get_instance(cls, *args, **kwargs):
        cls._instance = sentinel
        return sentinel

    monkeypatch.setattr(ModelLoader, "get_instance", classmethod(fake_get_instance))
    ModelLoader._instance = None
    ModelLoader._instance_locked = False
    ModelLoader._active_generation_count = 0

    llm = ModelLoader.acquire_instance()
    assert llm is sentinel
    assert ModelLoader.is_instance_locked()

    with pytest.raises(RuntimeError, match="inference is active"):
        ModelLoader.reset_instance()

    ModelLoader.unlock_instance()
    assert not ModelLoader.is_instance_locked()
    assert ModelLoader._active_generation_count == 0


def test_generation_threads_use_guarded_model_acquisition():
    llm_source = Path("app/engine/llm_thread.py").read_text(encoding="utf-8")
    agentic_source = Path("app/engine/agentic_thread.py").read_text(encoding="utf-8")

    assert "ModelLoader.acquire_instance" in llm_source
    assert "ModelLoader.acquire_instance" in agentic_source
    assert "response_generator" in llm_source and 'getattr(response_generator, "close", None)' in llm_source
    assert "response_gen" in agentic_source and 'getattr(response_gen, "close", None)' in agentic_source


def test_app_state_queues_cross_thread_signal_emissions():
    source = Path("app/state.py").read_text(encoding="utf-8")

    assert "QMetaObject.invokeMethod" in source
    assert "Qt.ConnectionType.QueuedConnection" in source
    assert "@pyqtSlot(str, object)" in source


def test_websocket_broadcast_prunes_failed_clients():
    from app.engine.websocket_server import WebSocketServerManager

    class FailingClient:
        async def send(self, payload):
            raise RuntimeError("closed")

    class GoodClient:
        def __init__(self):
            self.payloads = []

        async def send(self, payload):
            self.payloads.append(payload)

    manager = WebSocketServerManager.__new__(WebSocketServerManager)
    manager.clients = set()
    manager.client_metadata = {}
    manager.client_histories = {}
    manager._clients_lock = threading.Lock()

    failing = FailingClient()
    good = GoodClient()
    manager.clients.update({failing, good})
    manager.client_metadata[failing] = {"id": "bad"}
    manager.client_metadata[good] = {"id": "good"}
    manager.client_histories[failing] = []
    manager.client_histories[good] = []

    asyncio.run(manager._broadcast_notification("status_update", {"message": "ok"}))

    assert good in manager.clients
    assert good.payloads
    assert failing not in manager.clients
    assert failing not in manager.client_metadata
    assert failing not in manager.client_histories


def test_websocket_manager_exposes_thread_safe_client_count():
    from app.engine.websocket_server import WebSocketServerManager

    assert "client_count" in dir(WebSocketServerManager)
    source = inspect.getsource(WebSocketServerManager.client_count)
    assert "_clients_lock" in source
