"""
SwarmMemory — persistent cross-run failure/fix learning for the swarm.

Every time a dependency layer fails verification, the failure gets fingerprinted
(exception/error class + normalized message + touched file) and stored alongside
the task that caused it. Every time a layer *succeeds* after one or more prior
failures, the fingerprints that led to it are linked to the instructions that
finally worked. Future tasks recall matching fingerprints before the Coder agent
even starts, so the swarm stops re-making the same mistake on this codebase
across separate runs (and separate app restarts).

Deliberately LLM-free: recall is pure keyword/fingerprint matching over a local
JSON store, so calling it costs zero tokens and adds zero latency-sensitive
model calls (keeps orchestrator call sequencing deterministic for callers that
don't opt into the LLM-heavier features).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any


_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "into", "from", "file",
    "edit", "use", "using", "define", "create", "update", "return", "error",
}

# Matches "TypeError", "SyntaxError: invalid syntax", "AssertionError", etc.
_ERROR_CLASS_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Error|Exception|Warning))\b")


def _keywords(text: str, limit: int = 10) -> list[str]:
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text or "")
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        key = w.lower()
        if key in _STOPWORDS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out[:limit]


def fingerprint_failure(trace: str) -> str:
    """Collapse a raw traceback/error string into a short, stable signature.

    Two failures with the same exception class and a similar first-line
    message fingerprint identically even if line numbers or variable names
    differ, so recall matches "the same class of bug" rather than requiring
    byte-identical tracebacks.
    """
    if not trace:
        return "unknown_error"
    match = _ERROR_CLASS_RE.search(trace)
    err_class = match.group(1) if match else "Error"
    # First non-empty line after the error class mention, truncated + normalized.
    first_line = ""
    for line in trace.splitlines():
        line = line.strip()
        if line and not line.startswith("Traceback"):
            first_line = line
            break
    # Strip anything that looks like a line number, memory address, or path
    # so the fingerprint is stable across runs.
    normalized = re.sub(r"0x[0-9a-fA-F]+", "<addr>", first_line)
    normalized = re.sub(r"\bline \d+\b", "line <n>", normalized)
    normalized = re.sub(r"[\'\"][^\'\"]{0,80}[\'\"]", "<str>", normalized)
    return f"{err_class}:{normalized[:120]}"


class SwarmMemory:
    """Thread-safe, atomically-persisted failure/fix memory for one workspace."""

    def __init__(self, workspace_path: str, db_path: str | None = None):
        self.workspace_path = workspace_path
        if db_path is None:
            # Scope memory per-workspace (by realpath hash) so unrelated
            # codebases -- and unrelated test runs pointed at different temp
            # directories -- never read or pollute each other's failure/fix
            # history through a single shared file.
            ws_hash = hashlib.sha1(os.path.realpath(workspace_path).encode("utf-8")).hexdigest()[:16]
            db_path = f"data/swarm_memory/{ws_hash}.json"
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self._loaded = False

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._loaded:
            return
        try:
            data = json.loads(self.db_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._records = data
        except (OSError, json.JSONDecodeError):
            self._records = []
        self._loaded = True

    def _persist(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.db_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._records[-500:], indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.db_path)

    # ── Writes ───────────────────────────────────────────────────────────────

    def record_failure(self, filepath: str, instructions: str, trace: str) -> str:
        """Store a failure fingerprint. Returns the fingerprint string so the
        caller can later link a successful fix back to it via record_success().
        """
        fp = fingerprint_failure(trace)
        with self._lock:
            self._load()
            self._records.append({
                "kind": "failure",
                "filepath": filepath,
                "fingerprint": fp,
                "keywords": _keywords(f"{filepath} {instructions}"),
                "trace_excerpt": (trace or "")[:400],
                "timestamp": time.time(),
            })
            self._persist()
        return fp

    def record_success(self, filepath: str, instructions: str, fingerprints: list[str]) -> None:
        """Link a successful outcome to the failure fingerprints it resolved,
        so future recall can surface 'here's what fixed this before'.
        """
        if not fingerprints:
            return
        with self._lock:
            self._load()
            self._records.append({
                "kind": "fix",
                "filepath": filepath,
                "resolves": list(dict.fromkeys(fingerprints)),
                "instructions_excerpt": (instructions or "")[:400],
                "keywords": _keywords(f"{filepath} {instructions}"),
                "timestamp": time.time(),
            })
            self._persist()

    # ── Recall ───────────────────────────────────────────────────────────────

    def recall(self, filepath: str, instructions: str, limit: int = 3) -> str:
        """Return a formatted block of past failures (and their fixes, when
        known) relevant to a new task, or "" if nothing matches. Pure local
        keyword overlap — no LLM call.
        """
        with self._lock:
            self._load()
            records = list(self._records)

        terms = set(_keywords(f"{filepath} {instructions}"))
        if not terms:
            return ""

        failures = [r for r in records if r.get("kind") == "failure"]
        fixes_by_fp: dict[str, list[dict]] = {}
        for r in records:
            if r.get("kind") == "fix":
                for fp in r.get("resolves", []):
                    fixes_by_fp.setdefault(fp, []).append(r)

        def _score(rec: dict) -> int:
            return len(terms & set(rec.get("keywords", [])))

        scored = sorted(
            (r for r in failures if _score(r) > 0),
            key=_score,
            reverse=True,
        )[:limit]

        if not scored:
            return ""

        lines = ["Known Past Failure Patterns on this codebase:"]
        for rec in scored:
            fp = rec.get("fingerprint", "unknown")
            lines.append(f"- [{rec.get('filepath', '?')}] {fp}")
            fix = fixes_by_fp.get(fp)
            if fix:
                lines.append(f"  Previously fixed by: {fix[-1].get('instructions_excerpt', '')[:160]}")
        return "\n".join(lines)
