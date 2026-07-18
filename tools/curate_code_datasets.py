#!/usr/bin/env python3
"""Curate code SFT/DPO datasets from Karl trace logs."""

from __future__ import annotations

import argparse
import ast
import json
import random
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.compactor import decompact_trace


POSITIVE_FEEDBACK = {"thumbs_up", "corrected", "eval_chosen"}
NEGATIVE_FEEDBACK = {"thumbs_down", "eval_rejected"}
CODE_HINT_RE = re.compile(
    r"\b(code|python|pytest|function|class|module|diff|patch|bug|test|compile|traceback|exception)\b",
    re.IGNORECASE,
)
CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)
DEFAULT_MAX_TOKENS = 3500


def iter_trace_records(trace_dir: Path) -> Iterable[dict]:
    seen: set[str] = set()
    for path in sorted(trace_dir.glob("trace_*.jsonl")):
        yield from _read_jsonl(path, compact=False, seen=seen)
    for path in sorted(trace_dir.glob("trace_*.jsonl.compact")):
        yield from _read_jsonl(path, compact=True, seen=seen)


def _read_jsonl(path: Path, compact: bool, seen: set[str]) -> Iterable[dict]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = decompact_trace(line) if compact else json.loads(line)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                if not isinstance(record, dict):
                    continue
                record_id = str(record.get("id") or "")
                if record_id and record_id in seen:
                    continue
                if record_id:
                    seen.add(record_id)
                yield record
    except OSError:
        return


def is_verified_success(record: dict) -> bool:
    haystack = json.dumps(record, ensure_ascii=False).lower()
    return any(
        marker in haystack
        for marker in (
            '"verified": true',
            '"verification_passed": true',
            '"passed": true',
            "verification passed",
            "dry-run verification passed",
            "verified successfully",
        )
    )


def is_code_record(record: dict) -> bool:
    workflow = str(record.get("workflow", "")).lower()
    if "code" in workflow:
        return True
    text = "\n".join(
        str(record.get(key, ""))
        for key in ("compiled_prompt", "response", "raw_output", "thinking", "corrected_response")
    )
    return bool(CODE_HINT_RE.search(text) or "```" in text)


def prompt_key(record: dict) -> tuple[str, str]:
    system = str(record.get("system_prompt") or "")
    user = extract_user_prompt(str(record.get("compiled_prompt") or ""))
    if not user:
        user = str(record.get("prompt") or "")
    return system, user


