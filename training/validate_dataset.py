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
import shutil
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


# ── Repair helpers ────────────────────────────────────────────────────────────

# Smart-quote and whitespace normalisation table (applied once, globally).
_UNICODE_REPAIR_TABLE = str.maketrans({
    "“": '"',   # left double quotation mark  "
    "”": '"',   # right double quotation mark "
    "‘": "'",   # left single quotation mark  '
    "’": "'",   # right single quotation mark '
    " ": " ",   # non-breaking space
})


def _sanitize_text(s: str) -> str:
    """Replace smart quotes, NBSP, and trailing CR in a single string."""
    return s.translate(_UNICODE_REPAIR_TABLE).rstrip("\r")


def _sanitize_record(rec: dict) -> tuple[dict, bool]:
    """
    Recursively walk all string values and apply _sanitize_text.
    Returns (cleaned_rec, changed) where changed=True if anything was modified.
    """
    changed = False

    def _walk(obj):
        nonlocal changed
        if isinstance(obj, str):
            cleaned = _sanitize_text(obj)
            if cleaned != obj:
                changed = True
            return cleaned
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(item) for item in obj]
        return obj

    return _walk(rec), changed


def _reasoning_guard(text: str) -> str:
    """
    If a <think> block is opened more times than it is closed, append </think>
    at the absolute end of the truncated string so the reasoning tag pair is
    always balanced after truncation.
    """
    if text.count("<think>") > text.count("</think>"):
        return text.rstrip() + "</think>"
    return text


def _truncate_text(text: str, max_chars: int) -> str:
    """Hard character truncation. Caller applies _reasoning_guard afterwards."""
    return text[:max_chars] if len(text) > max_chars else text


_THINK_CLOSE_LEN = len("</think>")  # 8 — maximum chars _reasoning_guard can add


def _truncate_record(rec: dict, fmt: str, char_budget: int) -> dict:
    """
    Truncate natural-language fields so the total character count stays within
    char_budget.  Strategy per format:
      SFT  — truncate output first, then instruction if still over budget.
      DPO  — reserve 1/3 of budget for prompt, split the rest between
              chosen/rejected evenly.
      Chat — walk assistant turns backwards and trim content until under budget.
    The reasoning guard is applied after every individual field truncation.

    Budget accounting is exact:
      • Separator count is derived from which fields are actually non-empty
        (matching filter(None, ...) in _record_text, which skips empty strings).
      • _THINK_CLOSE_LEN chars are reserved per field so the reasoning guard
        cannot push the total over budget after it appends </think>.
    """
    rec = dict(rec)

    if fmt == "sft":
        instruction = str(rec.get("instruction", ""))
        inp = str(rec.get("input", ""))
        output = str(rec.get("output", ""))

        # Mirror the filter(None, ...) join in _record_text: count only the
        # separating spaces that will actually appear between non-empty fields.
        nonempty_count = sum(bool(x) for x in (instruction, inp, output))
        sep_overhead = max(0, nonempty_count - 1)

        output_budget = max(
            0,
            char_budget - len(instruction) - len(inp) - sep_overhead - _THINK_CLOSE_LEN,
        )
        if len(output) > output_budget:
            rec["output"] = _reasoning_guard(_truncate_text(output, output_budget))

        # If instruction is still too long (rare), trim it with the updated output len.
        updated_output = str(rec.get("output", ""))
        instr_budget = max(
            0,
            char_budget - len(updated_output) - len(inp) - sep_overhead - _THINK_CLOSE_LEN,
        )
        if len(instruction) > instr_budget:
            rec["instruction"] = _reasoning_guard(
                _truncate_text(instruction, instr_budget)
            )

    elif fmt == "dpo":
        prompt = str(rec.get("prompt", ""))
        chosen = str(rec.get("chosen", ""))
        rejected = str(rec.get("rejected", ""))

        # Separator overhead: prompt + chosen + rejected joined → 2 spaces.
        sep_overhead = 2
        prompt_budget = char_budget // 3 - _THINK_CLOSE_LEN
        half = (char_budget - sep_overhead - prompt_budget) // 2
        chosen_budget = half - _THINK_CLOSE_LEN
        rejected_budget = char_budget - sep_overhead - prompt_budget - half - _THINK_CLOSE_LEN

        if len(chosen) > chosen_budget:
            rec["chosen"] = _reasoning_guard(_truncate_text(chosen, chosen_budget))
        if len(rejected) > rejected_budget:
            rec["rejected"] = _reasoning_guard(_truncate_text(rejected, rejected_budget))
        if len(prompt) > prompt_budget:
            rec["prompt"] = _reasoning_guard(_truncate_text(prompt, prompt_budget))

    elif fmt == "chat":
        messages = [dict(m) for m in rec.get("messages", [])]
        for i in range(len(messages) - 1, -1, -1):
            total = sum(len(str(m.get("content", ""))) for m in messages)
            if total <= char_budget:
                break
            if messages[i].get("role") != "assistant":
                continue
            content = str(messages[i].get("content", ""))
            excess = total - char_budget + _THINK_CLOSE_LEN
            new_len = max(0, len(content) - excess)
            messages[i]["content"] = _reasoning_guard(_truncate_text(content, new_len))
        rec["messages"] = messages

    return rec


