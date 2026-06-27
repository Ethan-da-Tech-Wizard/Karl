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
ENGINE_CONFIG_PATH = os.path.join("data", "engine_config.json")

DEFAULT_MODEL_FILENAME = "deepseek-r1-1.5b.gguf"
DEFAULT_N_CTX = 4096

# Schema version written to ui_config.json on every save. Increment when adding
# fields that require migration (e.g. renamed keys, changed defaults).
CONFIG_VERSION: int = 1

_registry_lock = threading.Lock()
_registry_cache: list[dict] | None = None
_registry_cache_mtime: float | None = None

ENGINE_CONFIG_DEFAULTS: dict[str, Any] = {
    "remote_engine_enabled": False,
    "remote_engine_url": "",
    "remote_engine_token": "",
    "engine_mode": "local",
    "remote_server_url": "",
    "remote_auth_token": "",
}


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
    """Return persisted speculative draft-model settings."""
    data = read_json(DRAFT_MODEL_PATH, default={})
    if not isinstance(data, dict):
        data = {}
    filename = data.get("filename") or None
    if filename is None:
        filename = registry_draft_model_filename(get_active_model()["filename"])
    return {
        "enabled": bool(data.get("enabled", False)),
        "filename": filename,
    }


def set_active_draft_model(filename: str | None, enabled: bool = False) -> bool:
    """Persist or clear the draft model. Pass None to disable speculative decoding."""
    return write_json_atomic(
        DRAFT_MODEL_PATH,
        {"enabled": bool(enabled), "filename": filename},
    )


def get_engine_config() -> dict[str, Any]:
    """Return persisted engine/offload settings with defaults applied."""
    data = read_json(ENGINE_CONFIG_PATH, default={})
    if not isinstance(data, dict):
        data = {}
    cfg = dict(ENGINE_CONFIG_DEFAULTS)
    cfg.update(data)
    return cfg


def set_remote_engine_config(
    enabled: bool,
    url: str | None = None,
    token: str | None = None,
) -> bool:
    """Persist remote-engine toggle while preserving existing engine settings."""
    cfg = get_engine_config()
    cfg["remote_engine_enabled"] = bool(enabled)
    cfg["engine_mode"] = "remote" if enabled else "local"
    if url is not None:
        cfg["remote_engine_url"] = url
        cfg["remote_server_url"] = url
    if token is not None:
        cfg["remote_engine_token"] = token
        cfg["remote_auth_token"] = token
    return write_json_atomic(ENGINE_CONFIG_PATH, cfg)


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


def registry_draft_model_filename(filename: str) -> str | None:
    """Look up a model registry companion draft GGUF filename."""
    entry = registry_entry(filename)
    if not entry:
        return None
    draft = entry.get("draft_model_filename")
    return str(draft) if draft else None


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
    "rag_threshold": 0.0,
    "rag_top_k": 3,
    "log_rotation_size_mb": 10,
    "log_retention_days": 30,
    "max_log_disk_size_mb": 1024,
    "single_session_auth": False,
    "enable_dynamic_scheduling": True,
    "thinking_temperature": 0.8,
    "answering_temperature": 0.1,
    "thermal_protection_enabled": True,
    "thermal_protection_threshold": 95,
    "quantized_kv_cache": False,
}

# Per-field validation rules: (type_or_types, min_value_or_None, max_value_or_None).
# Fields not listed here receive no range check (type check only via default type).
_UI_FIELD_RULES: dict[str, tuple] = {
    "rag_threshold":              (float,  0.0,  1.0),
    "rag_top_k":                  (int,    1,    100),
    "animation_intensity":        (float,  0.0,  2.0),
    "glow_strength":              (float,  0.0,  2.0),
    "log_rotation_size_mb":       (int,    1,    10240),
    "log_retention_days":         (int,    1,    3650),
    "max_log_disk_size_mb":       (int,    64,   102400),
    "thinking_temperature":       (float,  0.0,  2.0),
    "answering_temperature":      (float,  0.0,  2.0),
    "thermal_protection_threshold": (int,  50,   105),
}


def _validate_field(key: str, raw_value: Any, default_value: Any) -> Any:
    """Validate and coerce a single config field against its rule and default type.

    - If the field is in ``_UI_FIELD_RULES``, checks exact type and clamped range.
    - Otherwise checks that the value's type matches the default's type.
    - ``custom_accent`` accepts ``None`` *or* ``str``; any other type falls back.
    - Returns the coerced/accepted value, or ``default_value`` if validation fails.
    """
    # Special case: custom_accent may be None or str
    if key == "custom_accent":
        if raw_value is None or isinstance(raw_value, str):
            return raw_value
        return default_value

    rule = _UI_FIELD_RULES.get(key)
    if rule is not None:
        expected_type, lo, hi = rule
        # bool is a subclass of int — reject bool for int fields and vice-versa
        if type(raw_value) is not expected_type:  # noqa: E721
            # Allow int→float and float→int coercion for numeric fields only
            if expected_type is float and isinstance(raw_value, int) and not isinstance(raw_value, bool):
                raw_value = float(raw_value)
            elif expected_type is int and isinstance(raw_value, float) and not isinstance(raw_value, bool):
                raw_value = int(raw_value)
            else:
                return default_value
        if lo is not None and raw_value < lo:
            return default_value
        if hi is not None and raw_value > hi:
            return default_value
        return raw_value

    # Generic type check using default's type
    expected = type(default_value)
    if default_value is None:
        return raw_value  # None-typed defaults accept anything
    # Strict bool check — prevent int 1/0 masquerading as bool
    if expected is bool:
        if not isinstance(raw_value, bool):
            return default_value
        return raw_value
    if not isinstance(raw_value, expected):
        return default_value
    return raw_value


