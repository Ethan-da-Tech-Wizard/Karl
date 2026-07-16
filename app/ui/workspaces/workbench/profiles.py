"""Agent profile definitions injected into the active system prompt.

Architecture
------------
There are two layers:

1. ``_BUILTIN_PROFILES`` — hardcoded defaults for the six built-in agent
   personas.  These are the "flavours" shipped with Karl and are never
   modified on disk.

2. ``data/profile_overrides.json`` — a JSON dict that maps a profile key to a
   replacement prompt string.  Any profile (built-in *or* custom) can have an
   override stored here.  On load, ``reload_profiles()`` merges overrides on
   top of the defaults so the rest of the codebase always sees a single,
   already-merged ``AGENT_PROFILES`` dict.

This means:
* Built-in prompts are preserved as read-only defaults.
* Users can edit any profile's prompt from the UI.
* A "Reset to default" action removes the override for a built-in, restoring
  the hardcoded text.
* Custom agents (``data/custom_agents.json``) still work exactly as before.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger("karl.profiles")

# ── Hardcoded built-in profiles ───────────────────────────────────────────────

_BUILTIN_PROFILES: dict[str, dict] = {
    "karl": {
        "label": "Karl",
        "description": "Balanced analytical assistant for general work.",
        "prompt": "",
    },
    "architect": {
        "label": "Architect",
        "description": "Plans systems, breaks work into phases, and calls out file boundaries.",
        "prompt": (
            "Active agent profile: Architect. Focus on system design, implementation planning, "
            "dependency mapping, risk analysis, and clear sequencing before code-level detail."
        ),
    },
    "coder": {
        "label": "Coder",
        "description": "Implementation-focused engineer for concrete code changes and fixes.",
        "prompt": (
            "Active agent profile: Coder. Focus on practical implementation, precise code behavior, "
            "minimal safe edits, and runnable verification steps."
        ),
    },
    "reviewer": {
        "label": "Reviewer",
        "description": "Code-review stance: bugs, regressions, tests, and maintainability first.",
        "prompt": (
            "Active agent profile: Reviewer. Prioritize correctness bugs, regressions, missing tests, "
            "security issues, and maintainability risks. Lead with concrete findings."
        ),
    },
    "debugger": {
        "label": "Debugger",
        "description": "Diagnoses errors, logs, screenshots, stack traces, and runtime failures.",
        "prompt": (
            "Active agent profile: Debugger. Focus on symptoms, root cause, reproduction steps, "
            "logs, stack traces, and the smallest fix that proves the issue is resolved."
        ),
    },
    "vision": {
        "label": "Vision",
        "description": "Screenshot/image analysis with OCR, UI, document, and code-error awareness.",
        "prompt": (
            "Active agent profile: Vision. For attached images or OCR, describe only visible evidence, "
            "separate observation from inference, and focus on accurate screenshot, document, UI, or error analysis."
        ),
    },
}

# Immutable snapshot — tests and external code can compare against this to
# detect which profiles are built-in vs user-added.
DEFAULT_PROFILES: dict = dict(_BUILTIN_PROFILES)

# Live mutable registry.  Always access this after calling reload_profiles().
AGENT_PROFILES: dict = dict(_BUILTIN_PROFILES)

# ── Paths ─────────────────────────────────────────────────────────────────────

_CUSTOM_AGENTS_PATH    = os.path.join("data", "custom_agents.json")
_OVERRIDES_PATH        = os.path.join("data", "profile_overrides.json")


# ── Override persistence helpers ──────────────────────────────────────────────

def _load_overrides() -> dict[str, str]:
    """Return the raw overrides dict from disk (key → prompt string)."""
    if not os.path.exists(_OVERRIDES_PATH):
        return {}
    try:
        with open(_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}
    except (json.JSONDecodeError, OSError):
        logger.warning("profile_overrides.json is corrupt — ignoring overrides.")
        return {}


def _save_overrides(overrides: dict[str, str]) -> bool:
    """Atomically write overrides dict to disk. Returns True on success."""
    try:
        os.makedirs("data", exist_ok=True)
        tmp = _OVERRIDES_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _OVERRIDES_PATH)
        return True
    except OSError as exc:
        logger.error("Failed to save profile_overrides.json: %s", exc)
        return False


def save_profile_override(key: str, prompt: str) -> bool:
    """Persist a user-edited prompt for *key* and reload the registry.

    Works for both built-in profiles (overrides the hardcoded default) and
    custom agents (overrides their stored prompt).

    Returns True on success.
    """
    overrides = _load_overrides()
    overrides[key] = prompt
    ok = _save_overrides(overrides)
    if ok:
        reload_profiles()
    return ok


def delete_profile_override(key: str) -> bool:
    """Remove the override for *key* and reload the registry.

    For built-in profiles this restores the hardcoded default prompt.
    For custom agents this restores the prompt stored in custom_agents.json.

    Returns True on success (or True if there was nothing to delete).
    """
    overrides = _load_overrides()
    if key not in overrides:
        return True
    del overrides[key]
    ok = _save_overrides(overrides)
    if ok:
        reload_profiles()
    return ok


def get_default_prompt(key: str) -> str:
    """Return the hardcoded default prompt for *key*, ignoring any override.

    For custom agents (not in ``_BUILTIN_PROFILES``) the 'default' is the
    prompt stored in ``custom_agents.json``; this helper returns an empty
    string for those since there's no pre-override baseline.
    """
    return _BUILTIN_PROFILES.get(key, {}).get("prompt", "")


def is_overridden(key: str) -> bool:
    """Return True if *key* has a user override in profile_overrides.json."""
    return key in _load_overrides()


# ── Registry reload ───────────────────────────────────────────────────────────

def reload_profiles() -> None:
    """Rebuild AGENT_PROFILES by merging built-ins → custom agents → overrides.

    Layer order (later wins):
    1. Hardcoded ``_BUILTIN_PROFILES`` — always the starting point.
    2. ``data/custom_agents.json`` — user-defined extra profiles.
       Custom entries that collide with built-in *names* are dropped to
       prevent shadowing (same behaviour as before).
    3. ``data/profile_overrides.json`` — per-profile prompt overrides.
       An override replaces only the ``prompt`` field; label and description
       remain unchanged.
    """
    AGENT_PROFILES.clear()
    AGENT_PROFILES.update(_BUILTIN_PROFILES)

    # ── Layer 2: custom agents ────────────────────────────────────────────────
    if os.path.exists(_CUSTOM_AGENTS_PATH):
        try:
            with open(_CUSTOM_AGENTS_PATH, "r", encoding="utf-8") as f:
                custom = json.load(f)
            if isinstance(custom, dict):
                for name, profile in custom.items():
                    if not isinstance(name, str) or not isinstance(profile, dict):
                        continue
                    if name in _BUILTIN_PROFILES:
                        continue  # never shadow built-ins
                    AGENT_PROFILES[name] = profile
        except (json.JSONDecodeError, OSError):
            pass

    # ── Layer 3: user overrides ───────────────────────────────────────────────
    overrides = _load_overrides()
    for key, prompt in overrides.items():
        if key in AGENT_PROFILES:
            # Deep-copy the profile entry before mutating so the built-in
            # snapshot is never touched.
            AGENT_PROFILES[key] = dict(AGENT_PROFILES[key])
            AGENT_PROFILES[key]["prompt"] = prompt