def _repair_schema(rec: dict, fmt: str) -> tuple[dict, bool]:
    """
    Attempt format-specific schema repair.
    Returns (repaired_rec, should_drop).
    should_drop=True means the record is unfixable and must be omitted.
    """
    if fmt == "sft":
        if not str(rec.get("instruction", "")).strip():
            return rec, True
        if not str(rec.get("output", "")).strip():
            return rec, True
        repaired = dict(rec)
        repaired.setdefault("input", "")
        repaired.setdefault("source", "")
        repaired.setdefault("timestamp", "")
        return repaired, False

    if fmt == "dpo":
        prompt = str(rec.get("prompt", "")).strip()
        chosen = str(rec.get("chosen", "")).strip()
        rejected = str(rec.get("rejected", "")).strip()
        if not prompt or not chosen or not rejected:
            return rec, True
        if chosen == rejected:
            return rec, True
        return rec, False

    if fmt == "chat":
        messages = rec.get("messages")
        if not isinstance(messages, list) or not messages:
            return rec, True
        clean_msgs = [m for m in messages if str(m.get("content", "")).strip()]
        roles = {m.get("role") for m in clean_msgs}
        if "user" not in roles or "assistant" not in roles:
            return rec, True
        repaired = dict(rec)
        repaired["messages"] = clean_msgs
        return repaired, False

    # Unknown format — not repairable.
    return rec, True


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


# ── Active repair pipeline ────────────────────────────────────────────────────

def repair(path: str, block_size_override: int | None = None) -> None:
    """
    Sanitize, schema-repair, and truncate every record in *path* in-place.
    A .bak backup is written before any modifications are made.
    """
    bar = "─" * 62
    print(f"\n{bar}")
    print(f"  Karl Dataset Repair Mode")
    print(f"  Path : {path}")
    print(f"{bar}\n")

    if not os.path.exists(path):
        _fail(f"File not found: {path}")
        return

    # ── Backup ────────────────────────────────────────────────────────────────
    bak_path = path + ".bak"
    shutil.copy2(path, bak_path)
    _pass(f"Backup created  : {bak_path}")

    # ── Token budget ──────────────────────────────────────────────────────────
    estimate_tokens, block_size, using_model = _build_token_estimator(block_size_override)
    # Character budget is always heuristic-based for truncation: 1 tok ≈ 4 chars.
    # This guarantees the heuristic estimator sees ≤ block_size tokens after repair,
    # and is a safe under-approximation for real tokenizers.
    char_budget = block_size * CHARS_PER_TOKEN
    tokenizer_label = "model tokenizer" if using_model else f"heuristic (1 tok ≈ {CHARS_PER_TOKEN} chars)"
    _info(f"Token estimator : {tokenizer_label}")
    _info(f"Block size cap  : {block_size} tokens  ({char_budget} chars)")
    print()

    # ── Parse ─────────────────────────────────────────────────────────────────
    parsed: list[tuple[int, dict]] = []
    json_dropped = 0
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                parsed.append((lineno, json.loads(raw)))
            except json.JSONDecodeError:
                json_dropped += 1
                _info(f"  Dropped line {lineno}: unparseable JSON")

    # ── Process each record ───────────────────────────────────────────────────
    output_records: list[dict] = []
    n_sanitized = 0
    n_schema_dropped = 0
    n_truncated = 0

    for lineno, rec in parsed:
        # Step 1 — Unicode normalization
        rec, changed = _sanitize_record(rec)
        if changed:
            n_sanitized += 1

        # Step 2 — Schema repair / drop
        fmt = _detect_format(rec)
        rec, should_drop = _repair_schema(rec, fmt)
        if should_drop:
            n_schema_dropped += 1
            _info(f"  Dropped line {lineno}: unfixable schema (format={fmt})")
            continue

        # Step 3 — Sequence truncation
        est = estimate_tokens(_record_text(rec, fmt))
        if est > block_size:
            rec = _truncate_record(rec, fmt, char_budget)
            n_truncated += 1
            _info(f"  Truncated line {lineno}: was ~{est} tokens → capped at {block_size}")

        output_records.append(rec)

    # ── Write back ────────────────────────────────────────────────────────────
    with open(path, "w", encoding="utf-8") as fh:
        for rec in output_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ── Repair summary ────────────────────────────────────────────────────────
    total_input = len(parsed) + json_dropped
    total_dropped = json_dropped + n_schema_dropped
    print(f"\n{bar}")
    print(f"  REPAIR SUMMARY")
    print(f"{bar}")
    print(f"  Input records           : {total_input}")
    print(f"  Records sanitized       : {n_sanitized}  (unicode / whitespace)")
    print(f"  Records dropped         : {total_dropped}")
    print(f"    Unparseable JSON      : {json_dropped}")
    print(f"    Unfixable schema      : {n_schema_dropped}")
    print(f"  Records truncated       : {n_truncated}  (sequence length)")
    print(f"  Records written         : {len(output_records)}")
    print(f"  Backup path             : {bak_path}")
    print(f"{bar}\n")


