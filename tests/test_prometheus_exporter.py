from types import SimpleNamespace

import tests.qt_test_helper  # noqa: F401

from websockets.datastructures import Headers

from app.engine.websocket_server import WebSocketServerManager


def make_manager():
    manager = WebSocketServerManager.__new__(WebSocketServerManager)
    manager.clients = set()
    manager.last_generation_metrics = {
        "prefill_duration_seconds": 0.1234,
        "tokens_per_second": 42.5,
        "kv_cache_hit_rate": 0.75,
        "vram_delta_mb": 256.0,
    }
    return manager


def make_request(path, headers=None):
    return SimpleNamespace(path=path, headers=Headers(headers or []))


def response_text(response):
    return bytes(response.body).decode("utf-8")


def test_prometheus_metrics_exposition_contains_expected_headers():
    manager = make_manager()
    manager.clients = {object()}

    body = manager._prometheus_metrics()

    assert "# HELP karl_active_connections Number of active WebSocket clients" in body
    assert "# TYPE karl_active_connections gauge" in body
    assert "karl_active_connections 1" in body
    assert "# HELP karl_system_memory_usage_bytes" in body
    assert "# TYPE karl_system_memory_usage_bytes gauge" in body
    assert "# HELP karl_prefill_duration_seconds" in body
    assert "# TYPE karl_tokens_per_second gauge" in body
    assert "# TYPE karl_kv_cache_hit_rate gauge" in body
    assert "# TYPE karl_vram_delta_mb gauge" in body


def test_metrics_http_request_returns_200_prometheus_text():
    manager = make_manager()

    response = manager._process_http_request(None, make_request("/metrics"))

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"
    body = response_text(response)
    assert "# HELP karl_active_connections" in body
    assert "# TYPE karl_active_connections gauge" in body


def test_non_websocket_http_request_returns_404():
    manager = make_manager()

    response = manager._process_http_request(None, make_request("/not-metrics"))

    assert response.status_code == 404
    assert response_text(response) == "Not Found\n"


def test_websocket_upgrade_bypasses_http_interceptor():
    manager = make_manager()
    request = make_request(
        "/?token=test-token",
        [("Upgrade", "websocket"), ("Connection", "Upgrade")],
    )

    assert manager._process_http_request(None, request) is None


def test_generation_diagnostics_update_last_metrics():
    manager = make_manager()

    manager._record_generation_metrics({
        "prefill_duration_sec": 0.5,
        "tokens_per_second": 20.0,
        "prefill_tokens_count": 100,
        "kv_cache_hits": 25,
        "vram_usage_mb_delta": -12.5,
    })

    assert manager.last_generation_metrics["prefill_duration_seconds"] == 0.5
    assert manager.last_generation_metrics["tokens_per_second"] == 20.0
    assert manager.last_generation_metrics["kv_cache_hit_rate"] == 0.25
    assert manager.last_generation_metrics["vram_delta_mb"] == -12.5
