"""
Karl's default system prompt — single source of truth.

Several call sites need this exact text: the Workbench's initial system
prompt field, the System Config "Defaults" panel, the WebSocket
submit_chat RPC's fallback when no system_prompt is supplied, and
core.interaction_loop.build_prompt()'s is_default check (which recognizes
it — and its historical predecessors, kept in LEGACY_DEFAULT_SYSTEM_PROMPTS
for old saved sessions — to decide whether the greeting/reasoning shortcuts
apply). Import from here rather than re-typing the string: a wording tweak
made in only one place is exactly how is_default silently stopped matching
before (see the "disable reasoning pre-seed" fix).
"""

KARL_IDENTITY = "You are Karl, a precise and thoughtful AI assistant. Always respond in English."

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
})
