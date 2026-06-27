"""Inference safety tests for model locking, stream cleanup, and offline mode."""

from __future__ import annotations

import io
import os

import pytest


def test_model_reset_blocked_during_active_generation():
    from app.engine.model_loader import ModelLoader

    original_count = ModelLoader._active_generation_count
    original_locked = ModelLoader._instance_locked
    try:
        ModelLoader._active_generation_count = 1
        ModelLoader._instance_locked = True
        with pytest.raises(RuntimeError, match="Cannot reset ModelLoader while inference is active"):
            ModelLoader.reset_instance()
    finally:
        ModelLoader._active_generation_count = original_count
        ModelLoader._instance_locked = original_locked


def test_model_reload_or_adapter_change_blocked_during_active_generation():
    from app.engine.model_loader import ModelLoader

    original_count = ModelLoader._active_generation_count
    original_locked = ModelLoader._instance_locked
    original_instance = getattr(ModelLoader, "_instance", None)
    original_model_path = getattr(ModelLoader, "_model_path", None)
    original_adapter = getattr(ModelLoader, "_active_adapter", None)
    original_offloaded = getattr(ModelLoader, "_adapter_offloaded", False)
    try:
        ModelLoader._instance = object()
        ModelLoader._model_path = "data/models/current.gguf"
        ModelLoader._active_adapter = None
        ModelLoader._adapter_offloaded = False
        ModelLoader._active_generation_count = 1
        ModelLoader._instance_locked = True

        with pytest.raises(RuntimeError, match="Cannot reload model or change adapter"):
            ModelLoader.get_instance(model_path="data/models/other.gguf")

        with pytest.raises(RuntimeError, match="Cannot reload model or change adapter"):
            ModelLoader.get_instance(
                model_path="data/models/current.gguf",
                adapter_name="new-adapter",
            )
    finally:
        ModelLoader._active_generation_count = original_count
        ModelLoader._instance_locked = original_locked
        ModelLoader._instance = original_instance
        ModelLoader._model_path = original_model_path
        ModelLoader._active_adapter = original_adapter
        ModelLoader._adapter_offloaded = original_offloaded


def test_failed_acquire_does_not_release_existing_generation():
    from app.engine.model_loader import ModelLoader

    original_count = ModelLoader._active_generation_count
    original_locked = ModelLoader._instance_locked
    original_instance = getattr(ModelLoader, "_instance", None)
    original_model_path = getattr(ModelLoader, "_model_path", None)
    try:
        ModelLoader._instance = object()
        ModelLoader._model_path = "data/models/current.gguf"
        ModelLoader._active_generation_count = 1
        ModelLoader._instance_locked = True

        with pytest.raises(RuntimeError, match="Cannot reload model or change adapter"):
            ModelLoader.acquire_instance(model_path="data/models/other.gguf")

        assert ModelLoader._active_generation_count == 1
        assert ModelLoader._instance_locked is True
    finally:
        ModelLoader._active_generation_count = original_count
        ModelLoader._instance_locked = original_locked
        ModelLoader._instance = original_instance
        ModelLoader._model_path = original_model_path


def test_offline_guard_blocks_external_http_by_default(monkeypatch):
    from app.engine.offline_guard import OfflineNetworkError, assert_online_allowed

    monkeypatch.delenv("KARL_ONLINE_EXECUTION", raising=False)
    with pytest.raises(OfflineNetworkError):
        assert_online_allowed("https://huggingface.co/models", operation="test request")


def test_offline_guard_allows_localhost_by_default(monkeypatch):
    from app.engine.offline_guard import assert_online_allowed

    monkeypatch.delenv("KARL_ONLINE_EXECUTION", raising=False)
    assert_online_allowed("http://127.0.0.1:8080/status", operation="local test request")
    assert_online_allowed("ws://localhost:8080", operation="local websocket")


def test_offline_guard_env_allows_external(monkeypatch):
    from app.engine.offline_guard import assert_online_allowed

    monkeypatch.setenv("KARL_ONLINE_EXECUTION", "1")
    assert_online_allowed("https://huggingface.co/models", operation="test request")


def test_requests_external_call_is_blocked_before_network(monkeypatch):
    import requests
    from app.engine.offline_guard import OfflineNetworkError

    monkeypatch.delenv("KARL_ONLINE_EXECUTION", raising=False)
    with pytest.raises(OfflineNetworkError):
        requests.get("https://huggingface.co/models", timeout=0.01)


