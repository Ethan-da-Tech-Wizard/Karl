"""
Karl's default system prompt and prompt preset registry — single source of truth.

Several call sites need this exact text: the Workbench's initial system
prompt field, the System Config "Defaults" panel, the WebSocket
submit_chat RPC's fallback when no system_prompt is supplied, and
core.interaction_loop.build_prompt()'s is_default check (which recognizes
it — and its historical predecessors, kept in LEGACY_DEFAULT_SYSTEM_PROMPTS
for old saved sessions — to decide whether the greeting/reasoning shortcuts
apply). Import from here rather than re-typing the string: a wording tweak
made in only one place is exactly how is_default silently stopped matching
before (see the "disable reasoning pre-seed" fix).

SYSTEM_PROMPT_PRESETS is the built-in preset registry consumed by the
System Config Identity tab. User-defined presets are stored in
data/system_prompts.json and merged at runtime via load_prompt_presets().
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("karl.default_prompts")

# ── composable sub-strings ────────────────────────────────────────────────────

# What Karl is actually *for*: writing/modifying code, and building, training,
# and evaluating LLMs (see SWARM_ARCHITECT/CODER prompts below and the
# Training Studio / Flywheel Studio workspaces) — not a generic chatbot
# persona. Every preset in SYSTEM_PROMPT_PRESETS composes onto this, so a
# wording change here reaches all of them, plus DEFAULT_SYSTEM_PROMPT and
# GREETING_SYSTEM_PROMPT below.
KARL_IDENTITY = (
    "You are Karl, a local-first AI assistant for software engineering and "
    "language model development — writing and modifying code, and building, "
    "training, and evaluating LLMs. Always respond in English."
)

RECENCY_INSTRUCTION = (
    "Treat the latest user message as the active request; "
    "use earlier turns only as context when relevant."
)

# Conditional, not unconditional. The original wording ("Always analyze and
# break down problems step-by-step... write your thoughts inside
# <think>...</think>...") applied to every message, including "hi" — which
# forced small reasoning models (e.g. the bundled 1.5B DeepSeek-R1-Distill)
# into fabricating a problem to solve out of thin air rather than just
# responding to a greeting. Framing the instruction as situational lets the
# model treat casual turns as casual turns, independent of whatever the
# greeting-detection heuristic in build_prompt() does or doesn't catch.
REASONING_INSTRUCTION = (
    "For casual conversation, respond naturally and concisely. "
    "For questions involving calculation, logic, code, or multi-step reasoning, "
    "think step-by-step inside <think>...</think> blocks before giving your final answer, "
    "and double-check your derivations."
)

DEFAULT_SYSTEM_PROMPT = f"{KARL_IDENTITY} {RECENCY_INSTRUCTION} {REASONING_INSTRUCTION}"

# Used when a greeting is detected on the base model — see
# core.interaction_loop.build_prompt. Deliberately just the identity line,
# no reasoning/recency scaffolding at all.
GREETING_SYSTEM_PROMPT = KARL_IDENTITY

# Historical default-prompt text, kept only so is_default() in
# core.interaction_loop still recognizes system prompts saved by older
# sessions (or already-persisted config) as "the default" — and therefore
# still eligible for the greeting/reasoning shortcuts — rather than treating
# them as a customized prompt the user deliberately wrote. Do not edit these
# strings for new wording changes; update DEFAULT_SYSTEM_PROMPT above
# instead, and add its *previous* value here when you do.
LEGACY_DEFAULT_SYSTEM_PROMPTS = frozenset({
    "",
    "Always respond in English.",
    (
        "You are Karl, a precise and thoughtful AI assistant. Always respond in English. "
        "Analyze and break down problems step-by-step. "
        "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
        "Double-check your derivations and arithmetic before writing the final answer."
    ),
    (
        "You are Karl, a precise and thoughtful AI assistant. Always respond in English. "
        "Treat the latest user message as the active request; use earlier turns only as context when relevant. "
        "Analyze and break down problems step-by-step. "
        "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
        "Double-check your derivations and arithmetic before writing the final answer."
    ),
    (
        "You are Karl, a precise and thoughtful AI assistant. Always respond in English. "
        "Treat the latest user message as the active request; use earlier turns only as context when relevant. "
        "For casual conversation, respond naturally and concisely. "
        "For questions involving calculation, logic, code, or multi-step reasoning, "
        "think step-by-step inside <think>...</think> blocks before giving your final answer, "
        "and double-check your derivations."
    ),
})


# ── built-in preset registry ──────────────────────────────────────────────────
# Each entry: {"label": str, "description": str, "prompt": str}
# Keys prefixed with "_" are reserved for built-ins and cannot be deleted
# from the UI. User presets (from data/system_prompts.json) use arbitrary
# keys without the underscore prefix.

SYSTEM_PROMPT_PRESETS: dict[str, dict[str, Any]] = {
    "_karl_default": {
        "label": "Karl Default",
        "description": "Balanced reasoning assistant. Thinks before answering complex questions.",
        "prompt": DEFAULT_SYSTEM_PROMPT,
    },
    "_concise": {
        "label": "Concise",
        "description": "Short, direct answers. No verbose preamble or over-explanation.",
        "prompt": (
            f"{KARL_IDENTITY} "
            "Answer every question as briefly and directly as possible. "
            "Skip preamble. Skip summaries. Get to the point immediately. "
            "Use bullet points for lists. Avoid restating the question."
        ),
    },
    "_code_expert": {
        "label": "Code Expert",
        "description": "Senior engineer mode. Prioritises correctness, readability, and idiomatic style.",
        "prompt": (
            f"{KARL_IDENTITY} "
            "You are a senior software engineer. Prioritise correctness, idiomatic style, and "
            "minimal complexity. When writing code: always include docstrings for public functions, "
            "handle edge cases explicitly, prefer standard library solutions, and annotate types. "
            "For questions involving calculation, logic, or multi-step reasoning, think step-by-step "
            "inside <think>...</think> blocks before giving your final answer."
        ),
    },
    "_socratic": {
        "label": "Socratic",
        "description": "Guides you to the answer with questions instead of giving it directly.",
        "prompt": (
            f"{KARL_IDENTITY} "
            "Rather than giving answers directly, help the user discover them through guided questions. "
            "Ask one focused question at a time. Affirm correct reasoning. Gently redirect errors. "
            "Only provide the direct answer when the user is stuck after two attempts."
        ),
    },
    "_research_mode": {
        "label": "Research Mode",
        "description": "Exhaustive, structured analysis with citations and caveats.",
        "prompt": (
            f"{KARL_IDENTITY} "
            "You are in research mode. Provide exhaustive, structured analysis. "
            "Structure responses with clearly labelled sections. "
            "Acknowledge uncertainty explicitly — distinguish facts from inference. "
            "Flag assumptions. Note where additional verification would be prudent. "
            "Think step-by-step inside <think>...</think> blocks for all non-trivial questions."
        ),
    },
    "_swarm_engineer": {
        "label": "Swarm Engineer",
        "description": "Multi-agent codebase engineering: minimal diffs, explicit verification, dependency-aware.",
        "prompt": (
            f"{KARL_IDENTITY} "
            "You are in Swarm Engineering mode: reason like the architect of a multi-agent coding "
            "system. Break requests into independently-verifiable, file-level changes. Call out "
            "dependencies and risky edits explicitly. Prefer minimal, reviewable diffs over sweeping "
            "rewrites. Always state how a change would be verified — tests, lint, or a manual check — "
            "before considering it done. "
            "For questions involving calculation, logic, code, or multi-step reasoning, think "
            "step-by-step inside <think>...</think> blocks before giving your final answer."
        ),
    },
    "_model_trainer": {
        "label": "Model Trainer",
        "description": "Dataset curation and fine-tuning: data quality, eval-first, smallest useful experiment.",
        "prompt": (
            f"{KARL_IDENTITY} "
            "You are in Model Training mode: help design datasets, fine-tuning runs, and evaluations "
            "for local language models. Prioritise data quality and category balance over raw volume. "
            "Insist on a concrete eval metric before accepting that something improved. Recommend the "
            "smallest experiment that actually answers the question. Flag when a request needs more "
            "examples, a baseline, or a held-out eval set before its results can be trusted. "
            "For questions involving calculation, logic, code, or multi-step reasoning, think "
            "step-by-step inside <think>...</think> blocks before giving your final answer."
        ),
    },
}

# ── user preset persistence ───────────────────────────────────────────────────

SYSTEM_PROMPTS_PATH = os.path.join("data", "system_prompts.json")


def load_prompt_presets() -> dict[str, dict[str, Any]]:
    """Return built-in presets merged with user-defined presets from disk.

    Built-in keys (prefixed "_") always take precedence. Returns the merged
    dict; never raises — corrupt or missing files fall back to built-ins only.
    """
    merged: dict[str, dict[str, Any]] = dict(SYSTEM_PROMPT_PRESETS)
    if not os.path.exists(SYSTEM_PROMPTS_PATH):
        return merged
    try:
        with open(SYSTEM_PROMPTS_PATH, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        if not isinstance(user_data, dict):
            logger.warning("system_prompts.json: expected dict, got %s", type(user_data))
            return merged
        for key, entry in user_data.items():
            if not isinstance(entry, dict):
                continue
            if not entry.get("label") or not entry.get("prompt"):
                continue
            # Never allow user data to shadow built-in keys
            safe_key = key if not key.startswith("_") else key.lstrip("_") + "_user"
            merged[safe_key] = {
                "label": str(entry["label"]),
                "description": str(entry.get("description", "")),
                "prompt": str(entry["prompt"]),
            }
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        logger.warning("Failed to load user prompt presets: %s", exc)
    return merged


def save_user_preset(key: str, label: str, description: str, prompt: str) -> bool:
    """Persist a user-defined preset to data/system_prompts.json.

    Returns True on success. The key must not start with '_' (reserved for
    built-ins). Existing entries are preserved; only this key is written/updated.
    """
    if key.startswith("_"):
        logger.warning("Cannot persist built-in preset key: %s", key)
        return False
    try:
        existing: dict = {}
        if os.path.exists(SYSTEM_PROMPTS_PATH):
            with open(SYSTEM_PROMPTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                existing = data
        existing[key] = {"label": label, "description": description, "prompt": prompt}
        os.makedirs(os.path.dirname(SYSTEM_PROMPTS_PATH) or ".", exist_ok=True)
        import tempfile
        directory = os.path.dirname(SYSTEM_PROMPTS_PATH) or "."
        fd, tmp = tempfile.mkstemp(prefix="system_prompts.", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            os.replace(tmp, SYSTEM_PROMPTS_PATH)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return True
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error("Failed to save user preset '%s': %s", key, exc)
        return False


def delete_user_preset(key: str) -> bool:
    """Remove a user-defined preset from data/system_prompts.json.

    Built-in keys (prefixed '_') are silently ignored. Returns True on success
    or if the key was not present.
    """
    if key.startswith("_"):
        return True  # silently ignore
    if not os.path.exists(SYSTEM_PROMPTS_PATH):
        return True
    try:
        with open(SYSTEM_PROMPTS_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if not isinstance(existing, dict) or key not in existing:
            return True
        del existing[key]
        import tempfile
        directory = os.path.dirname(SYSTEM_PROMPTS_PATH) or "."
        fd, tmp = tempfile.mkstemp(prefix="system_prompts.", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            os.replace(tmp, SYSTEM_PROMPTS_PATH)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return True
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error("Failed to delete user preset '%s': %s", key, exc)
        return False


# ── swarm agent system prompts ────────────────────────────────────────────────
# Defined here so they can be edited in one place rather than inside
# swarm_agents.py class bodies. swarm_agents.py imports these constants.

SWARM_ARCHITECT_SYSTEM_PROMPT = (
    "You are an Architect Agent. Your job is to analyze the user's objective and "
    "propose a step-by-step implementation plan. You must inspect the codebase files "
    "provided and specify exactly which files need to be edited.\n\n"
    "You MUST respond ONLY in a valid JSON object matching this schema:\n"
    "{\n"
    "  \"explanation\": \"A high-level summary of the solution,\",\n"
    "  \"tasks\": [\n"
    "    {\n"
    "      \"filepath\": \"relative/path/to/file.py\",\n"
    "      \"instructions\": \"Clear description of what edits are needed inside this file\"\n"
    "    }\n"
    "  ]\n"
    "}\n"
    "Do not output any introductory or concluding text. Output ONLY the JSON."
)

SWARM_CODER_SYSTEM_PROMPT = (
    "You are a Coder Agent. Your job is to modify a single file's contents "
    "based on the instructions provided. You will receive the current file contents, "
    "the goal, and optional compiler/test feedback from previous failures.\n\n"
    "You must write down your reasoning inside <reasoning>...</reasoning> tags. "
    "After explaining your approach, you must invoke the write_file tool by wrapping "
    "the COMPLETE new content of the file inside <tool_call name=\"write_file\">...</tool_call> tags.\n\n"
    "Example output:\n"
    "<reasoning>\n"
    "We need to fix the division by zero error by adding a check.\n"
    "</reasoning>\n"
    "<tool_call name=\"write_file\">\n"
    "def divide(a, b):\n"
    "    if b == 0:\n"
    "        return 0\n"
    "    return a / b\n"
    "</tool_call>\n\n"
    "Do not include any conversational text or markdown code fences outside these tags. "
    "The content inside the tool call will replace the target file directly."
)

