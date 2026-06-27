"""Agent profile definitions injected into the active system prompt."""

import json
import os

_BUILTIN_PROFILES = {
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

# Immutable snapshot of the built-in profiles. Tests and external code can
# compare against DEFAULT_PROFILES to detect user-added custom profiles.
DEFAULT_PROFILES: dict = dict(_BUILTIN_PROFILES)

# Live mutable registry. Starts as a copy of defaults and is extended by
# reload_profiles() when custom agents are found in data/custom_agents.json.
AGENT_PROFILES: dict = dict(_BUILTIN_PROFILES)

_CUSTOM_AGENTS_PATH = os.path.join("data", "custom_agents.json")


def reload_profiles() -> None:
    """Reload AGENT_PROFILES from disk, merging built-ins with any custom agents.

    Custom agents are stored in ``data/custom_agents.json`` as a dict mapping
    profile name to profile dict (same schema as AGENT_PROFILES).  Missing or
    corrupt files are silently ignored and the registry resets to defaults.

    Built-in profile names cannot be overridden by custom entries; any custom
    entry whose name collides with a built-in is silently dropped.
    """
    AGENT_PROFILES.clear()
    AGENT_PROFILES.update(_BUILTIN_PROFILES)

    if not os.path.exists(_CUSTOM_AGENTS_PATH):
        return

    try:
        with open(_CUSTOM_AGENTS_PATH, "r", encoding="utf-8") as f:
            custom = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    if not isinstance(custom, dict):
        return

    for name, profile in custom.items():
        if not isinstance(name, str) or not isinstance(profile, dict):
            continue
        if name in _BUILTIN_PROFILES:
            continue  # never let custom profiles shadow built-ins
        AGENT_PROFILES[name] = profile

