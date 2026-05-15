"""
Dataset Validator — karl_finetune
===================================
Validates a JSONL training dataset before fine-tuning.

Supported formats:
  - Alpaca: {"instruction": "...", "input": "...", "output": "..."}
  - Minimal: {"instruction": "...", "output": "..."}  (input optional)
  - ShareGPT: {"messages": [{"role": "...", "content": "..."}, ...]}

Checks:
  1. File exists and is non-empty
  2. JSON parseable on every line
  3. Required fields present and non-empty
  4. Minimum example count
  5. Token length estimate (flag long examples)
  6. Exact duplicates
  7. Privacy scan (via privacy_guard)
  8. Output field not empty

Usage:
  python -m karl_finetune.validate_dataset data/train.jsonl
  python -m karl_finetune.validate_dataset data/train.jsonl --format alpaca
"""

import argparse
import json
import sys
from pathlib import Path

from karl_finetune.privacy_guard import scan_dataset, print_scan_report

WARN_COUNT  = 50
ERROR_COUNT = 10
MAX_TOKENS  = 1024   # rough: 1 token ≈ 4 chars


def _estimate_tokens(text) -> int:
    if isinstance(text, int):
        return max(1, text // 4)
    return max(1, len(str(text)) // 4)


def _detect_format(record: dict) -> str:
    if "messages" in record:
        return "sharegpt"
    if "instruction" in record:
        return "alpaca"
    return "unknown"


def _get_text_fields(record: dict, fmt: str) -> dict[str, str]:
    if fmt == "alpaca":
        return {
            "instruction": record.get("instruction", ""),
            "input":       record.get("input", ""),
            "output":      record.get("output", ""),
        }
    if fmt == "sharegpt":
        msgs = record.get("messages", [])
        return {
            f"message_{i}_{m.get('role','?')}": m.get("content", "")
            for i, m in enumerate(msgs)
        }
    return {}


def validate(path: str, expected_format: str = "auto") -> bool:
    bar = "─" * 62
    print(f"\n{bar}")
    print(f"  Karl Dataset Validator")
    print(f"  Path  : {path}")
    print(f"  Format: {expected_format}")
    print(f"{bar}\n")

    ok = True
    fpath = Path(path)

    # ── 1. File exists ────────────────────────────────────────────────────────
    if not fpath.exists():
        print(f"  ✗  ERROR: File not found: {path}")
        return False
    print(f"  ✓  File exists")

    # ── Load records ──────────────────────────────────────────────────────────
    records: list[dict] = []
    parse_errors = 0
    with open(fpath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  ✗  ERROR: Line {i}: invalid JSON — {e}")
                parse_errors += 1
                ok = False

    total = len(records)

    # ── 2. Count ──────────────────────────────────────────────────────────────
    if total == 0:
        print("  ✗  ERROR: Dataset is empty")
        return False
    elif total < ERROR_COUNT:
        print(f"  ✗  ERROR: Only {total} examples — minimum {ERROR_COUNT} needed for any effect")
        ok = False
    elif total < WARN_COUNT:
        print(f"  ⚠  WARN : {total} examples — {WARN_COUNT}+ recommended for stable training")
    else:
        print(f"  ✓  Example count: {total}")

    # ── 3. Format detection & field validation ────────────────────────────────
    schema_errors = 0
    detected_formats: set[str] = set()

    for i, rec in enumerate(records, 1):
        fmt = _detect_format(rec) if expected_format == "auto" else expected_format
        detected_formats.add(fmt)

        if fmt == "alpaca":
            if not rec.get("instruction", "").strip():
                print(f"  ⚠  WARN : Line {i}: empty or missing 'instruction'")
                schema_errors += 1
            if not rec.get("output", "").strip():
                print(f"  ✗  ERROR: Line {i}: empty or missing 'output'")
                schema_errors += 1
                ok = False
        elif fmt == "sharegpt":
            msgs = rec.get("messages", [])
            roles = [m.get("role") for m in msgs]
            if "assistant" not in roles:
                print(f"  ✗  ERROR: Line {i}: no assistant message in messages list")
                schema_errors += 1
                ok = False
            for m in msgs:
                if not m.get("content", "").strip():
                    print(f"  ⚠  WARN : Line {i}: empty content in role '{m.get('role')}'")
                    schema_errors += 1
        else:
            print(f"  ⚠  WARN : Line {i}: unrecognised format — no 'instruction' or 'messages' field")
            schema_errors += 1

    if schema_errors == 0:
        detected_str = "/".join(sorted(detected_formats))
        print(f"  ✓  Schema: all {total} records valid ({detected_str} format)")
    elif ok:
        print(f"  ⚠  WARN : {schema_errors} schema issue(s) found")

    # ── 4. Token length ───────────────────────────────────────────────────────
    long_examples: list[tuple[int, int]] = []
    for i, rec in enumerate(records, 1):
        fmt = _detect_format(rec) if expected_format == "auto" else expected_format
        fields = _get_text_fields(rec, fmt)
        total_chars = sum(len(v) for v in fields.values())
        est = _estimate_tokens(total_chars)
        if est > MAX_TOKENS:
            long_examples.append((i, est))

    if not long_examples:
        print(f"  ✓  Token length: all examples estimated under {MAX_TOKENS} tokens")
    else:
        print(f"  ⚠  WARN : {len(long_examples)} examples estimated over {MAX_TOKENS} tokens")
        for line_num, est in long_examples[:5]:
            print(f"       Line {line_num}: ~{est} tokens")
        if len(long_examples) > 5:
            print(f"       ... and {len(long_examples) - 5} more")

    # ── 5. Duplicates ─────────────────────────────────────────────────────────
    seen: set[str] = set()
    dupes = 0
    for rec in records:
        key = json.dumps(rec, sort_keys=True)
        if key in seen:
            dupes += 1
        seen.add(key)

    if dupes == 0:
        print(f"  ✓  Duplicates: none")
    else:
        print(f"  ⚠  WARN : {dupes} duplicate rows — deduplicate before training")

    # ── 6. Privacy scan ───────────────────────────────────────────────────────
    privacy_results = scan_dataset(path)
    privacy_clean = print_scan_report(privacy_results, total)
    if not privacy_clean:
        ok = False

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{bar}")
    if ok:
        print(f"  ✅  Dataset READY — {total} examples, {dupes} dupes, 0 critical errors")
    else:
        print(f"  ❌  Dataset has errors. Fix before training.")
    print(f"{bar}\n")
    return ok


def main():
    p = argparse.ArgumentParser(description="Karl training dataset validator")
    p.add_argument("path", help="Path to JSONL dataset file")
    p.add_argument("--format", default="auto",
                   choices=["auto", "alpaca", "sharegpt"],
                   help="Expected dataset format (default: auto-detect)")
    args = p.parse_args()
    ok = validate(args.path, args.format)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
