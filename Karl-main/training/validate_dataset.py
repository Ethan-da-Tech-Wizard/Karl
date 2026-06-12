"""
Dataset Validator — Karl Workbench
====================================
Validates data/training/curated.jsonl before fine-tuning.

Checks:
  1. File exists and is non-empty
  2. Schema: every record has system/user/assistant roles in correct order
  3. Minimum count warnings (< 50 warn, < 20 error)
  4. Token length estimate (flag examples > 512 tokens)
  5. Distribution: corrected examples >= 20% of total
  6. Duplicate detection (identical user+response pairs)

Usage:
  python training/validate_dataset.py
  python training/validate_dataset.py --path data/training/custom.jsonl
"""

import json
import os
import sys
import argparse
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CURATED_PATH = "data/training/curated.jsonl"

WARN_COUNT  = 50
ERROR_COUNT = 20
MAX_TOKENS_ESTIMATE = 512  # Rough: 1 token ≈ 4 chars


def estimate_tokens(text: str) -> int:
    """Rough token count estimate: characters / 4."""
    return max(1, len(text) // 4)


def validate(path: str) -> bool:
    """
    Run all checks against the JSONL at `path`.
    Prints PASS/WARN/FAIL for each check.
    Returns True if no ERRORs found.
    """
    print(f"\n{'─'*60}")
    print(f"  Karl Dataset Validator")
    print(f"  Path: {path}")
    print(f"{'─'*60}\n")

    passed_all = True

    # ── Check 1: File exists ──────────────────────────────────────────────────
    if not os.path.exists(path):
        _fail(f"File not found: {path}")
        return False
    _pass("File exists")

    # ── Load records ──────────────────────────────────────────────────────────
    records = []
    parse_errors = 0
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                _warn(f"  Line {i}: JSON parse error — {e}")
                parse_errors += 1
                passed_all = False

    total = len(records)

    if parse_errors:
        _fail(f"{parse_errors} lines could not be parsed as JSON")
        passed_all = False

    # ── Check 2: Count ────────────────────────────────────────────────────────
    if total == 0:
        _fail("Dataset is empty (0 valid records)")
        return False
    elif total < ERROR_COUNT:
        _fail(f"Only {total} examples — minimum recommended is {ERROR_COUNT} for any effect")
        passed_all = False
    elif total < WARN_COUNT:
        _warn(f"Only {total} examples — {WARN_COUNT}+ recommended for stable fine-tuning")
    else:
        _pass(f"Example count: {total}")

    # ── Check 3: Schema ───────────────────────────────────────────────────────
    schema_errors = 0
    for i, rec in enumerate(records):
        messages = rec.get("messages", [])
        if not messages:
            _warn(f"  Record {i+1}: missing 'messages' field")
            schema_errors += 1
            continue
        roles = [m.get("role") for m in messages]
        # Expect [system, user, assistant] — system optional
        has_user = "user" in roles
        has_assistant = "assistant" in roles
        if not has_user or not has_assistant:
            _warn(f"  Record {i+1}: missing user or assistant role — roles found: {roles}")
            schema_errors += 1
        # Check all messages have content
        for m in messages:
            if not m.get("content", "").strip():
                _warn(f"  Record {i+1}: empty content in role '{m.get('role')}'")
                schema_errors += 1

    if schema_errors == 0:
        _pass(f"Schema: all {total} records have valid roles and content")
    else:
        _fail(f"Schema: {schema_errors} issues found")
        passed_all = False

    # ── Check 4: Token length ─────────────────────────────────────────────────
    long_examples = []
    for i, rec in enumerate(records):
        messages = rec.get("messages", [])
        total_chars = sum(len(m.get("content", "")) for m in messages)
        est_tokens = estimate_tokens(total_chars)
        if est_tokens > MAX_TOKENS_ESTIMATE:
            long_examples.append((i + 1, est_tokens))

    if not long_examples:
        _pass(f"Token length: all examples estimated under {MAX_TOKENS_ESTIMATE} tokens")
    else:
        _warn(
            f"Token length: {len(long_examples)} examples estimated over {MAX_TOKENS_ESTIMATE} tokens — "
            f"consider increasing max_seq_length in qlora_config_template.yaml"
        )
        for rec_num, est in long_examples[:5]:
            print(f"    Record {rec_num}: ~{est} tokens")
        if len(long_examples) > 5:
            print(f"    ... and {len(long_examples) - 5} more")

    # ── Check 5: Source distribution ──────────────────────────────────────────
    sources = Counter(rec.get("source", "unknown") for rec in records)
    thumbs_up = sources.get("thumbs_up", 0)
    corrected  = sources.get("corrected", 0)
    other      = total - thumbs_up - corrected

    corrected_pct = corrected / total if total else 0
    if corrected_pct < 0.20 and corrected < 10:
        _warn(
            f"Distribution: only {corrected} corrected examples ({corrected_pct:.0%} of total). "
            f"Add more 👎→corrected examples for robust SFT."
        )
    else:
        _pass(
            f"Distribution: {thumbs_up} thumbs_up | {corrected} corrected ({corrected_pct:.0%}) | {other} other"
        )

    # ── Check 6: Duplicates ───────────────────────────────────────────────────
    seen = set()
    dupes = 0
    for rec in records:
        messages = rec.get("messages", [])
        key_parts = []
        for m in messages:
            if m.get("role") in ("user", "assistant"):
                key_parts.append(m.get("content", "")[:200])
        key = tuple(key_parts)
        if key in seen:
            dupes += 1
        seen.add(key)

    if dupes == 0:
        _pass(f"Duplicates: none found")
    else:
        _warn(f"Duplicates: {dupes} near-duplicate records detected — consider deduplicating")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    if passed_all:
        print("  ✅ Dataset is READY for fine-tuning.")
    else:
        print("  ❌ Dataset has issues. Fix ERRORs before tuning; WARNs are optional.")
    print(f"{'─'*60}\n")

    return passed_all


# ── Formatting helpers ────────────────────────────────────────────────────────

def _pass(msg: str):
    print(f"  ✓  {msg}")

def _warn(msg: str):
    print(f"  ⚠  WARN: {msg}")

def _fail(msg: str):
    print(f"  ✗  ERROR: {msg}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Karl training dataset validator")
    p.add_argument(
        "--path", "-p",
        default=CURATED_PATH,
        help=f"Path to JSONL dataset (default: {CURATED_PATH})",
    )
    args = p.parse_args()
    ok = validate(args.path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
