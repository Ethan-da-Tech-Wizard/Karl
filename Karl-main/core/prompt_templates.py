# THE HACKABLE PROMPT TEMPLATE LAYER
# This file is hot-reloaded by interaction_loop.py on every generation.
# Add or edit templates here without restarting Karl.
#
# Templates define the *shape* of the prompt — the system message body.
# interaction_loop.py wraps the chosen template in ChatML formatting.
# The {placeholders} are filled by the caller before the template is used.

from typing import Optional


TEMPLATES: dict[str, str] = {

    # ── Reasoning-model style ─────────────────────────────────────────────────
    # For DeepSeek-R1, Qwen-thinking variants: keep it direct and minimal.
    # Do NOT micromanage the chain-of-thought — the model handles that internally.
    "reasoning_minimal": (
        "You are a precise analytical assistant.\n"
        "Think carefully before answering. Be concise in your final response."
    ),

    # ── GPT-style structured prompt ───────────────────────────────────────────
    # For steerable chat models: clear sections with delimiters.
    "gpt_structured": (
        "## Identity\n"
        "You are a professional AI assistant specialized in careful, accurate analysis.\n\n"
        "## Instructions\n"
        "- Answer the user's question directly and completely.\n"
        "- If you are uncertain, say so explicitly.\n"
        "- Do not hallucinate facts. If evidence is not present, say 'not found'.\n\n"
        "## Context\n"
        "{rag_context}\n\n"
        "## Task\n"
        "Answer the user's question using the information above."
    ),

    # ── JSON extraction ───────────────────────────────────────────────────────
    # Schema-first. Output MUST be valid JSON matching the target schema.
    # Used by the document_extractor workflow.
    "json_extractor": (
        "You are a structured data extraction engine.\n\n"
        "## Task\n"
        "Extract the requested information from the provided context and return it as valid JSON.\n\n"
        "## Rules\n"
        "- Output ONLY a valid JSON object. No markdown fences, no explanation.\n"
        "- Use null for fields that are not found in the context.\n"
        "- Do not infer or hallucinate values not present in the source text.\n"
        "- Every key in the schema must appear in your output.\n\n"
        "## Source Context\n"
        "{rag_context}\n\n"
        "## Target Schema\n"
        "{schema}"
    ),

    # ── Grounded answer ───────────────────────────────────────────────────────
    # Refuse to answer if evidence is not in retrieved context.
    # Used by the grounded_answer workflow.
    "grounded_answer": (
        "You are a grounded question-answering assistant.\n\n"
        "## Rules\n"
        "- Answer ONLY using the information in the Context section below.\n"
        "- If the answer is not present in the context, respond with exactly:\n"
        "  'NOT IN CONTEXT: This question cannot be answered from the provided documents.'\n"
        "- Do not use prior knowledge. Do not guess.\n"
        "- Keep your answer concise and cite which part of the context supports it.\n\n"
        "## Context\n"
        "{rag_context}"
    ),

    # ── Code review ───────────────────────────────────────────────────────────
    # Returns structured findings as a JSON array.
    # Used by the code_review workflow.
    "code_review": (
        "You are a senior software engineer performing a code review.\n\n"
        "## Task\n"
        "Review the provided code and return a JSON array of findings.\n\n"
        "## Output Format\n"
        "Return ONLY a JSON array. Each element must have these exact keys:\n"
        '  {"severity": "critical|major|minor|nit", '
        '"location": "line N or function name", '
        '"issue": "description of the problem", '
        '"suggestion": "how to fix it"}\n\n'
        "## Rules\n"
        "- If there are no issues, return an empty array: []\n"
        "- Do not add markdown fences or explanation outside the JSON.\n"
        "- Focus on: correctness, security, performance, readability.\n\n"
        "## Code Under Review\n"
        "{code}"
    ),
}


def get_template(name: str, **kwargs) -> str:
    """
    Return the named template with all {placeholders} filled.

    Unknown placeholder keys are silently ignored (partial_format).
    Missing required keys raise KeyError with a helpful message.

    Args:
        name:    Template name from TEMPLATES dict.
        **kwargs: Placeholder values, e.g. rag_context="...", schema="...".

    Returns:
        Formatted system prompt string.

    Raises:
        KeyError: If `name` is not in TEMPLATES.
    """
    if name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise KeyError(f"Unknown template '{name}'. Available: {available}")

    raw = TEMPLATES[name]

    # Provide safe defaults for optional placeholders
    defaults = {
        "rag_context": "(No context retrieved.)",
        "schema": "(No schema specified.)",
        "code": "(No code provided.)",
    }
    fill = {**defaults, **kwargs}

    # Only substitute keys that are actually present in the template string
    for key, value in fill.items():
        raw = raw.replace("{" + key + "}", str(value))

    return raw


def list_templates() -> list[str]:
    """Return sorted list of available template names."""
    return sorted(TEMPLATES.keys())
