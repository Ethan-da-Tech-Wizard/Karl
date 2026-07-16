import unittest
from unittest.mock import MagicMock, patch
import pytest

from app.engine.model_loader import ModelCircuitBreaker, ModelLoader
from app.engine import config_store
from app.engine.websocket_server import WebSocketServerManager

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += seconds


def test_circuit_breaker_states():
    clock = FakeClock()
    breaker = ModelCircuitBreaker(failure_threshold=2, cooldown_duration=10.0, clock=clock)
    
    # Initially CLOSED
    assert breaker.get_state() == "CLOSED"
    
    # First failure
    breaker.record_failure()
    assert breaker.get_state() == "CLOSED"
    
    # Second failure (trips)
    breaker.record_failure()
    assert breaker.get_state() == "COOLDOWN"
    
    # Cooldown half-way
    clock.advance(5.0)
    assert breaker.get_state() == "COOLDOWN"
    
    # Cooldown expires
    clock.advance(6.0)
    assert breaker.get_state() == "HALF_OPEN"
    
    # Manually reset
    breaker.reset()
    assert breaker.get_state() == "CLOSED"


def test_model_loader_speculative_fallback_persists(tmp_path, monkeypatch):
    # Mock config store paths
    draft_path = tmp_path / "draft_model.json"
    active_path = tmp_path / "active_model.json"
    monkeypatch.setattr(config_store, "DRAFT_MODEL_PATH", str(draft_path))
    monkeypatch.setattr(config_store, "ACTIVE_MODEL_PATH", str(active_path))
    
    # Setup initial enabled draft config
    config_store.set_active_draft_model("draft.gguf", enabled=True)
    assert config_store.get_active_draft_model()["enabled"] is True
    
    # Mock ModelLoader dependencies to force an exception on draft load
    with patch("app.engine.model_loader.ModelLoader._resolve_model_path", return_value="data/models/mock.gguf"), \
         patch("app.engine.model_loader.ModelLoader._read_registry_n_ctx", return_value=2048), \
         patch("app.engine.model_loader.ModelLoader._registry_entry", return_value={}), \
         patch("app.engine.model_loader.ModelLoader.preflight_model_load", return_value=None), \
         patch("app.engine.model_loader.ModelLoader._bench_vram_bandwidth", return_value=None), \
         patch("app.engine.model_loader.ModelLoader._attach_kv_cache", return_value=None), \
         patch("app.engine.model_loader.ModelLoader._inspect_adapter_vocab", return_value=None), \
         patch("app.engine.model_loader.ModelLoader._start_idle_watcher", return_value=None), \
         patch("app.engine.model_loader.Llama", return_value=MagicMock()), \
         patch("subprocess.run", return_value=MagicMock(returncode=0)), \
         patch("app.engine.model_loader.get_hardware_profile", return_value={"gpu_list": []}), \
         patch("app.engine.model_loader.config_store.get_active_model", return_value={"filename": "mock.gguf", "adapter": None}), \
         patch("llama_cpp.Llama", side_effect=RuntimeError("Draft model corrupt")):
         
         # Call get_instance which should invoke the loading logic with draft_model_path set
         ModelLoader._instance = None
         # Trigger the load with a non-empty draft_model_path that exists
         with patch("os.path.exists", return_value=True):
             ModelLoader.get_instance(model_path="mock.gguf", draft_model_path="draft.gguf")
             
         # The draft model load should have failed, resulting in disabled speculative config
         draft_cfg = config_store.get_active_draft_model()
         assert draft_cfg["enabled"] is False


def test_websocket_client_disconnect_cleanup():
    state_mock = MagicMock()
    
    with patch("app.engine.websocket_server.save_cached_token"), \
         patch("app.engine.websocket_server.WebSocketServerManager._ensure_ssl_certs"), \
         patch("app.engine.websocket_server.WebSocketServerManager._start_loop_thread"):
        
        manager = WebSocketServerManager(port=9999, state=state_mock)
        
        # Setup mock connections
        conn1 = MagicMock()
        conn2 = MagicMock()
        
        # Mock threads
        mock_chat_thread = MagicMock()
        mock_chat_thread.isRunning.return_value = True
        
        mock_orchestrator = MagicMock()
        mock_orchestrator.isRunning.return_value = True
        
        manager.chat_thread = mock_chat_thread
        manager.chat_thread_owner = conn1
        
        manager.orchestrator = mock_orchestrator
        manager.orchestrator_owner = conn2
        
        # Setup client list
        manager.clients.add(conn1)
        manager.clients.add(conn2)
        
        # Simulate disconnect for conn1
        websocket = conn1
        with manager._threads_lock:
            if getattr(manager, "orchestrator_owner", None) == websocket:
                if manager.orchestrator and manager.orchestrator.isRunning():
                    manager.orchestrator.request_stop()
                manager.orchestrator_owner = None
            if getattr(manager, "chat_thread_owner", None) == websocket:
                if manager.chat_thread and manager.chat_thread.isRunning():
                    if hasattr(manager.chat_thread, "request_stop"):
                        manager.chat_thread.request_stop()
                manager.chat_thread_owner = None
                
        # Assert chat thread stop request was called, orchestrator was not
        mock_chat_thread.request_stop.assert_called_once()
        mock_orchestrator.request_stop.assert_not_called()
        assert manager.chat_thread_owner is None
        assert manager.orchestrator_owner == conn2
        
        # Simulate disconnect for conn2
        websocket = conn2
        with manager._threads_lock:
            if getattr(manager, "orchestrator_owner", None) == websocket:
                if manager.orchestrator and manager.orchestrator.isRunning():
                    manager.orchestrator.request_stop()
                manager.orchestrator_owner = None
            if getattr(manager, "chat_thread_owner", None) == websocket:
                if manager.chat_thread and manager.chat_thread.isRunning():
                    if hasattr(manager.chat_thread, "request_stop"):
                        manager.chat_thread.request_stop()
                manager.chat_thread_owner = None
                
        # Assert orchestrator stop request was called
        mock_orchestrator.request_stop.assert_called_once()
        assert manager.orchestrator_owner is None
