"""
Unit Tests for Adapter Sandbox & Speculative Evaluation
=========================================================
Verifies evaluate_model_performance and visual PyQt6 sandbox components.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from tools.evaluate_adapters import evaluate_model_performance, extract_code_block
from app.ui.workspaces.system_config.adapter_sandbox import BenchmarkWorker, GenWorker, AdapterSandboxMixin
from app.state import AppState


class TestAdapterSandbox(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance for PyQt tests
        cls.app = QApplication.instance() or QApplication([])

    def test_extract_code_block(self):
        text_with_fences = "Some thought\n```python\nprint('hello')\n```\nSome footer"
        self.assertEqual(extract_code_block(text_with_fences), "print('hello')")
        
        text_no_fences = "print('hello')"
        self.assertEqual(extract_code_block(text_no_fences), "print('hello')")

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    @patch("app.engine.model_loader.ModelLoader.reset_instance")
    def test_evaluate_model_performance_tps(self, mock_reset, mock_get_instance):
        mock_llm = MagicMock()
        mock_llm.return_value = [{"choices": [{"text": "```python\ndef add(a, b): return a + b\n```"}]}]
        mock_llm.tokenize.return_value = [1, 2, 3, 4, 5]
        mock_get_instance.return_value = mock_llm
        
        stats = evaluate_model_performance(adapter_name="math_adapter", dataset_path=None, limit=1)
        
        self.assertEqual(stats["adapter"], "math_adapter")
        self.assertEqual(stats["eval_cases"], 1)
        self.assertTrue(stats["avg_tps"] > 0.0)
        self.assertEqual(stats["syntax_accuracy"], 100.0)

    @patch("subprocess.run")
    def test_benchmark_worker_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock writing of report file
        report_data = {
            "adapter_name": "math_adapter",
            "baseline": {"avg_tps": 10.0, "syntax_accuracy": 80.0},
            "adapted": {"avg_tps": 15.0, "syntax_accuracy": 90.0, "vram_delta_mb": 50.0},
            "tps_improvement_percent": 50.0,
            "accuracy_improvement_percent": 10.0
        }
        
        report_path = Path("data/adapters") / "eval_report_math_adapter.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as fh:
            json.dump(report_data, fh)
            
        try:
            worker = BenchmarkWorker("math_adapter")
            
            # Setup signal handlers
            results = []
            worker.finished.connect(results.append)
            
            worker.run()
            
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["adapter_name"], "math_adapter")
            self.assertEqual(results[0]["tps_improvement_percent"], 50.0)
        finally:
            if report_path.exists():
                report_path.unlink()

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_gen_worker_tps(self, mock_get_instance):
        mock_llm = MagicMock()
        mock_llm.return_value = [{"choices": [{"text": "print('speed test')"}]}]
        mock_llm.tokenize.return_value = [1, 2, 3]
        mock_get_instance.return_value = mock_llm
        
        worker = GenWorker("hello", "test_adapter")
        
        finished_signals = []
        worker.finished.connect(lambda txt, elap, tok: finished_signals.append((txt, elap, tok)))
        
        worker.run()
        
        self.assertEqual(len(finished_signals), 1)
        txt, elap, tok = finished_signals[0]
        self.assertEqual(txt, "print('speed test')")
        self.assertEqual(tok, 3)
        self.assertTrue(elap >= 0.0)
