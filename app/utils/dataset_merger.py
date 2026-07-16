"""
Dataset Merger — Multi-User Trace Import
=========================================
Merges curated.jsonl files from multiple developers without corrupting the
local training records.

Key guarantees:
  • Exact duplicate conversations (same system + user + assistant text) are
    silently dropped.
  • Conflicts (same prompt, different response) are resolved by keeping the
    record with the most recent timestamp.
  • Anomalous records (empty assistant reply, raw exception tracebacks, or
    thermal/latency warning flags) are filtered before writing.
  • The primary file is written atomically (temp-file + os.replace).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("karl.dataset_merger")


# ── Anomaly detection helpers ──────────────────────────────────────────────────

_TRACEBACK_SIGNALS = (
    "Traceback (most recent call last):",
    "SyntaxError:",
    "NameError:",
    "TypeError:",
    "ValueError:",
    "RuntimeError:",
    "AttributeError:",
    "ImportError:",
)

def _assistant_content(record: dict[str, Any]) -> str:
    """Return the assistant message content, or '' if absent."""
    for m in record.get("messages", []):
        if m.get("role") == "assistant":
            return m.get("content", "")
    return ""

def _is_anomalous(record: dict[str, Any]) -> bool:
    """
    Return True if the record should be filtered out:
      - No 'messages' key
      - Non-list / empty messages
      - Assistant response missing or blank
      - Response is entirely a Python traceback / exception dump
      - Record carries a latency / thermal warning flag
    """
    if not isinstance(record.get("messages"), list):
        return True
    messages = record["messages"]
    if len(messages) < 2:
        return True

    # Must have at least a user and an assistant turn.
    roles = {m.get("role") for m in messages}
    if "assistant" not in roles:
        return True

    content = _assistant_content(record)
    if not content.strip():
        return True

    # Reject responses that look like raw exception dumps (often from tool errors
    # being accidentally captured as the model response).
    if any(sig in content for sig in _TRACEBACK_SIGNALS) and len(content) < 600:
        return True

    # Reject records flagged with a latency / thermal degradation warning.
    if "warning" in record:
        return True

    return False


# ── Hashing helpers ────────────────────────────────────────────────────────────

def _exact_hash(record: dict[str, Any]) -> str:
    """SHA-256 of the full conversation (all roles + content) — catches perfect duplicates."""
    parts: list[str] = []
    for m in record.get("messages", []):
        parts.append(f"{m.get('role','')}:{m.get('content','')}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _prompt_key(record: dict[str, Any]) -> str:
    """SHA-256 of system + user turns only — used to detect same-prompt conflicts."""
    parts: list[str] = []
    for m in record.get("messages", []):
        if m.get("role") in ("system", "user"):
            parts.append(f"{m.get('role','')}:{m.get('content','')}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _parse_ts(record: dict[str, Any]) -> datetime:
    """Parse the record timestamp, falling back to epoch 0 on any error."""
    ts = record.get("timestamp", "")
    if not ts:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)


# ── Loader helpers ─────────────────────────────────────────────────────────────

def _load_jsonl(path: str) -> list[dict[str, Any]]:
    """Read a JSONL file, silently skipping blank and malformed lines."""
    records: list[dict[str, Any]] = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    records.append(obj)
            except json.JSONDecodeError as exc:
                logger.debug("Skipping malformed JSON on line %d of %s: %s", lineno, path, exc)
    return records


def _write_jsonl_atomic(path: str, records: list[dict[str, Any]]) -> None:
    """Write records to *path* atomically via a sibling temp file."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".merge_tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── Public API ─────────────────────────────────────────────────────────────────

