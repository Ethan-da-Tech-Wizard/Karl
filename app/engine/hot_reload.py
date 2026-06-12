from __future__ import annotations

import importlib
import logging
import py_compile
from types import ModuleType
from typing import Callable


def compile_and_reload(
    module: ModuleType,
    label: str,
    notice: Callable[[str], None] | None = None,
    logger: logging.Logger | None = None,
) -> ModuleType:
    """Reload a hackable module only after it compiles cleanly.

    If the user saves a broken file, keep the last successfully imported module
    active and surface a clear notice instead of failing generation mid-run.
    """
    log = logger or logging.getLogger("karl.hot_reload")
    path = getattr(module, "__file__", None)
    if not path:
        message = f"{label}: reload skipped because module path is unknown"
        log.warning(message)
        if notice:
            notice(message)
        return module

    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        detail = exc.msg or str(exc)
        message = f"{label}: hot-reload blocked by compile error: {detail}"
        log.warning(message)
        if notice:
            notice(message)
        return module

    try:
        reloaded = importlib.reload(module)
    except Exception as exc:
        message = f"{label}: hot-reload failed, keeping previous module: {exc}"
        log.warning(message, exc_info=True)
        if notice:
            notice(message)
        return module

    if notice:
        notice(f"{label}: reloaded")
    return reloaded
