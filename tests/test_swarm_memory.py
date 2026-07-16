"""Tests for SwarmMemory — cross-run failure/fix learning."""

import json
import os
import tempfile
import unittest

from app.engine.swarm_memory import SwarmMemory, fingerprint_failure


class TestFingerprintFailure(unittest.TestCase):
    def test_extracts_error_class_and_normalizes_message(self):
        trace = (
            "Traceback (most recent call last):\n"
            '  File "math_utils.py", line 42, in add\n'
            "AssertionError: expected 5, got 'foo' at 0x7f0000000000\n"
        )
        fp = fingerprint_failure(trace)
        self.assertTrue(fp.startswith("AssertionError:"))
        self.assertNotIn("0x7f0000000000", fp)

    def test_empty_trace_is_stable(self):
        self.assertEqual(fingerprint_failure(""), "unknown_error")

    def test_same_class_different_details_fingerprint_identically(self):
        fp1 = fingerprint_failure("TypeError: unsupported operand type(s) for +: 'int' and 'str'")
        fp2 = fingerprint_failure("TypeError: unsupported operand type(s) for +: 'int' and 'str'")
        self.assertEqual(fp1, fp2)


class TestSwarmMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "swarm_memory.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_recall_empty_store_returns_empty_string(self):
        mem = SwarmMemory("ws", db_path=self.db_path)
        self.assertEqual(mem.recall("math_utils.py", "add two numbers"), "")

    def test_record_failure_then_recall_matches_by_keyword(self):
        mem = SwarmMemory("ws", db_path=self.db_path)
        mem.record_failure("math_utils.py", "define add function", "AssertionError: expected 5 got -1")
        recalled = mem.recall("math_utils.py", "add function returns wrong value")
        self.assertIn("AssertionError", recalled)
        self.assertIn("math_utils.py", recalled)

    def test_recall_does_not_match_unrelated_task(self):
        mem = SwarmMemory("ws", db_path=self.db_path)
        mem.record_failure("math_utils.py", "define add function", "AssertionError: expected 5 got -1")
        recalled = mem.recall("network_client.py", "open a socket connection")
        self.assertEqual(recalled, "")

    def test_record_success_links_fix_to_failure_and_surfaces_on_recall(self):
        mem = SwarmMemory("ws", db_path=self.db_path)
        fp = mem.record_failure("math_utils.py", "define add function", "AssertionError: expected 5 got -1")
        mem.record_success("math_utils.py", "used + instead of - operator", [fp])
        recalled = mem.recall("math_utils.py", "add function implementation")
        self.assertIn("Previously fixed by", recalled)
        self.assertIn("+ instead of -", recalled)

    def test_persists_across_instances(self):
        mem1 = SwarmMemory("ws", db_path=self.db_path)
        mem1.record_failure("a.py", "task instructions", "ValueError: bad input")
        self.assertTrue(os.path.exists(self.db_path))

        mem2 = SwarmMemory("ws", db_path=self.db_path)
        recalled = mem2.recall("a.py", "task instructions")
        self.assertIn("ValueError", recalled)

    def test_corrupted_store_recovers_gracefully(self):
        with open(self.db_path, "w") as f:
            f.write("{not valid json")
        mem = SwarmMemory("ws", db_path=self.db_path)
        self.assertEqual(mem.recall("a.py", "anything"), "")
        # Should still be able to write after recovering from corruption.
        mem.record_failure("a.py", "task", "TypeError: boom")
        with open(self.db_path, encoding="utf-8") as f:
            data = json.loads(f.read())
        self.assertEqual(len(data), 1)


if __name__ == "__main__":
    unittest.main()
