from __future__ import annotations

import types

import pytest
from unittest.mock import MagicMock, patch


def test_remote_rpc_timeout_disables_remote_and_streams_local_fallback(monkeypatch):
    from app.engine.remote_rpc_client import RemoteRPCModel

    captured = {
        "fallback_reason": None,
        "local_prompt": None,
        "local_kwargs": None,
    }

    class FailingWebSocketContext:
        async def __aenter__(self):
            raise TimeoutError("handshake timeout")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def fake_connect(url, ssl=None, close_timeout=None):
        captured["connect_url"] = url
        captured["ssl_context"] = ssl
        captured["close_timeout"] = close_timeout
        return FailingWebSocketContext()

    monkeypatch.setitem(__import__("sys").modules, "websockets", types.ModuleType("websockets"))
    monkeypatch.setitem(__import__("sys").modules, "websockets.asyncio", types.ModuleType("websockets.asyncio"))
    client_module = types.ModuleType("websockets.asyncio.client")
    client_module.connect = fake_connect
    monkeypatch.setitem(__import__("sys").modules, "websockets.asyncio.client", client_module)

    class LocalFallbackModel:
        def __call__(self, prompt, **kwargs):
            captured["local_prompt"] = prompt
            captured["local_kwargs"] = kwargs
            yield {"choices": [{"text": "local answer", "finish_reason": "stop"}]}

    def on_fallback(reason):
        captured["fallback_reason"] = reason

    model = RemoteRPCModel(
        server_url="wss://192.168.1.50:8080",
        auth_token="secret-token",
        on_fallback=on_fallback,
        local_fallback_factory=lambda: LocalFallbackModel(),
        handshake_timeout=0.01,
    )

    chunks = list(model(
        "hello remote",
        stream=True,
        max_tokens=123,
        temperature=0.25,
        top_p=0.8,
        stop=["<stop>"],
        echo=False,
    ))

    assert chunks == [{"choices": [{"text": "local answer", "finish_reason": "stop"}]}]
    assert captured["connect_url"] == "wss://192.168.1.50:8080?token=secret-token"
    assert captured["close_timeout"] == 2
    assert captured["ssl_context"].check_hostname is False
    assert "handshake timeout" in captured["fallback_reason"]
    assert captured["local_prompt"] == "hello remote"
    assert captured["local_kwargs"]["max_tokens"] == 123
    assert captured["local_kwargs"]["temperature"] == 0.25
    assert captured["local_kwargs"]["top_p"] == 0.8
    assert captured["local_kwargs"]["stream"] is True
    assert captured["local_kwargs"]["stop"] == ["<stop>"]


def test_model_loader_remote_fallback_persists_disabled(monkeypatch):
    from app.engine.model_loader import ModelLoader

    calls = []

    monkeypatch.setattr(
        "app.engine.config_store.get_engine_config",
        lambda: {
            "remote_engine_enabled": True,
            "remote_engine_url": "wss://localhost:8080",
            "remote_engine_token": "token",
            "engine_mode": "remote",
            "remote_server_url": "wss://localhost:8080",
            "remote_auth_token": "token",
        },
    )
    monkeypatch.setattr(
        "app.engine.config_store.set_remote_engine_config",
        lambda enabled, url=None, token=None: calls.append((enabled, url, token)) or True,
    )

    original_remote = ModelLoader._remote_instance
    original_reason = ModelLoader._remote_fallback_reason
    try:
        ModelLoader._remote_instance = object()
        ModelLoader._remote_fallback("connection dropped")

        assert calls == [(False, "wss://localhost:8080", "token")]
        assert ModelLoader._remote_instance is None
        assert ModelLoader.last_remote_fallback_reason() == "connection dropped"
    finally:
        ModelLoader._remote_instance = original_remote
        ModelLoader._remote_fallback_reason = original_reason


# ── ModelLoader.get_instance() remote-mode wiring ────────────────────────────
#
# These tests exercise the branch that get_instance() takes when remote engine
# mode is enabled: it must construct/reuse a RemoteRPCModel and return it
# *without* touching the local llama-cpp load path, and must fall through to
# the exact unmodified local path when remote mode is disabled (the default).

