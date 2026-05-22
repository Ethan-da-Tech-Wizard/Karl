"""
Eval Graders — Karl Workbench
==============================
Collection of pure functions that score a model output against an expected
answer. All graders return a dict:

    {"passed": bool, "score": float, "detail": str}

Graders are intentionally side-effect-free and dependency-light so they can
run in CI, in the headless eval harness, or interactively.
"""

import json
import re
from typing import Any


# ── exact_match ───────────────────────────────────────────────────────────────

def exact_match(output: str, expected: str) -> dict:
    """
    Pass if output.strip() == expected.strip() (case-insensitive).
    Useful for short, deterministic answers (IDs, labels, yes/no).
    """
    clean_out = output.strip().lower()
    clean_exp = expected.strip().lower()
    passed = clean_out == clean_exp
    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "detail": f"exact_match: {'PASS' if passed else 'FAIL'} | got={output.strip()!r} expected={expected.strip()!r}",
    }


# ── json_valid ────────────────────────────────────────────────────────────────

def json_valid(output: str, schema_keys: list[str] | None = None) -> dict:
    """
    Pass if output is valid JSON and contains all required schema_keys.

    Args:
        output:      Raw model output string.
        schema_keys: List of required top-level keys. None = just check parseable.

    The grader strips markdown fences (```json ... ```) before parsing.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", output).replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "passed": False,
            "score": 0.0,
            "detail": f"json_valid: FAIL — not parseable JSON: {e}",
        }

    if schema_keys:
        # Handle both dict (object schema) and list (array of objects)
        if isinstance(parsed, list):
            if not parsed:
                # Empty array is valid if the model found no issues
                return {
                    "passed": True,
                    "score": 1.0,
                    "detail": "json_valid: PASS — empty array (no findings)",
                }
            # Check first element for required keys
            check_obj = parsed[0] if isinstance(parsed[0], dict) else {}
        elif isinstance(parsed, dict):
            check_obj = parsed
        else:
            return {
                "passed": False,
                "score": 0.0,
                "detail": f"json_valid: FAIL — unexpected JSON type: {type(parsed).__name__}",
            }

        missing = [k for k in schema_keys if k not in check_obj]
        if missing:
            return {
                "passed": False,
                "score": (len(schema_keys) - len(missing)) / len(schema_keys),
                "detail": f"json_valid: FAIL — missing keys: {missing}",
            }

    return {
        "passed": True,
        "score": 1.0,
        "detail": "json_valid: PASS — valid JSON with all required keys",
    }


# ── keyword_hit ───────────────────────────────────────────────────────────────

def keyword_hit(output: str, keywords: list[str], require_all: bool = True) -> dict:
    """
    Pass if the output contains all (or any) of the required keywords.

    Args:
        output:      Raw model output string.
        keywords:    List of strings that must appear (case-insensitive).
        require_all: If True, ALL keywords must be present. If False, ANY one suffices.
    """
    output_lower = output.lower()
    hits = [kw for kw in keywords if kw.lower() in output_lower]
    misses = [kw for kw in keywords if kw.lower() not in output_lower]

    if require_all:
        passed = len(misses) == 0
    else:
        passed = len(hits) > 0

    score = len(hits) / len(keywords) if keywords else 1.0

    return {
        "passed": passed,
        "score": score,
        "detail": (
            f"keyword_hit: {'PASS' if passed else 'FAIL'} | "
            f"found={hits} | missing={misses}"
        ),
    }


# ── groundedness ──────────────────────────────────────────────────────────────

def groundedness(output: str, context_chunks: list[str], min_overlap_words: int = 3) -> dict:
    """
    Estimate whether the model's output is grounded in the retrieved context.

    Strategy: for each sentence in the output, check if it shares at least
    `min_overlap_words` words with any context chunk. Sentences that are
    grounded count toward the score.

    Also immediately passes if the output contains the NOT IN CONTEXT refusal
    (which is the correct grounded behaviour when evidence is absent).

    Args:
        output:            Model output string.
        context_chunks:    List of retrieved text chunks.
        min_overlap_words: Minimum shared word count to count as grounded.

    Returns:
        passed: True if >= 60% of sentences are grounded OR refusal detected.
        score:  Fraction of sentences that are grounded.
    """
    NOT_IN_CONTEXT_MARKER = "NOT IN CONTEXT"

    if NOT_IN_CONTEXT_MARKER in output.upper():
        return {
            "passed": True,
            "score": 1.0,
            "detail": "groundedness: PASS — model correctly issued NOT IN CONTEXT refusal",
        }

    if not context_chunks:
        return {
            "passed": False,
            "score": 0.0,
            "detail": "groundedness: FAIL — no context chunks provided for grounding check",
        }

    # Tokenise context into a flat word set for cheap overlap check
    ctx_words = set()
    for chunk in context_chunks:
        ctx_words.update(re.findall(r"\b\w+\b", chunk.lower()))

    # Split output into sentences (rough split on . ! ?)
    sentences = [s.strip() for s in re.split(r"[.!?]", output) if s.strip()]
    if not sentences:
        return {"passed": False, "score": 0.0, "detail": "groundedness: FAIL — empty output"}

    grounded = 0
    for sentence in sentences:
        sent_words = set(re.findall(r"\b\w+\b", sentence.lower()))
        # Ignore very short sentences (conjunctions, articles)
        if len(sent_words) < 4:
            grounded += 1  # give benefit of the doubt
            continue
        overlap = sent_words & ctx_words
        if len(overlap) >= min_overlap_words:
            grounded += 1

    score = grounded / len(sentences)
    passed = score >= 0.60

    return {
        "passed": passed,
        "score": round(score, 3),
        "detail": (
            f"groundedness: {'PASS' if passed else 'FAIL'} | "
            f"{grounded}/{len(sentences)} sentences grounded (threshold 60%)"
        ),
    }


# ── not_in_context ────────────────────────────────────────────────────────────

def not_in_context(output: str) -> dict:
    """
    Inverse grader: passes when the model correctly refuses to answer.
    Used in eval cases where the expected answer is the refusal itself.
    """
    refused = "NOT IN CONTEXT" in output.upper()
    return {
        "passed": refused,
        "score": 1.0 if refused else 0.0,
        "detail": f"not_in_context: {'PASS' if refused else 'FAIL — model hallucinated instead of refusing'}",
    }


# ── Registry ──────────────────────────────────────────────────────────────────

GRADER_REGISTRY: dict[str, callable] = {
    "exact_match": exact_match,
    "json_valid": json_valid,
    "keyword_hit": keyword_hit,
    "groundedness": groundedness,
    "not_in_context": not_in_context,
}


def run_grader(name: str, output: str, **kwargs) -> dict:
    """
    Dispatch to the named grader.

    Args:
        name:    Grader name from GRADER_REGISTRY.
        output:  Model output string.
        **kwargs: Grader-specific arguments (expected, schema_keys, keywords, etc.)

    Raises:
        KeyError: If grader name is not registered.
    """
    if name not in GRADER_REGISTRY:
        available = ", ".join(GRADER_REGISTRY.keys())
        raise KeyError(f"Unknown grader '{name}'. Available: {available}")
    return GRADER_REGISTRY[name](output, **kwargs)
