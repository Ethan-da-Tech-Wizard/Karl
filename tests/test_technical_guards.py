"""
Technical Guards Tests — Karl SWE-bench Optimizations
======================================================
Verifies ripgrep codebase searches, AST/JSON validation in the orchestrator,
and Reason-Before-Action tagging enforcer.
"""

import tests.qt_test_helper  # noqa: F401

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from PyQt6.QtCore import QCoreApplication
from app.utils.codebase_search import codebase_search
from app.engine.swarm_agents import parse_reasoning_and_tool
from app.engine.swarm_orchestrator import SwarmOrchestratorThread


class TestTechnicalGuards(unittest.TestCase):
    def setUp(self):
        # Create a temporary sandbox directory for test assets
        self.sandbox_dir = tempfile.TemporaryDirectory()
        self.workspace_path = self.sandbox_dir.name

    def tearDown(self):
        self.sandbox_dir.cleanup()

    def test_codebase_search_ripgrep(self):
        # Create a test file with unique content
        target_file = os.path.join(self.workspace_path, "search_target.py")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("\n\n# UNIQUE_TEST_PATTERN_XYZ\n")

        # Query the codebase search
        results = codebase_search("UNIQUE_TEST_PATTERN_XYZ", self.workspace_path)
        
        # Verify result is parsed correctly
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["filepath"], "search_target.py")
        self.assertEqual(results[0]["line"], 3)
        self.assertIn("UNIQUE_TEST_PATTERN_XYZ", results[0]["content"])

    def test_parse_reasoning_and_tool(self):
        # 1. Valid case with reasoning preceding tool call
        raw_valid = (
            "<reasoning>\n"
            "We need to fix the addition function.\n"
            "</reasoning>\n"
            "<tool_call name=\"write_file\" file=\"math.py\">\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "</tool_call>"
        )
        reasoning, content = parse_reasoning_and_tool(raw_valid)
        self.assertEqual(reasoning, "We need to fix the addition function.")
        self.assertIn("return a + b", content)

        # 2. Blocked case: tool call without reasoning preceding it
        raw_invalid = (
            "<tool_call name=\"write_file\">\n"
            "def add(a, b): return a + b\n"
            "</tool_call>"
        )
        with self.assertRaises(ValueError) as context:
            parse_reasoning_and_tool(raw_invalid)
        self.assertIn("Action blocked", str(context.exception))

        # 3. Graceful fallback case: no tool call at all
        raw_text = "Just a general explanation with no tool calls."
        reasoning, content = parse_reasoning_and_tool(raw_text)
        self.assertIsNone(reasoning)
        self.assertIsNone(content)

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_orchestrator_syntax_validation_guards(self, mock_get_llm):
        # We need a PyQt application context for QThread signals
        app = QCoreApplication.instance() or QCoreApplication(sys.argv)

        # Set up mock LLM to return invalid python syntax first, then valid python
        call_count = 0
        def stateful_mock_llm(prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "Edit files",
                    "tasks": [
                        {
                            "filepath": "broken.py",
                            "instructions": "Write code."
                        }
                    ]
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            else:
                if call_count == 2:
                    # Broken syntax (missing colon)
                    return {"choices": [{"text": "<reasoning>Broken</reasoning><tool_call>def broken()\n    pass</tool_call>"}]}
                else:
                    # Correct syntax
                    return {"choices": [{"text": "<reasoning>Fixed</reasoning><tool_call>def broken():\n    pass</tool_call>"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        # Create dummy test script that succeeds instantly
        test_script_path = os.path.join(self.workspace_path, "run_tests.py")
        with open(test_script_path, "w", encoding="utf-8") as f:
            f.write("import sys\nsys.exit(0)\n")

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Write broken.py",
            test_command=f"{sys.executable} run_tests.py"
        )

        signals = {
            "status": [],
            "test_results": [],
            "finished": None
        }
        orchestrator.status_update.connect(lambda msg: signals["status"].append(msg))
        orchestrator.test_result.connect(lambda passed, trace: signals["test_results"].append((passed, trace)))
        orchestrator.finished_swarm.connect(lambda success, summary: signals.update({"finished": (success, summary)}))

        # Run orchestrator
        orchestrator.run()

        # The first attempt should have triggered the AST syntax guard and been blocked
        # The second attempt (fixed) should pass and succeed
        self.assertEqual(len(signals["test_results"]), 2)
        # Attempt 1: Failed on AST syntax guard
        self.assertFalse(signals["test_results"][0][0])
        self.assertIn("SyntaxError", signals["test_results"][0][1])
        # Attempt 2: Passed
        self.assertTrue(signals["test_results"][1][0])

        # Verify broken.py contains the correct syntax
        with open(os.path.join(self.workspace_path, "broken.py"), "r") as f:
            content = f.read()
            self.assertIn("def broken():", content)


if __name__ == "__main__":
    unittest.main()
