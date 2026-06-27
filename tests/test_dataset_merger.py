"""
Unit tests for app/utils/dataset_merger.py

Covers:
  - Exact-duplicate detection
  - Conflict resolution by timestamp
  - Malformed / anomalous record filtering
  - Atomic write + creates parent directory if absent
  - validate_file helper
  - Merged output integrity
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from app.utils.dataset_merger import (
    DatasetMerger,
    _exact_hash,
    _is_anomalous,
    _prompt_key,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _record(
    user: str,
    assistant: str,
    *,
    system: str = "You are helpful.",
    source: str = "thumbs_up",
    ts: str = "2026-01-01T00:00:00+00:00",
    warning: str | None = None,
) -> dict:
    r: dict = {
        "timestamp": ts,
        "source": source,
        "messages": [
            {"role": "system",    "content": system},
            {"role": "user",      "content": user},
            {"role": "assistant", "content": assistant},
        ],
    }
    if warning is not None:
        r["warning"] = warning
    return r


def _write(path: str, records: list[dict]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ── Helper unit tests ─────────────────────────────────────────────────────────

class TestIsAnomalous:
    def test_good_record_passes(self):
        assert not _is_anomalous(_record("hi", "hello!"))

    def test_missing_messages_key(self):
        assert _is_anomalous({"timestamp": "2026-01-01T00:00:00+00:00", "source": "x"})

    def test_messages_not_a_list(self):
        assert _is_anomalous({"messages": "bad"})

    def test_too_few_messages(self):
        assert _is_anomalous({"messages": [{"role": "user", "content": "hi"}]})

    def test_no_assistant_turn(self):
        r = {"messages": [
            {"role": "system", "content": "sys"},
            {"role": "user",   "content": "hi"},
        ]}
        assert _is_anomalous(r)

    def test_empty_assistant_response(self):
        assert _is_anomalous(_record("hi", ""))
        assert _is_anomalous(_record("hi", "   "))

    def test_traceback_dump_filtered(self):
        bad_response = (
            "Traceback (most recent call last):\n"
            "  File 'x.py', line 1\n"
            "TypeError: unsupported operand"
        )
        assert _is_anomalous(_record("hi", bad_response))

    def test_latency_warning_flag_filtered(self):
        assert _is_anomalous(_record("hi", "good", warning="thermal"))

    def test_long_traceback_not_filtered(self):
        # A long response that happens to mention an error is likely a tutorial, not a dump.
        long_response = "SyntaxError: " + "x" * 700
        assert not _is_anomalous(_record("explain errors", long_response))


class TestHashing:
    def test_exact_hash_stable(self):
        r = _record("hello", "world")
        assert _exact_hash(r) == _exact_hash(r.copy())

    def test_different_assistant_differs_in_exact_hash(self):
        r1 = _record("hello", "world")
        r2 = _record("hello", "universe")
        assert _exact_hash(r1) != _exact_hash(r2)

    def test_same_prompt_shares_prompt_key(self):
        r1 = _record("hello", "world")
        r2 = _record("hello", "universe")
        assert _prompt_key(r1) == _prompt_key(r2)

    def test_different_prompts_differ_in_prompt_key(self):
        r1 = _record("hello", "world")
        r2 = _record("goodbye", "world")
        assert _prompt_key(r1) != _prompt_key(r2)

    def test_prompt_key_ignores_assistant(self):
        r1 = _record("hi", "response A", ts="2025-01-01T00:00:00+00:00")
        r2 = _record("hi", "response B", ts="2026-06-01T00:00:00+00:00")
        assert _prompt_key(r1) == _prompt_key(r2)


# ── merge_files integration tests ─────────────────────────────────────────────

class TestMergeFiles:
    def setup_method(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = self._tmpdir.name

    def teardown_method(self):
        self._tmpdir.cleanup()

    def _paths(self):
        return (
            os.path.join(self.tmp, "primary.jsonl"),
            os.path.join(self.tmp, "incoming.jsonl"),
        )

    # ── stat keys ────────────────────────────────────────────────────────────

    def test_return_keys_match_spec(self):
        primary, incoming = self._paths()
        _write(primary, [])
        _write(incoming, [_record("Q", "A")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert set(stats.keys()) == {"added", "duplicates_skipped", "errors"}

    # ── plain add ────────────────────────────────────────────────────────────

    def test_new_record_is_added(self):
        primary, incoming = self._paths()
        _write(primary, [_record("Q1", "A1")])
        _write(incoming, [_record("Q2", "A2")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["added"] == 1
        assert stats["duplicates_skipped"] == 0
        assert stats["errors"] == 0
        assert len(_read(primary)) == 2

    def test_multiple_new_records(self):
        primary, incoming = self._paths()
        _write(primary, [])
        _write(incoming, [_record(f"Q{i}", f"A{i}") for i in range(5)])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["added"] == 5
        assert len(_read(primary)) == 5

    # ── duplicate detection ───────────────────────────────────────────────────

    def test_exact_duplicate_skipped(self):
        primary, incoming = self._paths()
        r = _record("Q", "A")
        _write(primary, [r])
        _write(incoming, [r])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["added"] == 0
        assert stats["duplicates_skipped"] == 1
        assert len(_read(primary)) == 1

    def test_same_prompt_same_response_is_duplicate(self):
        """Identical prompt + response from a different source tag is still a duplicate."""
        primary, incoming = self._paths()
        _write(primary, [_record("Q", "A", source="thumbs_up")])
        _write(incoming, [_record("Q", "A", source="corrected")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["duplicates_skipped"] == 1
        assert stats["added"] == 0

    def test_multiple_duplicates_all_counted(self):
        primary, incoming = self._paths()
        records = [_record(f"Q{i}", f"A{i}") for i in range(4)]
        _write(primary, records)
        _write(incoming, records)
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["duplicates_skipped"] == 4
        assert stats["added"] == 0

    # ── conflict resolution ───────────────────────────────────────────────────

    def test_newer_incoming_replaces_older_primary(self):
        primary, incoming = self._paths()
        _write(primary, [_record("Q", "OldAnswer", ts="2025-01-01T00:00:00+00:00")])
        _write(incoming, [_record("Q", "NewAnswer", ts="2026-06-01T00:00:00+00:00")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["added"] == 1
        final = _read(primary)
        assert len(final) == 1
        asst = next(m["content"] for m in final[0]["messages"] if m["role"] == "assistant")
        assert asst == "NewAnswer"

    def test_older_incoming_does_not_replace_newer_primary(self):
        primary, incoming = self._paths()
        _write(primary, [_record("Q", "NewerAnswer", ts="2026-06-01T00:00:00+00:00")])
        _write(incoming, [_record("Q", "OlderAnswer", ts="2025-01-01T00:00:00+00:00")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["duplicates_skipped"] == 1
        assert stats["added"] == 0
        final = _read(primary)
        asst = next(m["content"] for m in final[0]["messages"] if m["role"] == "assistant")
        assert asst == "NewerAnswer"

    def test_same_timestamp_conflict_keeps_primary(self):
        ts = "2026-03-15T12:00:00+00:00"
        primary, incoming = self._paths()
        _write(primary, [_record("Q", "PrimaryAnswer", ts=ts)])
        _write(incoming, [_record("Q", "IncomingAnswer", ts=ts)])
        DatasetMerger.merge_files(primary, incoming)
        final = _read(primary)
        asst = next(m["content"] for m in final[0]["messages"] if m["role"] == "assistant")
        assert asst == "PrimaryAnswer"

    # ── error / anomaly filtering ─────────────────────────────────────────────

    def test_empty_assistant_response_counted_as_error(self):
        primary, incoming = self._paths()
        _write(primary, [])
        _write(incoming, [_record("Q", ""), _record("Q2", "fine")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["errors"] == 1
        assert stats["added"] == 1

    def test_latency_warning_counted_as_error(self):
        primary, incoming = self._paths()
        _write(primary, [])
        _write(incoming, [_record("Q", "fine", warning="thermal")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["errors"] == 1
        assert stats["added"] == 0

    def test_traceback_response_counted_as_error(self):
        primary, incoming = self._paths()
        _write(primary, [])
        bad = _record("Q", "Traceback (most recent call last):\n  TypeError: bad")
        _write(incoming, [bad])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["errors"] == 1

    def test_malformed_json_line_skipped_gracefully(self):
        primary, incoming = self._paths()
        _write(primary, [])
        # Write one valid line and one garbage line
        with open(incoming, "w") as fh:
            fh.write(json.dumps(_record("Q", "A")) + "\n")
            fh.write("this is not json at all\n")
            fh.write(json.dumps(_record("Q2", "A2")) + "\n")
        stats = DatasetMerger.merge_files(primary, incoming)
        # Malformed JSON is silently skipped (not counted as error — it's not a record)
        assert stats["added"] == 2
        assert len(_read(primary)) == 2

    def test_missing_messages_key_counted_as_error(self):
        primary, incoming = self._paths()
        _write(primary, [])
        bad = {"timestamp": "2026-01-01T00:00:00+00:00", "source": "x"}
        _write(incoming, [bad])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["errors"] == 1
        assert stats["added"] == 0

    def test_does_not_crash_on_empty_incoming(self):
        primary, incoming = self._paths()
        _write(primary, [_record("Q", "A")])
        _write(incoming, [])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats == {"added": 0, "duplicates_skipped": 0, "errors": 0}
        assert len(_read(primary)) == 1

    def test_does_not_crash_on_empty_primary(self):
        primary, incoming = self._paths()
        _write(primary, [])
        _write(incoming, [_record("Q", "A")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["added"] == 1

    def test_does_not_crash_when_primary_missing(self):
        incoming = os.path.join(self.tmp, "incoming.jsonl")
        primary = os.path.join(self.tmp, "sub", "primary.jsonl")
        _write(incoming, [_record("Q", "A")])
        stats = DatasetMerger.merge_files(primary, incoming)
        assert stats["added"] == 1
        assert os.path.exists(primary)

    # ── output integrity ──────────────────────────────────────────────────────

    def test_output_is_valid_jsonl(self):
        primary, incoming = self._paths()
        _write(primary, [_record("Q1", "A1")])
        _write(incoming, [_record("Q2", "A2"), _record("Q3", "A3")])
        DatasetMerger.merge_files(primary, incoming)
        records = _read(primary)
        assert len(records) == 3
        for r in records:
            assert "messages" in r
            assert isinstance(r["messages"], list)

    def test_primary_anomalous_records_cleaned_on_merge(self):
        """Corrupt records already in primary are removed during a merge pass."""
        primary, incoming = self._paths()
        _write(primary, [
            _record("Good", "fine"),
            _record("Bad", "", ts="2025-01-01T00:00:00+00:00"),  # empty assistant
        ])
        _write(incoming, [])
        DatasetMerger.merge_files(primary, incoming)
        final = _read(primary)
        assert len(final) == 1
        user = next(m["content"] for m in final[0]["messages"] if m["role"] == "user")
        assert user == "Good"

    def test_write_is_atomic(self):
        """A .merge_tmp file must not persist after merge completes."""
        primary, incoming = self._paths()
        _write(primary, [])
        _write(incoming, [_record("Q", "A")])
        DatasetMerger.merge_files(primary, incoming)
        assert not os.path.exists(primary + ".merge_tmp")

    # ── validate_file ─────────────────────────────────────────────────────────

    def test_validate_file_counts(self):
        path = os.path.join(self.tmp, "check.jsonl")
        _write(path, [
            _record("Q1", "A1"),           # valid
            _record("Q2", ""),             # invalid — empty assistant
            _record("Q3", "A3"),           # valid
            _record("Q4", "A4", warning="x"),  # invalid — warning flag
        ])
        result = DatasetMerger.validate_file(path)
        assert result["total"] == 4
        assert result["valid"] == 2
        assert result["invalid"] == 2

    def test_validate_file_missing_path(self):
        result = DatasetMerger.validate_file("/nonexistent/path/data.jsonl")
        assert result == {"total": 0, "valid": 0, "invalid": 0}
