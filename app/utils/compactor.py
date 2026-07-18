"""Trace compaction for model-facing "Machine Speak" datasets.

The compact format is intentionally denser than the canonical TraceLogger JSONL
schema. It preserves trace identity and training-critical fields, shortens
standard keys, strips repeated prompt boilerplate, and represents code blocks as
unified diffs so repeated coder iterations are cheaper to store and replay.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from typing import Any


KEY_MAP = {
    "id": "i",
    "session_id": "sid",
    "timestamp": "ts",
    "timing": "tm",
    "total_seconds": "tt",
    "prefill_seconds": "ps",
    "generation_seconds": "gs",
    "prefill_tps": "pt",
    "generation_tps": "gt",
    "total_tps": "tp",
    "prompt_tokens": "pk",
    "generation_tokens": "gk",
    "gpu_temp_c": "gc",
    "throttle_reasons": "tr",
    "cooling_duration_sec": "cd",
    "model": "m",
    "adapter": "ad",
    "workflow": "w",
    "template": "te",
    "hyperparams": "hp",
    "system_prompt": "sp",
    "compiled_prompt": "p",
    "thinking": "tk",
    "response": "r",
    "raw_output": "ro",
    "rag_chunks": "rg",
    "feedback": "fb",
    "corrected_response": "cr",
    "warning": "wa",
}
REVERSE_KEY_MAP = {v: k for k, v in KEY_MAP.items()}

TEXT_KEYS = {"compiled_prompt", "system_prompt", "thinking", "response", "raw_output", "corrected_response"}

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "if", "in", "into", "is", "it", "its", "of", "on",
    "or", "that", "the", "their", "then", "there", "this", "to", "was",
    "were", "with", "you", "your",
}

BOILERPLATE_PATTERNS = [
    re.compile(r"(?is)<\|begin_of_text\|>|<\|end_of_text\|>|<\|eot_id\|>"),
    re.compile(r"(?is)<think>\s*|\s*</think>"),
    re.compile(r"(?is)you are karl,?.*?(?=\n\n|\nuser:|\nassistant:|$)"),
    re.compile(r"(?is)you are a helpful assistant\.?"),
    re.compile(r"(?is)system:\s*(?:you are .*?)(?=\n(?:user|assistant):|$)"),
    re.compile(r"(?is)###\s*system\s*.*?(?=###\s*(?:user|assistant)|$)"),
]

CODE_FENCE_RE = re.compile(r"```([A-Za-z0-9_+.\-#]*)\n(.*?)```", re.DOTALL)


def compact_trace_for_ai(trace: dict) -> str:
    """Return a dense JSON string for a TraceLogger entry."""
    compacted = {
        "$": "karl.trace.compact.v1",
        "d": _compact_value(trace),
    }
    return json.dumps(compacted, ensure_ascii=False, separators=(",", ":"))


def decompact_trace(compacted: str) -> dict:
    """Expand a compact trace string back into the canonical key names.

    Text fields are normalized, not byte-for-byte originals: boilerplate and
    stop words stripped during compaction are intentionally unrecoverable.
    """
    data = json.loads(compacted)
    if isinstance(data, dict) and data.get("$") == "karl.trace.compact.v1":
        expanded = _decompact_value(data.get("d", {}))
    else:
        expanded = _decompact_value(data)
    return expanded if isinstance(expanded, dict) else {}


def _compact_value(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        transitions = _compact_transition_dict(value)
        if transitions is not None:
            return transitions
        out: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            short_key = KEY_MAP.get(raw_key, raw_key)
            out[short_key] = _compact_value(raw_value, raw_key)
        return out
    if isinstance(value, list):
        return [_compact_value(item, key) for item in value]
    if isinstance(value, str):
        if key in TEXT_KEYS:
            return _compact_text(value)
        return value
    return value


def _decompact_value(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        if "$parts" in value:
            return _decompact_parts(value["$parts"])
        if "$diff" in value:
            return _new_text_from_unified_diff(value.get("$diff", []))
        if "$tr" in value:
            return _decompact_transition_array(value)
        out: dict[str, Any] = {}
        for short_key, raw_value in value.items():
            long_key = REVERSE_KEY_MAP.get(short_key, short_key)
            out[long_key] = _decompact_value(raw_value, long_key)
        return out
    if isinstance(value, list):
        return [_decompact_value(item, key) for item in value]
    return value


def _compact_text(text: str) -> Any:
    cleaned = _strip_boilerplate(text)
    matches = list(CODE_FENCE_RE.finditer(cleaned))
    if not matches:
        return _remove_stop_words(cleaned)

    parts: list[Any] = []
    cursor = 0
    previous_code = ""
    for index, match in enumerate(matches):
        prefix = cleaned[cursor:match.start()]
        if prefix.strip():
            parts.append(_remove_stop_words(prefix))
        lang = (match.group(1) or "text").strip()
        code = match.group(2)
        diff = _unified_diff(previous_code, code, fromfile=f"code_{index - 1}", tofile=f"code_{index}")
        parts.append({
            "$diff": diff,
            "l": lang,
            "h": hashlib.sha256(code.encode("utf-8")).hexdigest()[:12],
        })
        previous_code = code
        cursor = match.end()

    suffix = cleaned[cursor:]
    if suffix.strip():
        parts.append(_remove_stop_words(suffix))
    return {"$parts": parts}


def _strip_boilerplate(text: str) -> str:
    out = text
    for pattern in BOILERPLATE_PATTERNS:
        out = pattern.sub(" ", out)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _remove_stop_words(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        word = match.group(0)
        return "" if word.lower() in STOP_WORDS else word

    out = re.sub(r"\b[A-Za-z]+\b", repl, text)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" *\n *", "\n", out)
    return out.strip()


def _unified_diff(old: str, new: str, fromfile: str = "prev", tofile: str = "next") -> list[str]:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    return list(difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile, lineterm=""))


def _new_text_from_unified_diff(diff_lines: list[str]) -> str:
    new_lines: list[str] = []
    for line in diff_lines:
        if not line or line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith("+"):
            new_lines.append(line[1:])
        elif line.startswith(" "):
            new_lines.append(line[1:])
    return "\n".join(new_lines)


def _decompact_parts(parts: list[Any]) -> str:
    restored: list[str] = []
    for part in parts:
        if isinstance(part, str):
            restored.append(part)
        elif isinstance(part, dict) and "$diff" in part:
            lang = part.get("l", "")
            code = _new_text_from_unified_diff(part.get("$diff", []))
            restored.append(f"```{lang}\n{code}\n```")
    return "\n".join(chunk for chunk in restored if chunk)


def _compact_transition_dict(value: dict) -> dict | None:
    steps = value.get("transitions") or value.get("iterations") or value.get("steps")
    if not isinstance(steps, list) or not steps:
        return None

    dense: list[list[Any]] = []
    previous = ""
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        state = step.get("state") or step.get("status") or step.get("phase") or ""
        output = step.get("output") or step.get("response") or step.get("content") or ""
        if isinstance(output, str) and "```" in output:
            compacted = _compact_text(output)
        elif isinstance(output, str):
            compacted = _unified_diff(previous, output, fromfile=f"step_{index - 1}", tofile=f"step_{index}")
            previous = output
        else:
            compacted = output
        dense.append([index, state, compacted])
    return {"$tr": dense}


def _decompact_transition_array(value: dict) -> dict:
    steps = []
    for row in value.get("$tr", []):
        if not isinstance(row, list) or len(row) < 3:
            continue
        output = row[2]
        if isinstance(output, list):
            output = _new_text_from_unified_diff(output)
        else:
            output = _decompact_value(output)
        steps.append({"index": row[0], "state": row[1], "output": output})
    return {"transitions": steps}