def _quarantine_config() -> None:
    """Rename a corrupt ui_config.json to .corrupt_<timestamp> so the bad file
    is preserved for debugging while Karl can start cleanly with defaults."""
    import time
    if not os.path.exists(UI_CONFIG_PATH):
        return
    try:
        ts = int(time.time())
        corrupt_path = UI_CONFIG_PATH + f".corrupt_{ts}"
        os.rename(UI_CONFIG_PATH, corrupt_path)
        logger.warning("Quarantined corrupt config to %s", corrupt_path)
    except OSError as exc:
        logger.warning("Failed to quarantine corrupt config: %s", exc)


def get_ui_config() -> dict:
    """Return persisted UI settings merged over defaults.

    Behaviour:
    - Missing file → return defaults (first-run condition, logged at DEBUG).
    - Corrupt JSON or non-dict root → quarantine the file, write fresh defaults,
      and return defaults.
    - Unknown keys in the file → silently ignored (forward-compatibility).
    - Known keys → type and range validated; out-of-range values fall back to
      their hardcoded defaults rather than crashing.
    - ``version`` key → stored but not validated against known fields; a future
      version mismatch can trigger migration logic here.
    - Falls back to legacy ``data/theme_config.json`` when ``ui_config.json``
      does not exist (old installs).
    """
    merged = dict(UI_CONFIG_DEFAULTS)

    raw = None
    if os.path.exists(UI_CONFIG_PATH):
        try:
            with open(UI_CONFIG_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            logger.warning("Corrupt ui_config.json (%s) — quarantining and restoring defaults", exc)
            _quarantine_config()
            save_ui_config(merged)  # write fresh defaults
            return merged

        if not isinstance(raw, dict):
            logger.warning(
                "ui_config.json root is %s, not dict — quarantining", type(raw).__name__
            )
            _quarantine_config()
            save_ui_config(merged)
            return merged

        # Read (and ignore unknown) version key — reserved for migration
        version = raw.get("version")
        if not isinstance(version, int):
            version = 0  # treat missing or non-int as v0

        for key, default in UI_CONFIG_DEFAULTS.items():
            if key in raw:
                merged[key] = _validate_field(key, raw[key], default)
        return merged

    # No ui_config.json — try legacy theme_config.json
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
    """Persist appearance settings (only known keys). Returns True on success.

    Always writes the ``version`` key at ``CONFIG_VERSION`` so load-time
    migration logic can detect schema age.
    """
    payload: dict[str, Any] = {key: config.get(key, default) for key, default in UI_CONFIG_DEFAULTS.items()}
    payload["version"] = CONFIG_VERSION
    return write_json_atomic(UI_CONFIG_PATH, payload, indent=2)


MCP_CONFIG_PATH = os.path.join("data", "mcp_config.json")
MCP_CONFIG_DEFAULT: dict = {"mcpServers": {}}


def get_mcp_config() -> dict:
    """Return MCP server configuration, falling back to an empty server map."""
    data = read_json(MCP_CONFIG_PATH, default=MCP_CONFIG_DEFAULT)
    if not isinstance(data, dict) or "mcpServers" not in data:
        return dict(MCP_CONFIG_DEFAULT)
    return data


def add_mcp_server(name: str, command: str, args: list[str], env: dict | None = None) -> bool:
    """Persist or replace one MCP server entry. Returns True on write success."""
    cfg = get_mcp_config()
    cfg["mcpServers"][name] = {"command": command, "args": args or []}
    if env:
        cfg["mcpServers"][name]["env"] = env
    return write_json_atomic(MCP_CONFIG_PATH, cfg, indent=2)


def remove_mcp_server(name: str) -> bool:
    """Remove an MCP server entry if present. Returns True on write success."""
    cfg = get_mcp_config()
    cfg["mcpServers"].pop(name, None)
    return write_json_atomic(MCP_CONFIG_PATH, cfg, indent=2)


def get_model_variants(base_model: str) -> list[dict]:
    """Return all registry variants for a given base_model name."""
    return [e for e in get_model_registry()
            if isinstance(e, dict) and e.get("base_model") == base_model]