@pytest.fixture
def isolated_model_loader_remote_state():
    from app.engine.model_loader import ModelLoader

    saved = {
        "_instance": ModelLoader._instance,
        "_model_path": ModelLoader._model_path,
        "_model_name": ModelLoader._model_name,
        "_active_adapter": ModelLoader._active_adapter,
        "_n_ctx": ModelLoader._n_ctx,
        "_instance_locked": ModelLoader._instance_locked,
        "_active_generation_count": ModelLoader._active_generation_count,
        "_draft_instance": ModelLoader._draft_instance,
        "_draft_model_path": ModelLoader._draft_model_path,
        "_remote_instance": ModelLoader._remote_instance,
        "_remote_fallback_reason": ModelLoader._remote_fallback_reason,
    }
    ModelLoader._instance = None
    ModelLoader._model_path = None
    ModelLoader._model_name = None
    ModelLoader._active_adapter = None
    ModelLoader._n_ctx = 2048
    ModelLoader._instance_locked = False
    ModelLoader._active_generation_count = 0
    ModelLoader._draft_instance = None
    ModelLoader._draft_model_path = None
    ModelLoader._remote_instance = None
    ModelLoader._remote_fallback_reason = None

    yield

    for key, value in saved.items():
        setattr(ModelLoader, key, value)


def _local_load_patches():
    from app.engine.model_loader import ModelLoader
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


def test_get_instance_routes_to_remote_when_enabled(isolated_model_loader_remote_state):
    from app.engine.model_loader import ModelLoader

    fake_remote = MagicMock(name="RemoteRPCModel-instance")
    fake_remote.server_url = "wss://example.lan:9090"
    fake_remote.auth_token = "tok-1"

    with patch(
        "app.engine.model_loader.config_store.get_engine_config",
        return_value={
            "remote_engine_enabled": True,
            "remote_engine_url": "wss://example.lan:9090",
            "remote_engine_token": "tok-1",
            "engine_mode": "remote",
            "remote_server_url": "wss://example.lan:9090",
            "remote_auth_token": "tok-1",
        },
    ), patch(
        "app.engine.model_loader.RemoteRPCModel", return_value=fake_remote
    ) as remote_ctor, patch(
        "app.engine.model_loader.Llama"
    ) as llama_ctor:
        result = ModelLoader.get_instance()

    assert result is fake_remote
    assert ModelLoader._remote_instance is fake_remote
    # The local llama-cpp load path must never run in remote mode.
    llama_ctor.assert_not_called()
    remote_ctor.assert_called_once()
    _, ctor_args, ctor_kwargs = remote_ctor.mock_calls[0]
    assert ctor_args[0] == "wss://example.lan:9090"
    assert ctor_args[1] == "tok-1"
    assert callable(ctor_kwargs["on_fallback"])
    assert callable(ctor_kwargs["local_fallback_factory"])


def test_get_instance_reuses_cached_remote_instance_for_same_url_and_token(
    isolated_model_loader_remote_state,
):
    from app.engine.model_loader import ModelLoader

    fake_remote = MagicMock(name="RemoteRPCModel-instance")
    fake_remote.server_url = "wss://example.lan:9090"
    fake_remote.auth_token = "tok-1"

    with patch(
        "app.engine.model_loader.config_store.get_engine_config",
        return_value={
            "remote_engine_enabled": True,
            "remote_engine_url": "wss://example.lan:9090",
            "remote_engine_token": "tok-1",
        },
    ), patch(
        "app.engine.model_loader.RemoteRPCModel", return_value=fake_remote
    ) as remote_ctor:
        first = ModelLoader.get_instance()
        second = ModelLoader.get_instance()

    assert first is fake_remote
    assert second is fake_remote
    remote_ctor.assert_called_once()


def test_get_instance_reconstructs_remote_instance_when_url_changes(
    isolated_model_loader_remote_state,
):
    from app.engine.model_loader import ModelLoader

    first_remote = MagicMock(name="remote-1")
    first_remote.server_url = "wss://a.lan:9090"
    first_remote.auth_token = "tok"
    second_remote = MagicMock(name="remote-2")
    second_remote.server_url = "wss://b.lan:9090"
    second_remote.auth_token = "tok"

    with patch(
        "app.engine.model_loader.config_store.get_engine_config",
        side_effect=[
            {
                "remote_engine_enabled": True,
                "remote_engine_url": "wss://a.lan:9090",
                "remote_engine_token": "tok",
            },
            {
                "remote_engine_enabled": True,
                "remote_engine_url": "wss://b.lan:9090",
                "remote_engine_token": "tok",
            },
        ],
    ), patch(
        "app.engine.model_loader.RemoteRPCModel",
        side_effect=[first_remote, second_remote],
    ) as remote_ctor:
        first = ModelLoader.get_instance()
        second = ModelLoader.get_instance()

    assert first is first_remote
    assert second is second_remote
    assert remote_ctor.call_count == 2


