from unittest.mock import MagicMock, patch

import pytest

from app.engine.model_loader import (
    CircuitBreakerOpenException,
    ModelCircuitBreaker,
    ModelLoader,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += seconds


@pytest.fixture
def isolated_model_loader():
    original_breaker = ModelLoader._circuit_breaker
    original_instance = ModelLoader._instance
    original_model_path = ModelLoader._model_path
    original_model_name = ModelLoader._model_name
    original_active_adapter = ModelLoader._active_adapter
    original_n_ctx = ModelLoader._n_ctx
    original_instance_locked = ModelLoader._instance_locked
    original_active_generation_count = ModelLoader._active_generation_count
    original_draft_instance = ModelLoader._draft_instance
    original_draft_model_path = ModelLoader._draft_model_path

    clock = FakeClock()
    ModelLoader._circuit_breaker = ModelCircuitBreaker(
        failure_threshold=3,
        cooldown_duration=30.0,
        clock=clock,
    )
    ModelLoader._instance = None
    ModelLoader._model_path = None
    ModelLoader._model_name = None
    ModelLoader._active_adapter = None
    ModelLoader._n_ctx = 2048
    ModelLoader._instance_locked = False
    ModelLoader._active_generation_count = 0
    ModelLoader._draft_instance = None
    ModelLoader._draft_model_path = None

    yield clock

    ModelLoader._circuit_breaker = original_breaker
    ModelLoader._instance = original_instance
    ModelLoader._model_path = original_model_path
    ModelLoader._model_name = original_model_name
    ModelLoader._active_adapter = original_active_adapter
    ModelLoader._n_ctx = original_n_ctx
    ModelLoader._instance_locked = original_instance_locked
    ModelLoader._active_generation_count = original_active_generation_count
    ModelLoader._draft_instance = original_draft_instance
    ModelLoader._draft_model_path = original_draft_model_path


def _loader_patches():
    return patch.multiple(
        ModelLoader,
        _resolve_model_path=MagicMock(return_value="data/models/mock.gguf"),
        _read_registry_n_ctx=MagicMock(return_value=2048),
        _registry_entry=MagicMock(return_value={}),
        preflight_model_load=MagicMock(return_value=None),
        _bench_vram_bandwidth=MagicMock(return_value=None),
        _attach_kv_cache=MagicMock(return_value=None),
        _inspect_adapter_vocab=MagicMock(return_value=None),
        _start_idle_watcher=MagicMock(return_value=None),
    )


def test_model_circuit_breaker_trips_after_three_terminal_load_failures(isolated_model_loader):
    with _loader_patches(), patch(
        "app.engine.model_loader.get_hardware_profile",
        return_value={"gpu_list": []},
    ), patch(
        "app.engine.model_loader.config_store.get_active_model",
        return_value={"filename": "mock.gguf", "adapter": None},
    ), patch(
        "subprocess.run",
        return_value=MagicMock(returncode=0),
    ), patch(
        "app.engine.model_loader.Llama",
        side_effect=RuntimeError("CUDA out of memory"),
    ) as llama_ctor:
        for _ in range(3):
            with pytest.raises(RuntimeError):
                ModelLoader.get_instance()

        assert ModelLoader._circuit_breaker.state == ModelCircuitBreaker.OPEN
        assert llama_ctor.call_count == 3

        with pytest.raises(CircuitBreakerOpenException):
            ModelLoader.get_instance()

        assert llama_ctor.call_count == 3


def test_model_circuit_breaker_half_open_success_resets_to_closed(isolated_model_loader):
    clock = isolated_model_loader
    loaded_model = MagicMock()

    with _loader_patches(), patch(
        "app.engine.model_loader.get_hardware_profile",
        return_value={"gpu_list": []},
    ), patch(
        "app.engine.model_loader.config_store.get_active_model",
        return_value={"filename": "mock.gguf", "adapter": None},
    ), patch(
        "subprocess.run",
        return_value=MagicMock(returncode=0),
    ), patch(
        "app.engine.model_loader.Llama",
        side_effect=[
            RuntimeError("CUDA out of memory"),
            RuntimeError("CUDA out of memory"),
            RuntimeError("CUDA out of memory"),
            loaded_model,
        ],
    ) as llama_ctor:
        for _ in range(3):
            with pytest.raises(RuntimeError):
                ModelLoader.get_instance()

        clock.advance(31.0)

        assert ModelLoader.get_instance() is loaded_model
        assert ModelLoader._circuit_breaker.state == ModelCircuitBreaker.CLOSED
        assert ModelLoader._circuit_breaker.consecutive_failures == 0
        assert ModelLoader._circuit_breaker.cooldown_expiration is None
        assert llama_ctor.call_count == 4
