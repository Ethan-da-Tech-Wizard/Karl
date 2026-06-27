"""Runtime network guard for Karl's offline-first backend."""

from __future__ import annotations

import logging
import os
import threading
from urllib.parse import urlparse


logger = logging.getLogger("karl.offline_guard")

_INSTALLED = False
_HF_OFFLINE_VARS = ("TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE", "HF_HUB_OFFLINE")
_hf_vars_applied: bool = False
_hf_vars_lock = threading.Lock()
_ORIGINAL_REQUESTS_REQUEST = None
_ORIGINAL_URLLIB_URLOPEN = None
_ORIGINAL_HTTPX_REQUEST = None
_ORIGINAL_HTTPX_CLIENT_REQUEST = None
_ORIGINAL_HTTPX_ASYNC_CLIENT_REQUEST = None

_LOCAL_HOSTS = {
    "",
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}


class OfflineNetworkError(RuntimeError):
    """Raised when backend code attempts external network I/O in offline mode."""


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def online_execution_enabled() -> bool:
    """Return True only when Karl has been explicitly allowed to go online."""
    if _truthy(os.environ.get("KARL_ONLINE_EXECUTION")):
        return True
    try:
        from app.engine import config_store

        return bool(config_store.get_ui_config().get("online_execution_enabled", False))
    except Exception as exc:
        logger.debug("could not read online execution config; defaulting offline: %s", exc)
        return False


def _is_local_url(url: object) -> bool:
    parsed = urlparse(str(url))
    if parsed.scheme in {"", "file"}:
        return True
    host = parsed.hostname or ""
    return host in _LOCAL_HOSTS


def assert_online_allowed(url: object = None, *, operation: str = "network request") -> None:
    """Raise when an external network operation is attempted in offline mode."""
    if url is not None and _is_local_url(url):
        return
    if online_execution_enabled():
        return
    target = f" to {url}" if url is not None else ""
    raise OfflineNetworkError(
        f"Blocked {operation}{target}: Karl is running in strict offline mode. "
        "Set data/ui_config.json online_execution_enabled=true or "
        "KARL_ONLINE_EXECUTION=1 to permit external network access."
    )


def install() -> None:
    """Patch common Python HTTP clients so backend downloads fail closed offline."""
    global _INSTALLED
    global _ORIGINAL_REQUESTS_REQUEST
    global _ORIGINAL_URLLIB_URLOPEN
    global _ORIGINAL_HTTPX_REQUEST
    global _ORIGINAL_HTTPX_CLIENT_REQUEST
    global _ORIGINAL_HTTPX_ASYNC_CLIENT_REQUEST

    if _INSTALLED:
        return
    _INSTALLED = True

    try:
        import requests

        _ORIGINAL_REQUESTS_REQUEST = requests.sessions.Session.request

        def guarded_requests_request(session, method, url, *args, **kwargs):
            assert_online_allowed(url, operation=f"HTTP {str(method).upper()}")
            return _ORIGINAL_REQUESTS_REQUEST(session, method, url, *args, **kwargs)

        requests.sessions.Session.request = guarded_requests_request
    except Exception as exc:
        logger.debug("requests offline guard not installed: %s", exc)

    try:
        import urllib.request

        _ORIGINAL_URLLIB_URLOPEN = urllib.request.urlopen

        def guarded_urlopen(url, *args, **kwargs):
            target = getattr(url, "full_url", url)
            assert_online_allowed(target, operation="urllib request")
            return _ORIGINAL_URLLIB_URLOPEN(url, *args, **kwargs)

        urllib.request.urlopen = guarded_urlopen
    except Exception as exc:
        logger.debug("urllib offline guard not installed: %s", exc)

    try:
        import httpx

        _ORIGINAL_HTTPX_REQUEST = httpx.request
        _ORIGINAL_HTTPX_CLIENT_REQUEST = httpx.Client.request
        _ORIGINAL_HTTPX_ASYNC_CLIENT_REQUEST = httpx.AsyncClient.request

        def guarded_httpx_request(method, url, *args, **kwargs):
            assert_online_allowed(url, operation=f"HTTP {str(method).upper()}")
            return _ORIGINAL_HTTPX_REQUEST(method, url, *args, **kwargs)

        def guarded_httpx_client_request(self, method, url, *args, **kwargs):
            assert_online_allowed(url, operation=f"HTTP {str(method).upper()}")
            return _ORIGINAL_HTTPX_CLIENT_REQUEST(self, method, url, *args, **kwargs)

        async def guarded_httpx_async_client_request(self, method, url, *args, **kwargs):
            assert_online_allowed(url, operation=f"HTTP {str(method).upper()}")
            return await _ORIGINAL_HTTPX_ASYNC_CLIENT_REQUEST(self, method, url, *args, **kwargs)

        httpx.request = guarded_httpx_request
        httpx.Client.request = guarded_httpx_client_request
        httpx.AsyncClient.request = guarded_httpx_async_client_request
    except Exception as exc:
        logger.debug("httpx offline guard not installed: %s", exc)


def apply_for_current_config() -> None:
    """
    Sync HuggingFace offline env vars with the current runtime config.

    Call this whenever the config may have changed (e.g., at first model load).
    The HTTP-layer patches installed by install() perform dynamic checks and need
    no re-application; this function only governs the coarser HF library controls.
    """
    global _hf_vars_applied

    with _hf_vars_lock:
        if online_execution_enabled():
            if _hf_vars_applied:
                for var in _HF_OFFLINE_VARS:
                    os.environ.pop(var, None)
                _hf_vars_applied = False
                logger.info("Offline HF env vars cleared — online execution enabled.")
        else:
            if not _hf_vars_applied:
                for var in _HF_OFFLINE_VARS:
                    os.environ.setdefault(var, "1")
                _hf_vars_applied = True
                logger.info(
                    "HF offline env vars applied (%s). "
                    "Set KARL_ONLINE_EXECUTION=1 or online_execution_enabled=true to allow downloads.",
                    ", ".join(_HF_OFFLINE_VARS),
                )


def is_guard_installed() -> bool:
    """Return True if install() has been called."""
    return _INSTALLED


def hf_vars_applied() -> bool:
    """Return True if the HuggingFace offline env vars are currently set."""
    with _hf_vars_lock:
        return _hf_vars_applied
