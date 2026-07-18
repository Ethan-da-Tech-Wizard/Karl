"""Tests for core/prompt_optimizer.py — mutation and hill-climbing optimize_loop."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.default_prompts import DEFAULT_SYSTEM_PROMPT, load_prompt_presets
from core.prompt_optimizer import PromptOptimizer
from eval.harness import CaseResult, EvalHarness, EvalReport


def _report(score: float, has_failure: bool) -> EvalReport:
    case = CaseResult(
        case_id="c0", prompt="q", workflow="general_chat", template="t",
        output="out", grader="keyword_hit",
        grade={"passed": not has_failure, "score": score, "detail": "bad" if has_failure else ""},
        latency_s=0.1, context_used=[],
    )
    return EvalReport(
        workflow="general_chat", template="t", dataset="d", total=1,
        passed=0 if has_failure else 1, failed=1 if has_failure else 0, errors=0,
        pass_rate=0.0, avg_latency_s=0.1, avg_score=score, timestamp="t", cases=[case],
    )


def _write_dataset(path: Path, n: int = 4) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for i in range(n):
            fh.write(json.dumps({"id": f"c{i}", "prompt": f"q{i}", "expected": "ok"}) + "\n")


class TestMutatePrompt(unittest.TestCase):
    def test_returns_current_prompt_when_no_failures(self):
        optimizer = PromptOptimizer()
        self.assertEqual(optimizer.mutate_prompt("base", []), "base")

    @patch("core.prompt_optimizer.ModelLoader.get_instance")
    def test_mutates_prompt_using_failures(self, mock_get_instance):
        mock_llm = MagicMock(return_value={"choices": [{"text": "```\nRefined prompt text.\n```"}]})
        mock_get_instance.return_value = mock_llm

        optimizer = PromptOptimizer()
        failures = [{"prompt": "2+2?", "output": "5", "detail": "wrong answer"}]
        result = optimizer.mutate_prompt("Old prompt", failures)

        self.assertEqual(result, "Refined prompt text.")
        mock_llm.assert_called_once()

    @patch("core.prompt_optimizer.ModelLoader.get_instance", side_effect=RuntimeError("no model"))
    def test_falls_back_to_current_prompt_on_load_failure(self, _mock):
        optimizer = PromptOptimizer()
        result = optimizer.mutate_prompt("Old prompt", [{"prompt": "x", "output": "y", "detail": "z"}])
        self.assertEqual(result, "Old prompt")


class TestOptimizeLoop(unittest.TestCase):
    def test_requires_at_least_two_cases(self):
        optimizer = PromptOptimizer()
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "cases.jsonl"
            _write_dataset(dataset_path, n=1)
            with self.assertRaises(ValueError):
                optimizer.optimize_loop("_karl_default", str(dataset_path), iterations=1)

    def test_unknown_prompt_key_falls_back_to_default(self):
        optimizer = PromptOptimizer()
        with patch.object(EvalHarness, "run", return_value=_report(0.5, has_failure=False)):
            with tempfile.TemporaryDirectory() as tmp:
                dataset_path = Path(tmp) / "cases.jsonl"
                _write_dataset(dataset_path)
                result = optimizer.optimize_loop("not_a_real_key", str(dataset_path), iterations=0)
        self.assertEqual(result, DEFAULT_SYSTEM_PROMPT)

    @patch.object(EvalHarness, "run")
    def test_keeps_better_candidate(self, mock_run):
        mock_run.side_effect = [
            _report(0.5, has_failure=True),   # baseline on mini-val
            _report(0.2, has_failure=True),   # mini-train eval -> has failures, triggers mutation
            _report(0.9, has_failure=False),  # candidate on mini-val, better than baseline
        ]
        optimizer = PromptOptimizer()
        optimizer.mutate_prompt = MagicMock(return_value="mutated prompt")

        progress_calls = []
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "cases.jsonl"
            _write_dataset(dataset_path)
            result = optimizer.optimize_loop(
                "_karl_default", str(dataset_path), iterations=1,
                progress_callback=lambda *args: progress_calls.append(args),
            )

        self.assertEqual(result, "mutated prompt")
        optimizer.mutate_prompt.assert_called_once()
        self.assertEqual(len(progress_calls), 2)  # baseline (iter 0) + iteration 1
        self.assertEqual(progress_calls[-1][2], 0.9)  # best_score after keeping candidate

    @patch.object(EvalHarness, "run")
    def test_discards_worse_candidate(self, mock_run):
        mock_run.side_effect = [
            _report(0.8, has_failure=True),   # baseline on mini-val
            _report(0.2, has_failure=True),   # mini-train eval -> triggers mutation
            _report(0.3, has_failure=False),  # candidate on mini-val, worse than baseline
        ]
        optimizer = PromptOptimizer()
        optimizer.mutate_prompt = MagicMock(return_value="worse mutated prompt")
        baseline_prompt = load_prompt_presets()["_karl_default"]["prompt"]

        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "cases.jsonl"
            _write_dataset(dataset_path)
            result = optimizer.optimize_loop("_karl_default", str(dataset_path), iterations=1)

        self.assertEqual(result, baseline_prompt)

    @patch.object(EvalHarness, "run")
    def test_skips_mutation_when_no_train_failures(self, mock_run):
        mock_run.side_effect = [
            _report(0.9, has_failure=False),  # baseline on mini-val
            _report(1.0, has_failure=False),  # mini-train eval -> no failures, nothing to mutate
        ]
        optimizer = PromptOptimizer()
        optimizer.mutate_prompt = MagicMock()

        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "cases.jsonl"
            _write_dataset(dataset_path)
            optimizer.optimize_loop("_karl_default", str(dataset_path), iterations=1)

        optimizer.mutate_prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
