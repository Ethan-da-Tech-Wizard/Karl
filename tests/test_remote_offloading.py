from __future__ import annotations

import types


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
