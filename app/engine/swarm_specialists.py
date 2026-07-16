"""
Swarm Specialists — adaptive, LLM-free static-analysis reviewers.

The orchestrator classifies each task by what it *touches* (classify_task)
and only spins up the specialists that are relevant — a task editing a CSS
file never pays for a security audit; a task touching auth/subprocess/SQL
always does. All reviewers here are pure static analysis (regex + ast): no
model call, instant, deterministic, and safe to run on every candidate.

SecurityAuditorAgent findings are treated as gating — the orchestrator folds
a high-risk verdict into the layer's failure trace so the existing
self-correction retry loop kicks in automatically, the same way a failed test
or a syntax error does. PerformanceAuditorAgent and CriticAgent are advisory:
surfaced to the UI/telemetry but never block a run on their own.
"""

from __future__ import annotations

import ast
import re
from typing import Any


# ── Task classification ─────────────────────────────────────────────────────

_SECURITY_TERMS = re.compile(
    r"\b(auth|password|secret|token|crypto|encrypt|decrypt|sql|subprocess|"
    r"eval|exec|pickle|shell|jwt|session|login|permission|credential|"
    r"api[_ ]?key|admin|sanitiz|escape|injection)\b",
    re.IGNORECASE,
)
_PERFORMANCE_TERMS = re.compile(
    r"\b(loop|cache|caching|performance|optimi[sz]e|latency|throughput|"
    r"benchmark|slow|concurren|thread|async|batch|bottleneck)\b",
    re.IGNORECASE,
)


def classify_task(task: dict[str, Any]) -> list[str]:
    """Return specialist tags relevant to *task* based on filepath + instructions."""
    text = f"{task.get('filepath', '')} {task.get('instructions', '')}"
    tags = []
    if _SECURITY_TERMS.search(text):
        tags.append("security")
    if _PERFORMANCE_TERMS.search(text):
        tags.append("performance")
    return tags


# ── Security auditor ─────────────────────────────────────────────────────────

_DANGEROUS_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\beval\s*\("), "Use of eval() on potentially untrusted input", 0.6),
    (re.compile(r"\bexec\s*\("), "Use of exec() on potentially untrusted input", 0.6),
    (re.compile(r"\bos\.system\s*\("), "os.system() call — prefer subprocess with an argv list", 0.4),
    (re.compile(r"subprocess\.[a-zA-Z_]+\([^)]*shell\s*=\s*True"), "subprocess call with shell=True", 0.5),
    (re.compile(r"\bpickle\.loads?\s*\("), "pickle deserialization of potentially untrusted data", 0.5),
    (re.compile(r"yaml\.load\s*\((?!.*Loader=)"), "yaml.load() without an explicit safe Loader", 0.4),
    (re.compile(r"f[\"']\s*SELECT\b.*\{", re.IGNORECASE), "f-string SQL query — likely SQL injection risk", 0.7),
    (re.compile(r"[\"']SELECT\b.*[\"']\s*\+"), "String-concatenated SQL query — likely SQL injection risk", 0.7),
    (re.compile(r"\bhashlib\.(md5|sha1)\s*\(.*password", re.IGNORECASE), "Weak hash (md5/sha1) used near a password", 0.5),
    (re.compile(r"(password|secret|api_key|token)\s*=\s*[\"'][^\"']{4,}[\"']", re.IGNORECASE), "Hardcoded credential-looking literal", 0.6),
]


class SecurityAuditorAgent:
    """Regex-based scan for common insecure patterns. LLM-free, instant."""

    def review(self, filepath: str, content: str) -> dict[str, Any]:
        concerns = []
        risk = 0.0
        for pattern, message, weight in _DANGEROUS_PATTERNS:
            if pattern.search(content):
                concerns.append(message)
                risk = max(risk, weight)
        verdict = "revise" if risk >= 0.5 else "approve"
        return {
            "specialist": "security",
            "filepath": filepath,
            "concerns": concerns,
            "risk_score": round(risk, 2),
            "verdict": verdict,
        }


# ── Performance auditor ──────────────────────────────────────────────────────

class PerformanceAuditorAgent:
    """AST-based scan for common performance smells. Advisory only."""

    def review(self, filepath: str, content: str) -> dict[str, Any]:
        concerns: list[str] = []
        if filepath.endswith(".py"):
            try:
                tree = ast.parse(content)
                concerns.extend(self._scan(tree))
            except SyntaxError:
                pass
        risk = min(1.0, 0.2 * len(concerns))
        return {
            "specialist": "performance",
            "filepath": filepath,
            "concerns": concerns,
            "risk_score": round(risk, 2),
            "verdict": "advisory",
        }

    def _scan(self, tree: ast.AST) -> list[str]:
        concerns = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                nested = [
                    n for n in ast.walk(node)
                    if isinstance(n, (ast.For, ast.While)) and n is not node
                ]
                if nested:
                    concerns.append(
                        f"Nested loop at line {getattr(node, 'lineno', '?')} — likely O(n^2) or worse"
                    )
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                concerns.append(
                    f"String/list accumulation via += at line {getattr(node, 'lineno', '?')} "
                    "— consider list.append()+join() or a comprehension if this runs in a loop"
                )
        return concerns[:8]


# ── Critic / red-team agent ──────────────────────────────────────────────────

class CriticAgent:
    """General code-quality red-team pass: silent failure modes, leftover
    markers, and overlong functions. Advisory only — never blocks a run.
    """

    _MAX_FUNCTION_LINES = 120

    def review(self, filepath: str, content: str) -> dict[str, Any]:
        concerns: list[str] = []
        if "TODO" in content or "FIXME" in content or "XXX" in content:
            concerns.append("Contains TODO/FIXME/XXX markers left in committed code")

        if filepath.endswith(".py"):
            try:
                tree = ast.parse(content)
                concerns.extend(self._scan(tree))
            except SyntaxError:
                concerns.append("Could not parse for deep review (syntax error should already be gating)")

        risk = min(1.0, 0.15 * len(concerns))
        return {
            "specialist": "critic",
            "filepath": filepath,
            "concerns": concerns,
            "risk_score": round(risk, 2),
            "verdict": "revise" if risk >= 0.6 else "approve",
        }

    def _scan(self, tree: ast.AST) -> list[str]:
        concerns = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                body_is_noop = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
                if node.type is None and body_is_noop:
                    concerns.append(
                        f"Bare 'except: pass' at line {getattr(node, 'lineno', '?')} silently swallows all errors"
                    )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                span = getattr(node, "end_lineno", None)
                if span and node.lineno and (span - node.lineno) > self._MAX_FUNCTION_LINES:
                    concerns.append(
                        f"Function '{node.name}' is {span - node.lineno} lines long — consider splitting it"
                    )
        return concerns[:8]
