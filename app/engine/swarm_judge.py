"""
SwarmJudge — heuristic multi-signal scoring for "Multiverse" candidate selection.

When SwarmOrchestratorThread is configured with candidates_per_task > 1, the
Coder agent generates several independent solution attempts for the same task
(different temperature/persona each time — see CoderAgent.PERSONAS). Rather
than trusting whichever one finished last, every candidate is scored on four
independent, LLM-free signals and the highest-scoring one is written to disk:

  1. syntax_ok          — does it even parse? (hard gate, dominates the score)
  2. lint_violations     — pyflakes violation count (fewer is better)
  3. diff_size            — how much of the original file changed (smaller,
                            more targeted diffs score higher — a crude proxy
                            for "didn't rewrite the world to fix one bug")
  4. signature_alignment  — fraction of the codebase's *known* function/class
                            names that the candidate actually calls, vs. names
                            it invents that don't exist anywhere in the
                            workspace (a cheap hallucinated-API detector)

All signals are computed locally and instantly — no model call, no test
execution — so scoring N candidates costs nothing but a little CPU, and the
*official* verification test command still only runs once, against the winner.
"""

from __future__ import annotations

import ast
import difflib
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("karl.swarm_judge")

_WEIGHT_SYNTAX_FAIL = -1000.0
_WEIGHT_LINT = -4.0
_WEIGHT_DIFF = -0.02
_WEIGHT_SIGNATURE = 40.0
_WEIGHT_LENGTH_FLOOR = -50.0  # penalize suspiciously tiny/empty output


def _check_syntax(filepath: str, content: str) -> tuple[bool, str]:
    if filepath.endswith(".py"):
        try:
            ast.parse(content)
            return True, ""
        except SyntaxError as exc:
            return False, f"SyntaxError: {exc.msg} at line {exc.lineno}"
    if filepath.endswith(".json"):
        try:
            json.loads(content)
            return True, ""
        except json.JSONDecodeError as exc:
            return False, f"JSONDecodeError: {exc.msg} at line {exc.lineno}"
    return True, ""


def _lint_violation_count(filepath: str, content: str) -> int:
    if not filepath.endswith(".py") or not content.strip():
        return 0
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
            tf.write(content)
            tmp_path = tf.name
        result = subprocess.run(
            ["python3", "-m", "pyflakes", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        out = (result.stdout + result.stderr).strip()
        return 0 if not out else len(out.splitlines())
    except Exception as exc:
        logger.debug("Judge lint check failed (non-fatal): %s", exc)
        return 0
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def _diff_size(original: str, candidate: str) -> int:
    if not original:
        return 0
    a = original.splitlines()
    b = candidate.splitlines()
    diff = list(difflib.unified_diff(a, b, lineterm=""))
    return sum(1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))


def _signature_alignment(content: str, known_names: set[str]) -> float:
    """Fraction of "plausible call sites" in *content* that match a name the
    codebase actually defines. Returns 1.0 (neutral/best) when there's nothing
    to check against (empty index, or no call-like tokens found) so a
    workspace with no memory index doesn't unfairly tank every candidate.
    """
    if not known_names:
        return 1.0
    called = set(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content))
    # Ignore Python builtins/keywords-as-calls and very short/common names —
    # they're not meaningful signals either way.
    called = {c for c in called if len(c) > 3}
    if not called:
        return 1.0
    matched = called & known_names
    return len(matched) / len(called)


def score_candidate(
    filepath: str,
    content: str,
    *,
    original_content: str = "",
    known_names: set[str] | None = None,
) -> dict[str, Any]:
    """Score a single candidate. Returns a breakdown dict with 'total_score'."""
    syntax_ok, syntax_error = _check_syntax(filepath, content)
    lint_violations = _lint_violation_count(filepath, content) if syntax_ok else 0
    diff_size = _diff_size(original_content, content)
    alignment = _signature_alignment(content, known_names or set())

    total = 0.0
    if not syntax_ok:
        total += _WEIGHT_SYNTAX_FAIL
    total += lint_violations * _WEIGHT_LINT
    total += diff_size * _WEIGHT_DIFF
    total += alignment * _WEIGHT_SIGNATURE
    if len(content.strip()) < 5:
        total += _WEIGHT_LENGTH_FLOOR

    return {
        "filepath": filepath,
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        "lint_violations": lint_violations,
        "diff_size": diff_size,
        "signature_alignment": round(alignment, 3),
        "total_score": round(total, 2),
    }


def select_winner(
    filepath: str,
    candidates: list[str],
    *,
    original_content: str = "",
    known_names: set[str] | None = None,
) -> tuple[int, dict[str, Any], list[dict[str, Any]]]:
    """Score every candidate and return (winner_index, winner_score, all_scores).

    Ties are broken by preferring the earlier candidate (lower temperature /
    more conservative persona — see CoderAgent.PERSONAS ordering).
    """
    if not candidates:
        raise ValueError("select_winner() requires at least one candidate")

    scores = [
        score_candidate(filepath, c, original_content=original_content, known_names=known_names)
        for c in candidates
    ]
    best_index = max(range(len(scores)), key=lambda i: (scores[i]["total_score"], -i))
    return best_index, scores[best_index], scores
