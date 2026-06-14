"""
Dataset Validator — Karl Workbench
====================================
Pre-flight validation for SFT and DPO training datasets before Unsloth loops.

Detected formats
────────────────
  SFT   — keys: instruction, input, output, source, timestamp
  DPO   — keys: prompt, chosen, rejected
  Chat  — keys: messages  (legacy Karl curated.jsonl format)

Checks
──────
  1. File exists and is non-empty
  2. Valid JSON on every line
  3. Format-specific schema (required keys, non-empty fields, DPO diversity)
  4. Token-length envelope vs. model context or --block-size (default 2048)
  5. Structured summary report + exit code 0 (pass) / 1 (fail)

Usage
─────
  python training/validate_dataset.py
  python training/validate_dataset.py --path data/training/dpo_export.jsonl
  python training/validate_dataset.py --path data/training/sft.jsonl --block-size 4096
"""

import json
import os
import sys
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CURATED_PATH = "data/training/curated.jsonl"
DEFAULT_BLOCK_SIZE = 2048
CHARS_PER_TOKEN = 4  # Heuristic fallback: 1 token ≈ 4 characters


# ── Token estimation ──────────────────────────────────────────────────────────

def _build_token_estimator(block_size_override: int | None) -> tuple:
    """
    Returns (estimate_fn, block_size, using_model_tokenizer).

    Prefers the live ModelLoader tokenizer so the length check uses real BPE
    boundaries.  Falls back to the 4-chars-per-token heuristic when no model
    is loaded (or llama_cpp is unavailable), so the script always runs.
    """
    block_size = block_size_override or DEFAULT_BLOCK_SIZE
    try:
        from app.engine.model_loader import ModelLoader
        if ModelLoader.is_loaded():
            llm = ModelLoader.get_instance()
            if block_size_override is None:
                block_size = ModelLoader.context_limit() or DEFAULT_BLOCK_SIZE

            def _model_estimate(text: str) -> int:
                try:
                    return len(llm.tokenize(text.encode("utf-8", errors="replace")))
                except Exception:
                    return max(1, len(text) // CHARS_PER_TOKEN)

            return _model_estimate, block_size, True
    except Exception:
        pass

    def _heuristic_estimate(text: str) -> int:
        return max(1, len(text) // CHARS_PER_TOKEN)

    return _heuristic_estimate, block_size, False


# ── Format detection ──────────────────────────────────────────────────────────

def _detect_format(rec: dict) -> str:
    """Return 'dpo', 'sft', 'chat', or 'unknown'."""
    if "prompt" in rec and ("chosen" in rec or "rejected" in rec):
        return "dpo"
    if "instruction" in rec or "output" in rec:
        return "sft"
    if "messages" in rec:
        return "chat"
    return "unknown"


# ── Text extraction (for token budget) ───────────────────────────────────────

def _record_text(rec: dict, fmt: str) -> str:
    """Concatenate all natural-language fields so we can estimate total tokens."""
    if fmt == "sft":
        return " ".join(filter(None, [
            str(rec.get("instruction", "")),
            str(rec.get("input", "")),
            str(rec.get("output", "")),
        ]))
    if fmt == "dpo":
        return " ".join(filter(None, [
            str(rec.get("prompt", "")),
            str(rec.get("chosen", "")),
            str(rec.get("rejected", "")),
        ]))
    if fmt == "chat":
        return " ".join(
            str(m.get("content", "")) for m in rec.get("messages", [])
        )
    return json.dumps(rec)


# ── Per-format schema validators ──────────────────────────────────────────────

def _validate_sft(rec: dict, lineno: int) -> tuple[list[str], list[str]]:
    """Returns (schema_errors, empty_field_errors)."""
    schema, empty = [], []
    for key in ("instruction", "input", "output", "source", "timestamp"):
        if key not in rec:
            schema.append(f"line {lineno}: missing key '{key}'")
    if not str(rec.get("instruction", "")).strip():
        empty.append(f"line {lineno}: 'instruction' is empty")
    if not str(rec.get("output", "")).strip():
        empty.append(f"line {lineno}: 'output' is empty")
    return schema, empty


def _validate_dpo(rec: dict, lineno: int) -> tuple[list[str], list[str]]:
    """Returns (schema_errors, empty_field_errors)."""
    schema, empty = [], []
    for key in ("prompt", "chosen", "rejected"):
        if key not in rec:
            schema.append(f"line {lineno}: missing key '{key}'")
    if not str(rec.get("prompt", "")).strip():
        empty.append(f"line {lineno}: 'prompt' is empty")
    chosen = str(rec.get("chosen", "")).strip()
    rejected = str(rec.get("rejected", "")).strip()
    if chosen and rejected and chosen == rejected:
        empty.append(f"line {lineno}: 'chosen' and 'rejected' are identical")
    return schema, empty


def _validate_chat(rec: dict, lineno: int) -> tuple[list[str], list[str]]:
    """Returns (schema_errors, empty_field_errors)."""
    schema, empty = [], []
    messages = rec.get("messages")
    if not isinstance(messages, list) or not messages:
        schema.append(f"line {lineno}: 'messages' is missing or empty")
        return schema, empty
    roles = [m.get("role") for m in messages]
    if "user" not in roles or "assistant" not in roles:
        schema.append(
            f"line {lineno}: messages must include 'user' and 'assistant' roles"
        )
    for m in messages:
        if not str(m.get("content", "")).strip():
            empty.append(
                f"line {lineno}: empty content in role '{m.get('role')}'"
            )
    return schema, empty


# ── Formatting helpers ────────────────────────────────────────────────────────

def _pass(msg: str):
    print(f"  ✓  {msg}")

def _fail(msg: str):
    print(f"  ✗  FAIL: {msg}")

def _info(msg: str):
    print(f"  ·  {msg}")

def _indent(lines: list[str], limit: int = 10):
    for line in lines[:limit]:
        print(f"         {line}")
    if len(lines) > limit:
        print(f"         … and {len(lines) - limit} more")


# ── Main validator ────────────────────────────────────────────────────────────

def validate(path: str, block_size_override: int | None = None) -> bool:
    bar = "─" * 62
    print(f"\n{bar}")
    print(f"  Karl DPO/SFT Dataset Validator")
    print(f"  Path : {path}")
    print(f"{bar}\n")

    # ── 1. File existence ─────────────────────────────────────────────────────
    if not os.path.exists(path):
        _fail(f"File not found: {path}")
        return False
    _pass("File exists")

    # ── Token estimator setup ─────────────────────────────────────────────────
    estimate_tokens, block_size, using_model = _build_token_estimator(
        block_size_override
    )
    tokenizer_label = "model tokenizer" if using_model else f"heuristic (1 tok ≈ {CHARS_PER_TOKEN} chars)"
    _info(f"Token estimator : {tokenizer_label}")
    _info(f"Block size cap  : {block_size} tokens")
    print()

    # ── 2. JSON parse pass ────────────────────────────────────────────────────
    records: list[tuple[int, dict]] = []
    json_errors: list[str] = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append((lineno, json.loads(raw)))
            except json.JSONDecodeError as exc:
                json_errors.append(f"line {lineno}: {exc.msg} (col {exc.colno})")

    total = len(records)

    if json_errors:
        _fail(f"JSON parse errors: {len(json_errors)}")
        _indent(json_errors)
    else:
        _pass(f"JSON: all lines parsed successfully")

    if total == 0:
        _fail("No valid JSON records found — aborting further checks")
        _print_report(total, len(json_errors), 0, 0, 0, 0.0, block_size)
        return False

    # ── 3. Schema + 4. Token-length checks ───────────────────────────────────
    schema_failures: list[str] = []
    empty_failures: list[str] = []
    length_overflows: list[tuple[int, int]] = []   # (lineno, est_tokens)
    format_counts: dict[str, int] = defaultdict(int)
    total_tokens = 0

    for lineno, rec in records:
        fmt = _detect_format(rec)
        format_counts[fmt] += 1

        if fmt == "sft":
            s_errs, e_errs = _validate_sft(rec, lineno)
        elif fmt == "dpo":
            s_errs, e_errs = _validate_dpo(rec, lineno)
        elif fmt == "chat":
            s_errs, e_errs = _validate_chat(rec, lineno)
        else:
            s_errs = [
                f"line {lineno}: unrecognised format "
                f"(top-level keys: {list(rec.keys())[:6]})"
            ]
            e_errs = []

        schema_failures.extend(s_errs)
        empty_failures.extend(e_errs)

        est = estimate_tokens(_record_text(rec, fmt))
        total_tokens += est
        if est > block_size:
            length_overflows.append((lineno, est))

    avg_tokens = total_tokens / total

    # Schema report
    if schema_failures:
        _fail(f"Schema (missing keys / unknown format): {len(schema_failures)} issue(s)")
        _indent(schema_failures)
    else:
        _pass(f"Schema: all {total} records have required keys")

    # Empty-field / DPO diversity report
    if empty_failures:
        _fail(f"Empty or invalid fields: {len(empty_failures)} issue(s)")
        _indent(empty_failures)
    else:
        _pass("Empty/identical fields: none detected")

    # Token-length report
    if length_overflows:
        _fail(
            f"Token length overflow: {len(length_overflows)} record(s) "
            f"exceed {block_size} tokens"
        )
        _indent(
            [f"line {ln}: ~{est} tokens" for ln, est in length_overflows],
            limit=5,
        )
    else:
        _pass(f"Token length: all records estimated under {block_size} tokens")

    # Format breakdown (informational)
    fmt_parts = ", ".join(
        f"{cnt} {fmt}" for fmt, cnt in sorted(format_counts.items())
    )
    _info(f"Format breakdown: {fmt_parts}")

    # ── 5. Summary report ─────────────────────────────────────────────────────
    invalid_count = (
        len(json_errors)
        + len(schema_failures)
        + len(empty_failures)
        + len(length_overflows)
    )
    _print_report(
        total, len(json_errors), len(schema_failures),
        len(empty_failures), len(length_overflows), avg_tokens, block_size,
    )

    return invalid_count == 0


def _print_report(
    total: int,
    json_errors: int,
    schema_failures: int,
    empty_failures: int,
    length_overflows: int,
    avg_tokens: float,
    block_size: int,
):
    bar = "─" * 62
    invalid_total = json_errors + schema_failures + empty_failures + length_overflows
    print(f"\n{bar}")
    print(f"  EVALUATION SUMMARY")
    print(f"{bar}")
    print(f"  Total records evaluated : {total}")
    print(f"  Invalid records total   : {invalid_total}")
    print(f"    JSON parse errors     : {json_errors}")
    print(f"    Schema failures       : {schema_failures}")
    print(f"    Empty / identical     : {empty_failures}")
    print(f"    Length overflows      : {length_overflows}  (>{block_size} tok)")
    print(f"  Average token length    : {avg_tokens:.1f} tokens / example")
    status = "PASS ✅" if invalid_total == 0 else "FAIL ❌"
    print(f"  Status                  : {status}")
    print(f"{bar}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Karl DPO/SFT training dataset pre-flight validator"
    )
    parser.add_argument(
        "--path", "-p",
        default=CURATED_PATH,
        help=f"Path to JSONL dataset (default: {CURATED_PATH})",
    )
    parser.add_argument(
        "--block-size", "-b",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Token block-size cap for length checks "
            f"(default: model context limit or {DEFAULT_BLOCK_SIZE})"
        ),
    )
    args = parser.parse_args()
    ok = validate(args.path, block_size_override=args.block_size)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