def test_get_instance_local_path_unchanged_when_remote_disabled(
    isolated_model_loader_remote_state,
):
    """Regression guard: with remote mode off (the default), get_instance()
    must still take the exact local llama-cpp load path — this reproduces the
    ModelLoader circuit-breaker tests' happy path to prove the new branch is
    a true no-op when disabled."""
    from app.engine.model_loader import ModelLoader

    loaded_model = MagicMock(name="local-llama-instance")

    with _local_load_patches(), patch(
        "app.engine.model_loader.get_hardware_profile",
        return_value={"gpu_list": []},
    ), patch(
        "app.engine.model_loader.config_store.get_active_model",
        return_value={"filename": "mock.gguf", "adapter": None},
    ), patch(
        "app.engine.model_loader.config_store.get_engine_config",
        return_value={"remote_engine_enabled": False, "engine_mode": "local"},
    ), patch(
        "subprocess.run", return_value=MagicMock(returncode=0),
    ), patch(
        "app.engine.model_loader.Llama", return_value=loaded_model,
    ) as llama_ctor, patch(
        "app.engine.model_loader.RemoteRPCModel"
    ) as remote_ctor:
        result = ModelLoader.get_instance()

    assert result is loaded_model
    llama_ctor.assert_called_once()
    remote_ctor.assert_not_called()
    assert ModelLoader._remote_instance is None


def test_local_fallback_factory_disables_remote_and_reenters_local_path(
    isolated_model_loader_remote_state,
):
    """Simulates a mid-generation remote failure: RemoteRPCModel's own
    on_fallback/local_fallback_factory contract (exercised for real in
    test_remote_rpc_timeout_disables_remote_and_streams_local_fallback) is
    wired by get_instance() to disable remote mode and re-enter this same
    method, landing on the local load path."""
    from app.engine.model_loader import ModelLoader

    engine_cfg = {
        "remote_engine_enabled": True,
        "remote_engine_url": "wss://example.lan:9090",
        "remote_engine_token": "tok-1",
        "remote_server_url": "wss://example.lan:9090",
        "remote_auth_token": "tok-1",
    }
    loaded_model = MagicMock(name="local-llama-instance")
    captured = {}

    def fake_remote_ctor(url, token, on_fallback=None, local_fallback_factory=None, **_kw):
        captured["on_fallback"] = on_fallback
        captured["local_fallback_factory"] = local_fallback_factory
        remote = MagicMock(name="remote-instance")
        remote.server_url = url
        remote.auth_token = token
        return remote

    def fake_get_engine_config():
        # First call (remote-mode check) sees remote enabled; once
        # _remote_fallback() disables it, subsequent calls see it disabled —
        # mirroring what config_store.set_remote_engine_config(False, ...)
        # actually persists to disk.
        return dict(engine_cfg)

    with _local_load_patches(), patch(
        "app.engine.model_loader.get_hardware_profile",
        return_value={"gpu_list": []},
    ), patch(
        "app.engine.model_loader.config_store.get_active_model",
        return_value={"filename": "mock.gguf", "adapter": None},
    ), patch(
        "app.engine.model_loader.config_store.get_engine_config",
        side_effect=fake_get_engine_config,
    ), patch(
        "app.engine.model_loader.config_store.set_remote_engine_config",
        side_effect=lambda enabled, url=None, token=None: engine_cfg.update(
            {"remote_engine_enabled": enabled}
        ),
    ), patch(
        "subprocess.run", return_value=MagicMock(returncode=0),
    ), patch(
        "app.engine.model_loader.Llama", return_value=loaded_model,
    ) as llama_ctor, patch(
        "app.engine.model_loader.RemoteRPCModel", side_effect=fake_remote_ctor,
    ):
        remote = ModelLoader.get_instance()
        assert remote.server_url == "wss://example.lan:9090"
        llama_ctor.assert_not_called()

        # Simulate the remote bridge failing mid-stream, exactly as
        # RemoteRPCModel._stream() does: call on_fallback(reason) first,
        # then local_fallback_factory().
        captured["on_fallback"]("connection dropped")
        assert engine_cfg["remote_engine_enabled"] is False
        assert ModelLoader._remote_instance is None

        local_llm = captured["local_fallback_factory"]()

    assert local_llm is loaded_model
    llama_ctor.assert_called_once()