# ── Git Hook Installer ───────────────────────────────────────────────────────

def install_git_hook():
    """Programmatically install a Git pre-commit hook that validates datasets."""
    git_dir = ".git"
    if not os.path.isdir(git_dir):
        # Check parent if we're in training/
        if os.path.isdir("../.git"):
            git_dir = "../.git"
        else:
            _fail("Git repository not found. Please run this from the repo root.")
            return False

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    hook_path = os.path.join(hooks_dir, "pre-commit")

    hook_script = """#!/bin/bash

# Karl Training Dataset Pre-commit Validator
# -----------------------------------------
# Blocks commits if staged .jsonl files in data/training/ fail validation.

STAGED_DATASETS=$(git diff --cached --name-only --diff-filter=ACM | grep '^data/training/.*\\.jsonl$')

if [ -n "$STAGED_DATASETS" ]; then
    echo "[GIT PRE-COMMIT HOOK]: Validating staged training datasets..."
    
    # Identify python executable (prefer venv)
    PYTHON_EXE="python"
    if [ -f "venv/bin/python" ]; then
        PYTHON_EXE="venv/bin/python"
    elif [ -f ".venv/bin/python" ]; then
        PYTHON_EXE=".venv/bin/python"
    fi

    for ds in $STAGED_DATASETS; do
        if [ ! -f "$ds" ]; then continue; fi # Skip deleted files
        echo "  Validating $ds..."
        $PYTHON_EXE training/validate_dataset.py --path "$ds"
        if [ $? -ne 0 ]; then
            echo "[GIT PRE-COMMIT HOOK]: Staged training dataset validation failed for $ds. Commit aborted."
            exit 1
        fi
    done
    echo "[GIT PRE-COMMIT HOOK]: All staged datasets are valid."
fi

exit 0
"""

    try:
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(hook_script)
        
        # Set execution permissions (chmod +x)
        import stat
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
        
        _pass(f"Git pre-commit hook installed at {hook_path}")
        return True
    except Exception as e:
        _fail(f"Failed to install git hook: {e}")
        return False


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
    parser.add_argument(
        "--repair", "-r",
        action="store_true",
        default=False,
        help=(
            "Sanitize, schema-repair, and truncate the dataset in-place. "
            "A .bak backup is created before any writes. "
            "Validation is run on the cleaned file afterwards."
        ),
    )
    parser.add_argument(
        "--install-hook",
        action="store_true",
        help="Install a Git pre-commit hook to automate dataset validation.",
    )
    args = parser.parse_args()

    if args.install_hook:
        if install_git_hook():
            sys.exit(0)
        else:
            sys.exit(1)

    if args.repair:
        repair(args.path, block_size_override=args.block_size)

    ok = validate(args.path, block_size_override=args.block_size)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