class DatasetMerger:
    """
    Stateless utility class — call DatasetMerger.merge_files() directly.
    """

    @staticmethod
    def merge_files(primary_path: str, incoming_path: str) -> dict[str, int]:
        """
        Merge *incoming_path* into *primary_path* in place.

        Parameters
        ----------
        primary_path:
            Path to the local curated.jsonl that will be updated.
        incoming_path:
            Path to the teammate's curated.jsonl to absorb.

        Returns
        -------
        dict with keys:
            added              — records from incoming that were written to primary
            duplicates_skipped — exact matches or older conflicts already in primary
            errors             — records filtered for being anomalous / malformed
        """
        stats: dict[str, int] = {
            "added": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

        # 1. Load both files
        primary_raw = _load_jsonl(primary_path)
        incoming_raw = _load_jsonl(incoming_path)

        logger.info(
            "Merge starting: %d primary records, %d incoming records.",
            len(primary_raw), len(incoming_raw),
        )

        # 2. Validate primary records (keep only clean ones as our baseline).
        primary_clean: list[dict[str, Any]] = [r for r in primary_raw if not _is_anomalous(r)]

        # 3. Build lookup maps from the clean primary set.
        #    exact_hashes  — detect perfect duplicates quickly
        #    prompt_to_idx — map prompt_key → index in primary_clean for conflict resolution
        exact_hashes: set[str] = {_exact_hash(r) for r in primary_clean}
        prompt_to_idx: dict[str, int] = {
            _prompt_key(r): i for i, r in enumerate(primary_clean)
        }

        # 4. Process each incoming record.
        additions: list[dict[str, Any]] = []

        for record in incoming_raw:
            # Filter anomalies first.
            if _is_anomalous(record):
                stats["errors"] += 1
                continue

            eh = _exact_hash(record)

            # Exact duplicate — already exists byte-for-byte.
            if eh in exact_hashes:
                stats["duplicates_skipped"] += 1
                continue

            pk = _prompt_key(record)

            if pk in prompt_to_idx:
                # Same prompt exists — keep the record with the latest timestamp.
                # prompt_to_idx indexes into the eventual primary_clean + additions
                # list, so resolve into whichever of the two lists actually holds
                # that slot right now (additions may still be shorter than the
                # stored offset implies, since it grows as we process the batch).
                existing_idx = prompt_to_idx[pk]
                if existing_idx < len(primary_clean):
                    existing = primary_clean[existing_idx]
                else:
                    existing = additions[existing_idx - len(primary_clean)]
                if _parse_ts(record) > _parse_ts(existing):
                    # Incoming is newer: replace the existing record in-place.
                    if existing_idx < len(primary_clean):
                        primary_clean[existing_idx] = record
                    else:
                        additions[existing_idx - len(primary_clean)] = record
                    # Update exact hash set so subsequent duplicates of the new
                    # record are caught correctly.
                    exact_hashes.discard(_exact_hash(existing))
                    exact_hashes.add(eh)
                    stats["added"] += 1
                    logger.debug(
                        "Conflict resolved — replaced older record for prompt key %s.", pk[:12]
                    )
                else:
                    # Existing is newer or same age — ignore incoming.
                    stats["duplicates_skipped"] += 1
            else:
                # Brand new prompt: schedule for appending.
                additions.append(record)
                exact_hashes.add(eh)
                prompt_to_idx[pk] = len(primary_clean) + len(additions) - 1
                stats["added"] += 1

        # 5. Combine and write atomically.
        final_records = primary_clean + additions
        _write_jsonl_atomic(primary_path, final_records)

        logger.info(
            "Merge complete. added=%d, duplicates_skipped=%d, errors=%d. "
            "Final dataset: %d records.",
            stats["added"],
            stats["duplicates_skipped"],
            stats["errors"],
            len(final_records),
        )
        return stats

    @staticmethod
    def validate_file(path: str) -> dict[str, int]:
        """
        Scan a JSONL file and report how many records pass/fail validation.
        Useful for pre-flight checking before a merge.
        """
        records = _load_jsonl(path)
        clean = sum(1 for r in records if not _is_anomalous(r))
        return {
            "total": len(records),
            "valid": clean,
            "invalid": len(records) - clean,
        }