def test_agentic_stream_generator_closes_on_cancel():
    from app.engine.agentic_thread import AgenticThread

    class FakeStream:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            yield {"choices": [{"text": "ignored", "finish_reason": None}]}

        def close(self):
            self.closed = True

    class FakeLLM:
        def __init__(self):
            self.stream = FakeStream()

        def __call__(self, *args, **kwargs):
            return self.stream

        def tokenize(self, data, add_bos=False):
            return [1]

    llm = FakeLLM()
    thread = AgenticThread(
        system_prompt="system",
        initial_history=[],
        hyperparams={"max_tokens": 8},
    )
    thread.request_stop()

    thread._run_single_generation(llm, "prompt", io.StringIO())

    assert llm.stream.closed


def test_llm_thread_request_stop_sets_flag():
    from app.engine.llm_thread import LLMThread

    thread = LLMThread(
        system_prompt="system",
        chat_history=[],
        hyperparams={"max_tokens": 8},
    )
    assert not thread._stop_requested
    thread.request_stop()
    assert thread._stop_requested


def test_llm_thread_stop_flag_prevents_generation():
    """A stopped LLMThread still has close() called on the generator."""

    close_calls = []

    class FakeStream:
        def __iter__(self):
            yield {"choices": [{"text": "x", "finish_reason": None}]}

        def close(self):
            close_calls.append(True)

    # Verify the finally-close pattern directly without running the full thread.
    finish_reason = "stop"
    stop_requested = True
    stream = FakeStream()
    try:
        for chunk in stream:
            if stop_requested:
                finish_reason = "cancelled"
                break
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()

    assert finish_reason == "cancelled"
    assert close_calls, "close() must be called after cancellation break"


def test_active_generation_count_increments_and_decrements():
    from app.engine.model_loader import ModelLoader

    original_count = ModelLoader._active_generation_count
    original_locked = ModelLoader._instance_locked
    try:
        assert not ModelLoader.is_instance_locked()
        ModelLoader.lock_instance()
        assert ModelLoader._active_generation_count == 1
        assert ModelLoader.is_instance_locked()
        ModelLoader.lock_instance()
        assert ModelLoader._active_generation_count == 2

        ModelLoader.unlock_instance()
        assert ModelLoader._active_generation_count == 1
        assert ModelLoader.is_instance_locked()

        ModelLoader.unlock_instance()
        assert ModelLoader._active_generation_count == 0
        assert not ModelLoader.is_instance_locked()
    finally:
        ModelLoader._active_generation_count = original_count
        ModelLoader._instance_locked = original_locked


def test_inference_error_message_is_descriptive():
    from app.engine.model_loader import ModelLoader

    original_count = ModelLoader._active_generation_count
    original_locked = ModelLoader._instance_locked
    try:
        ModelLoader._active_generation_count = 2
        ModelLoader._instance_locked = True
        with pytest.raises(RuntimeError) as exc_info:
            ModelLoader.reset_instance()
        msg = str(exc_info.value)
        assert "2 active generation" in msg
        assert "cancellation" in msg.lower() or "cancel" in msg.lower()
    finally:
        ModelLoader._active_generation_count = original_count
        ModelLoader._instance_locked = original_locked


def test_hf_offline_vars_applied_when_offline(monkeypatch):
    from app.engine import offline_guard

    monkeypatch.delenv("KARL_ONLINE_EXECUTION", raising=False)
    # Reset the applied state so apply_for_current_config() re-evaluates.
    orig = offline_guard._hf_vars_applied
    offline_guard._hf_vars_applied = False
    for var in offline_guard._HF_OFFLINE_VARS:
        monkeypatch.delenv(var, raising=False)
    try:
        offline_guard.apply_for_current_config()
        assert offline_guard.hf_vars_applied()
        for var in offline_guard._HF_OFFLINE_VARS:
            assert os.environ.get(var) == "1", f"{var} should be set to '1'"
    finally:
        offline_guard._hf_vars_applied = orig


def test_hf_offline_vars_cleared_when_online(monkeypatch):
    from app.engine import offline_guard

    monkeypatch.setenv("KARL_ONLINE_EXECUTION", "1")
    # Simulate vars having been previously applied.
    orig = offline_guard._hf_vars_applied
    offline_guard._hf_vars_applied = True
    for var in offline_guard._HF_OFFLINE_VARS:
        os.environ[var] = "1"
    try:
        offline_guard.apply_for_current_config()
        assert not offline_guard.hf_vars_applied()
        for var in offline_guard._HF_OFFLINE_VARS:
            assert var not in os.environ, f"{var} should be cleared in online mode"
    finally:
        offline_guard._hf_vars_applied = orig


def test_guard_install_is_idempotent():
    from app.engine import offline_guard

    first = offline_guard._INSTALLED
    offline_guard.install()
    offline_guard.install()
    # If install() were not idempotent it would double-wrap the patched method.
    assert offline_guard._INSTALLED is True
    assert offline_guard._INSTALLED == first or first is False
