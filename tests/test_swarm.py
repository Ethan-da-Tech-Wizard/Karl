"""
Swarm Orchestrator Tests — Karl Workbench
==========================================
Integration tests verifying the multi-agent planning, execution, and self-correction
loop using a stateful mock LLM and a temporary codebase sandbox.
"""

import tests.qt_test_helper  # noqa: F401

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from app.engine.swarm_orchestrator import SwarmOrchestratorThread


class TestSwarmOrchestrator(unittest.TestCase):
    def setUp(self):
        # Create a temporary sandbox directory for code editing and testing
        self.sandbox_dir = tempfile.TemporaryDirectory()
        self.workspace_path = self.sandbox_dir.name

        # Create a dummy python test script in the workspace that asserts add(2, 3) == 5
        self.test_script_path = os.path.join(self.workspace_path, "run_tests.py")
        test_script_content = (
            "import sys\n"
            "sys.dont_write_bytecode = True\n"
            "try:\n"
            "    from math_utils import add\n"
            "    assert add(2, 3) == 5, f'Expected 5, got {add(2,3)}'\n"
            "    print('TESTS PASSED')\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    print(f'TESTS FAILED: {e}')\n"
            "    sys.exit(1)\n"
        )
        with open(self.test_script_path, "w", encoding="utf-8") as f:
            f.write(test_script_content)

    def tearDown(self):
        self.sandbox_dir.cleanup()

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_swarm_self_correction_loop(self, mock_get_llm):
        # We simulate a stateful local LLM call sequence
        # Call 1: Architect planning
        # Call 2: Coder first attempt (buggy: return a - b)
        # Call 3: Coder second attempt after error feedback (corrected: return a + b)
        call_count = 0

        def stateful_mock_llm(prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # 1. Architect call
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "Create a math utility with addition.",
                    "tasks": [
                        {
                            "filepath": "math_utils.py",
                            "instructions": "Define an add(a, b) function."
                        }
                    ]
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            
            # 2. Coder call
            elif "Coder" in prompt or "add(a, b)" in prompt:
                # If coder sees previous warning in prompt, return the fix
                if "Warning: Previous test failed" in prompt or "TESTS FAILED" in prompt:
                    correct_code = "def add(a, b):\n    return a + b\n"
                    return {"choices": [{"text": correct_code}]}
                else:
                    # Buggy implementation first (subtraction instead of addition)
                    buggy_code = "def add(a, b):\n    return a - b\n"
                    return {"choices": [{"text": buggy_code}]}
            
            # Catch-all
            return {"choices": [{"text": ""}]}

        # Register the stateful mock
        mock_llm_callable = MagicMock(side_effect=stateful_mock_llm)
        mock_get_llm.return_value = mock_llm_callable

        # Instantiate orchestrator targeting sandbox
        objective = "Create an add function in math_utils.py"
        test_command = f"{sys.executable} run_tests.py"
        
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective=objective,
            test_command=test_command
        )

        # Track signals emitted
        signals = {
            "status_messages": [],
            "plan": None,
            "edited_files": {},
            "test_results": [],
            "finished": None
        }

        orchestrator.status_update.connect(lambda msg: signals["status_messages"].append(msg))
        orchestrator.task_plan_created.connect(lambda plan: signals.update({"plan": plan}))
        orchestrator.file_edited.connect(lambda path, content: signals["edited_files"].update({path: content}))
        orchestrator.test_result.connect(lambda passed, trace: signals["test_results"].append((passed, trace)))
        orchestrator.finished_swarm.connect(lambda success, summary: signals.update({"finished": (success, summary)}))
        orchestrator.edits_proposed.connect(lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals]))

        # Run QThread synchronously in test thread to simplify assertions
        orchestrator.run()

        # --- ASSERTIONS ---
        # Verify Architect planned properly
        self.assertIsNotNone(signals["plan"])
        self.assertEqual(signals["plan"]["tasks"][0]["filepath"], "math_utils.py")

        # Verify Coder created 'math_utils.py'
        self.assertIn("math_utils.py", signals["edited_files"])

        # Verify the self-correction cycle:
        # - Attempt 1 failed (2 - 3 = -1, not 5)
        # - Attempt 2 succeeded (2 + 3 = 5)
        # Therefore, we should have two test runs: first False, then True
        self.assertEqual(len(signals["test_results"]), 2)
        self.assertFalse(signals["test_results"][0][0])  # First test run failed
        self.assertTrue(signals["test_results"][1][0])   # Second test run passed

        # Verify final code is correct
        final_code = signals["edited_files"]["math_utils.py"]
        self.assertIn("return a + b", final_code)

        # Verify final orchestrator status
        self.assertIsNotNone(signals["finished"])
        self.assertTrue(signals["finished"][0])  # Success is True
        self.assertIn("math_utils.py", signals["finished"][1])  # Summary names modified file

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_swarm_parallel_execution(self, mock_get_llm):
        # We simulate a stateful LLM to return Architect plan then Coder edits
        def stateful_mock_llm(prompt, **kwargs):
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "Create two independent helper files.",
                    "tasks": [
                        {
                            "filepath": "math_utils.py",
                            "instructions": "Define an add(a, b) function."
                        },
                        {
                            "filepath": "string_utils.py",
                            "instructions": "Define a reverse(s) function."
                        }
                    ]
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            elif "math_utils.py" in prompt:
                return {"choices": [{"text": "def add(a, b):\n    return a + b\n"}]}
            elif "string_utils.py" in prompt:
                return {"choices": [{"text": "def reverse(s):\n    return s[::-1]\n"}]}
            return {"choices": [{"text": ""}]}

        mock_llm_callable = MagicMock(side_effect=stateful_mock_llm)
        mock_get_llm.return_value = mock_llm_callable

        objective = "Create math_utils.py and string_utils.py"
        test_command = "echo 'tests passed'"

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective=objective,
            test_command=test_command
        )

        signals = {
            "status_messages": [],
            "plan": None,
            "layers": None,
            "edited_files": {},
            "finished": None
        }

        orchestrator.status_update.connect(lambda msg: signals["status_messages"].append(msg))
        orchestrator.task_plan_created.connect(lambda plan: signals.update({"plan": plan}))
        orchestrator.dependency_layers_built.connect(lambda layers: signals.update({"layers": layers}))
        orchestrator.file_edited.connect(lambda path, content: signals["edited_files"].update({path: content}))
        orchestrator.finished_swarm.connect(lambda success, summary: signals.update({"finished": (success, summary)}))
        orchestrator.edits_proposed.connect(lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals]))

        orchestrator.run()

        # Check that we parsed imports and sorted into 1 layer of 2 parallel tasks
        self.assertIsNotNone(signals["plan"])
        self.assertEqual(len(signals["plan"]["tasks"]), 2)
        self.assertIsNotNone(signals["layers"])
        self.assertEqual(len(signals["layers"]), 1)
        self.assertEqual(len(signals["layers"][0]), 2)
        self.assertIn("math_utils.py", signals["edited_files"])
        self.assertIn("string_utils.py", signals["edited_files"])
        self.assertIsNotNone(signals["finished"])
        self.assertTrue(signals["finished"][0])


if __name__ == "__main__":
    unittest.main()