def extract_user_prompt(compiled_prompt: str) -> str:
    if not compiled_prompt:
        return ""

    patterns = [
        r"(?is)(?:^|\n)user:\s*(.*?)(?=\nassistant:|\n<\|assistant|$)",
        r"(?is)<\|user\|>\s*(.*?)(?=<\|assistant\|>|$)",
        r"(?is)###\s*user\s*(.*?)(?=###\s*assistant|$)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, compiled_prompt)
        if matches:
            return matches[-1].strip()

    lines = [line.strip() for line in compiled_prompt.splitlines() if line.strip()]
    return "\n".join(lines[-12:]).strip()


def assistant_response(record: dict, chosen: bool) -> str:
    if chosen and record.get("corrected_response"):
        return str(record["corrected_response"])
    return str(record.get("response") or record.get("raw_output") or "")


def build_datasets(records: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    sft: list[dict] = []
    groups: dict[tuple[str, str], dict[str, list[str]]] = {}

    for record in records:
        if not is_code_record(record):
            continue

        feedback = str(record.get("feedback") or "none")
        positive = feedback in POSITIVE_FEEDBACK or is_verified_success(record)
        negative = feedback in NEGATIVE_FEEDBACK
        if not positive and not negative:
            continue

        system, user = prompt_key(record)
        response = assistant_response(record, chosen=positive)
        if not user or not response:
            continue

        if positive:
            sft.append({
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": response},
                ],
                "source": "trace",
                "trace_id": record.get("id"),
                "timestamp": record.get("timestamp"),
            })

        bucket = groups.setdefault((system, user), {"chosen": [], "rejected": []})
        if positive:
            bucket["chosen"].append(response)
        if negative:
            bucket["rejected"].append(response)

    dpo: list[dict] = []
    for (system, user), bucket in groups.items():
        pair_count = min(len(bucket["chosen"]), len(bucket["rejected"]))
        for idx in range(pair_count):
            dpo.append({
                "prompt": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "chosen": [{"role": "assistant", "content": bucket["chosen"][idx]}],
                "rejected": [{"role": "assistant", "content": bucket["rejected"][idx]}],
            })

    return sft, dpo


def write_jsonl(path: Path, rows: Iterable[dict], sft_only_messages: bool = False) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            out = {"messages": row["messages"]} if sft_only_messages else row
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
            count += 1
    return count


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _code_snippets(text: str) -> list[str]:
    blocks = CODE_BLOCK_RE.findall(text)
    return blocks if blocks else [text]


def is_syntactically_valid(assistant_content: str) -> bool:
    """Every assistant response must contain error-free Python: parse fenced
    code blocks if present, otherwise the raw response itself."""
    for snippet in _code_snippets(assistant_content):
        try:
            ast.parse(snippet)
        except SyntaxError:
            return False
    return True


def estimate_tokens(text: str) -> int:
    """Character-length heuristic (~4 chars/token) — cheap enough to run over
    the whole dataset without loading a real tokenizer."""
    return len(text) // 4


def passes_quality_checks(row: dict, max_tokens: int = DEFAULT_MAX_TOKENS) -> bool:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return False

    combined = "\n".join(str(m.get("content", "")) for m in messages)
    if estimate_tokens(combined) > max_tokens:
        return False

    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    if not assistant_messages:
        return False
    return all(is_syntactically_valid(str(m.get("content", ""))) for m in assistant_messages)


def merge_datasets(
    curated_path: Path,
    synthetic_path: Path,
    output_path: Path,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    seed: int | None = None,
) -> dict:
    """Merge curated trace-derived examples with codebase-scraped synthetic
    examples, public instruction examples, and library-doc-scraped examples,
    dropping rows with invalid Python or oversized prompts, then shuffle and
    write the validated set to *output_path*."""
    curated = load_jsonl(curated_path)
    synthetic = load_jsonl(synthetic_path)

    public_path = curated_path.parent / "public_code_sft.jsonl"
    public_data = load_jsonl(public_path) if public_path.exists() else []

    scraped_library_path = curated_path.parent / "scraped_library_sft.jsonl"
    scraped_library_data = load_jsonl(scraped_library_path) if scraped_library_path.exists() else []

    self_correction_path = curated_path.parent / "self_correction_sft.jsonl"
    self_correction_data = load_jsonl(self_correction_path) if self_correction_path.exists() else []

    combined = curated + synthetic + public_data + scraped_library_data + self_correction_data

    valid_rows = [row for row in combined if passes_quality_checks(row, max_tokens=max_tokens)]

    rng = random.Random(seed)
    rng.shuffle(valid_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for row in valid_rows:
            fh.write(json.dumps({"messages": row["messages"]}, ensure_ascii=False) + "\n")

    return {
        "curated_total": len(curated),
        "synthetic_total": len(synthetic),
        "public_total": len(public_data),
        "scraped_library_total": len(scraped_library_data),
        "self_correction_total": len(self_correction_data),
        "combined_total": len(combined),
        "valid_total": len(valid_rows),
        "discarded_total": len(combined) - len(valid_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Curate Karl trace logs into code SFT/DPO datasets.")
    parser.add_argument("--trace-dir", default="data/logs/traces", help="Trace log directory")
    parser.add_argument("--out-dir", default="data/training/code", help="Output dataset directory")
    parser.add_argument("--keep-metadata", action="store_true", help="Keep trace metadata in SFT rows")
    parser.add_argument("--synthetic-path", default=None, help="Codebase-scraped SFT JSONL to merge in (see tools/generate_code_sft_dataset.py)")
    parser.add_argument("--merged-out", default=None, help="Output path for the merged, validated SFT dataset")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Discard rows whose prompt+response estimate exceeds this many tokens")
    parser.add_argument("--seed", type=int, default=None, help="Shuffle seed for the merged dataset")
    parser.add_argument("--skip-merge", action="store_true", help="Skip the merge/validate step")
    args = parser.parse_args()

    trace_dir = Path(args.trace_dir)
    out_dir = Path(args.out_dir)
    records = list(iter_trace_records(trace_dir))
    sft, dpo = build_datasets(records)

    sft_path = out_dir / "sft.jsonl"
    dpo_path = out_dir / "dpo.jsonl"
    sft_count = write_jsonl(sft_path, sft, sft_only_messages=not args.keep_metadata)
    dpo_count = write_jsonl(dpo_path, dpo)

    print(f"Read {len(records)} unique trace records from {trace_dir}")
    print(f"Wrote {sft_count} SFT examples to {sft_path}")
    print(f"Wrote {dpo_count} DPO pairs to {dpo_path}")

    if not args.skip_merge:
        synthetic_path = Path(args.synthetic_path) if args.synthetic_path else out_dir / "synthetic_code_sft.jsonl"
        merged_path = Path(args.merged_out) if args.merged_out else out_dir / "merged_sft.jsonl"
        stats = merge_datasets(sft_path, synthetic_path, merged_path, max_tokens=args.max_tokens, seed=args.seed)
        print(
            f"Merged {stats['curated_total']} curated + {stats['synthetic_total']} synthetic "
            f"+ {stats['public_total']} public + {stats['scraped_library_total']} library-scraped "
            f"+ {stats['self_correction_total']} self-corrected = {stats['combined_total']} rows; "
            f"kept {stats['valid_total']}, discarded {stats['discarded_total']} (invalid syntax or over {args.max_tokens} tokens)."
        )
        print(f"Wrote validated, shuffled dataset to {merged_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
