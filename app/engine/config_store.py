"""
Centralized JSON configuration store for Karl.

All reads/writes of the runtime config files under data/ go through this module:

- data/active_model.json        — active GGUF model + adapter (runtime state)
- data/model_registry.json      — source-controlled model tier registry
- data/ui_config.json           — persisted appearance settings
- data/theme_config.json        — legacy appearance file (read-only fallback)

Guarantees:
- Atomic writes (temp file + os.replace) so a crash mid-write never leaves
  corrupt JSON on disk.
- mtime-based caching for the model registry so it is parsed once per change,
  not once per call.
- Missing or corrupt files return documented defaults and log a warning with
  the file path and the underlying error — never a silent empty result.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from typing import Any

logger = logging.getLogger("karl.config_store")

ACTIVE_MODEL_PATH = os.path.join("data", "active_model.json")
MODEL_REGISTRY_PATH = os.path.join("data", "model_registry.json")
UI_CONFIG_PATH = os.path.join("data", "ui_config.json")
LEGACY_THEME_CONFIG_PATH = os.path.join("data", "theme_config.json")

DEFAULT_MODEL_FILENAME = "deepseek-r1-1.5b.gguf"
DEFAULT_N_CTX = 4096

_registry_lock = threading.Lock()
_registry_cache: list[dict] | None = None
_registry_cache_mtime: float | None = None


# ── generic JSON I/O ─────────────────────────────────────────────────────────

def read_json(path: str, default: Any = None) -> Any:
    """Read a JSON file, returning `default` on missing/corrupt file.

    Corrupt or unreadable files are logged with full context; a missing file
    is logged at debug level only (it is a normal first-run condition).
    """
    if not os.path.exists(path):
        logger.debug("config file not present, using default: %s", path)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        logger.warning("failed to read config file %s: %s", path, exc)
        return default


def write_json_atomic(path: str, data: Any, indent: int | None = None) -> bool:
    """Atomically write JSON: temp file in the same directory + os.replace.

    Returns True on success. Failures are logged and reported via the return
    value so callers can surface them to the user.
    """
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=os.path.basename(path) + ".", suffix=".tmp", dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.error("failed to write config file %s: %s", path, exc)
        return False


# ── active model ─────────────────────────────────────────────────────────────

def get_active_model() -> dict:
    """Return {"filename": str, "adapter": str | None} for the active model."""
    data = read_json(ACTIVE_MODEL_PATH, default={})
    if not isinstance(data, dict):
        logger.warning("unexpected payload in %s: %r", ACTIVE_MODEL_PATH, type(data))
        data = {}
    filename = data.get("filename") or data.get("model") or DEFAULT_MODEL_FILENAME
    return {"filename": filename, "adapter": data.get("adapter")}


def set_active_model(filename: str, adapter: str | None = None) -> bool:
    """Persist the active model selection. Returns True on success."""
    active: dict[str, Any] = {"filename": filename}
    if adapter:
        active["adapter"] = adapter
    return write_json_atomic(ACTIVE_MODEL_PATH, active)


DRAFT_MODEL_PATH = os.path.join("data", "draft_model.json")


def get_active_draft_model() -> dict:
    """Return {"filename": str | None} for the speculative draft model, or None if unconfigured."""
    data = read_json(DRAFT_MODEL_PATH, default={})
    if not isinstance(data, dict):
        data = {}
    return {"filename": data.get("filename") or None}


def set_active_draft_model(filename: str | None) -> bool:
    """Persist or clear the draft model. Pass None to disable speculative decoding."""
    return write_json_atomic(DRAFT_MODEL_PATH, {"filename": filename})


# ── model registry ───────────────────────────────────────────────────────────

def get_model_registry() -> list[dict]:
    """Return the model registry list, cached until the file's mtime changes."""
    global _registry_cache, _registry_cache_mtime
    try:
        mtime = os.path.getmtime(MODEL_REGISTRY_PATH)
    except OSError:
        mtime = None

    with _registry_lock:
        if _registry_cache is not None and mtime == _registry_cache_mtime:
            return _registry_cache

        data = read_json(MODEL_REGISTRY_PATH, default=[])
        if not isinstance(data, list):
            logger.warning(
                "unexpected payload in %s: %r", MODEL_REGISTRY_PATH, type(data)
            )
            data = []
        _registry_cache = data
        _registry_cache_mtime = mtime
        return _registry_cache


def registry_entry(filename: str) -> dict | None:
    """Return the registry entry for a model filename, or None."""
    for entry in get_model_registry():
        if isinstance(entry, dict) and entry.get("filename") == filename:
            return entry
    return None


def registry_n_ctx(filename: str) -> int:
    """Look up n_ctx for the given model filename (default 4096)."""
    entry = registry_entry(filename)
    if entry:
        try:
            return int(entry.get("n_ctx", DEFAULT_N_CTX))
        except (TypeError, ValueError):
            logger.warning("invalid n_ctx for %s in registry", filename)
    return DEFAULT_N_CTX


# ── adapter compatibility ────────────────────────────────────────────────────

def is_adapter_compatible(model_filename: str, adapter_name: str) -> bool:
    """Heuristic check that a LoRA adapter matches the base model size.

    Prefers the adapter's recorded base model from adapter_config.json and
    falls back to size-token matching on the names.
    """
    config_path = os.path.join("data", "adapters", adapter_name, "adapter_config.json")
    config = read_json(config_path, default=None)
    if isinstance(config, dict):
        base_model = str(config.get("base_model_name_or_path", "")).lower()
        model_fn = model_filename.lower()
        if "1.5b" in model_fn and "1.5b" in base_model:
            return True
        if "8b" in model_fn and "8b" in base_model:
            return True
    # Fallback to simple sub-string matching on name
    if "1.5b" in model_filename.lower() and "1.5b" in adapter_name.lower():
        return True
    if "8b" in model_filename.lower() and "8b" in adapter_name.lower():
        return True
    return False


# ── appearance config ────────────────────────────────────────────────────────

UI_CONFIG_DEFAULTS: dict[str, Any] = {
    "theme_preset": "Karl Obsidian Core",
    "custom_accent": None,
    "layout_preset": "Focused Workbench",
    "reduced_motion": False,
    "glow_enabled": True,
    "animation_intensity": 1.0,
    "glow_strength": 1.0,
    "theme_mode": "midnight",
    "log_rotation_size_mb": 10,
    "log_retention_days": 30,
}


def get_ui_config() -> dict:
    """Return persisted appearance settings merged over defaults.

    Falls back to the legacy data/theme_config.json (old field names) when
    data/ui_config.json does not exist.
    """
    merged = dict(UI_CONFIG_DEFAULTS)

    config = read_json(UI_CONFIG_PATH, default=None)
    if isinstance(config, dict):
        for key in merged:
            if key in config:
                merged[key] = config[key]
        return merged

    legacy = read_json(LEGACY_THEME_CONFIG_PATH, default=None)
    if isinstance(legacy, dict):
        theme_preset = legacy.get("theme_name", merged["theme_preset"])
        if theme_preset == "Karl Obsidian":
            theme_preset = "Karl Obsidian Core"
        merged["theme_preset"] = theme_preset
        merged["custom_accent"] = legacy.get("custom_accent")
        merged["reduced_motion"] = legacy.get("reduced_motion", False)
    return merged


def save_ui_config(config: dict) -> bool:
    """Persist appearance settings (only known keys). Returns True on success."""
    payload = {key: config.get(key, default) for key, default in UI_CONFIG_DEFAULTS.items()}
    return write_json_atomic(UI_CONFIG_PATH, payload, indent=2)
