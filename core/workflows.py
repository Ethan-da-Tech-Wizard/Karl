# WORKFLOW DEFINITIONS
# Each workflow is a named mode with a default template, RAG config, output
# schema, and eval grader. Workflows are the product surface; templates are
# the implementation detail.
#
# This file is intentionally data-only — no heavy logic lives here.
# The UI reads WORKFLOWS to populate the mode selector.
# The eval harness reads WORKFLOWS to know which grader to apply.



WORKFLOWS: dict[str, dict] = {

    # ── General Chat (default) ────────────────────────────────────────────────
    "general_chat": {
        "label": "General Chat",
        "template": "reasoning_minimal",
        "rag_top_k": 3,
        "require_rag": False,
        "output_schema": None,
        "eval_grader": "keyword_hit",
        "description": "Open-ended conversation. Thought stream visible as diagnostic.",
    },

    # ── Document Extractor ────────────────────────────────────────────────────
    "document_extractor": {
        "label": "Document Extractor",
        "template": "json_extractor",
        "rag_top_k": 5,
        "require_rag": True,
        "output_schema": {
            "type": "object",
            "description": "Flexible schema — set per-session via the config panel.",
            "example_keys": ["title", "date", "amount", "parties"],
        },
        "eval_grader": "json_valid",
        "description": (
            "Extracts structured JSON from ingested documents. "
            "RAG required. Output MUST be valid JSON."
        ),
    },

    # ── Grounded Answer ───────────────────────────────────────────────────────
    "grounded_answer": {
        "label": "Grounded Answer",
        "template": "grounded_answer",
        "rag_top_k": 5,
        "require_rag": True,
        "output_schema": None,
        "eval_grader": "groundedness",
        "description": (
            "Answers only from retrieved context. Refuses to speculate. "
            "Responds with NOT IN CONTEXT if evidence is absent."
        ),
    },

    # ── Code Review ───────────────────────────────────────────────────────────
    "code_review": {
        "label": "Code Review",
        "template": "code_review",
        "rag_top_k": 0,
        "require_rag": False,
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "location", "issue", "suggestion"],
            },
        },
        "eval_grader": "json_valid",
        "description": (
            "Reviews code for correctness, security, and readability. "
            "Returns a JSON array of findings."
        ),
    },
}


def get_workflow(name: str) -> dict:
    """
    Return the workflow config dict for the given name.

    Raises:
        KeyError: If `name` is not in WORKFLOWS.
    """
    if name not in WORKFLOWS:
        available = ", ".join(WORKFLOWS.keys())
        raise KeyError(f"Unknown workflow '{name}'. Available: {available}")
    return WORKFLOWS[name]


def list_workflows() -> list[tuple[str, str]]:
    """Return [(name, label), ...] sorted by label for UI population."""
    return sorted(
        [(k, v["label"]) for k, v in WORKFLOWS.items()],
        key=lambda x: x[1]
    )
