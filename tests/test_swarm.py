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

from app.engine.swarm_orchestrator import SwarmOrchestratorThread, rollback_swarm_run


class TestSwarmOrchestrator(unittest.TestCase):
    def setUp(self):
        # Create a temporary sandbox directory for code editing and testing
        self.sandbox_dir = tempfile.TemporaryDirectory()
        self.workspace_path = self.sandbox_dir.name

        # Patch config_store to disable machine speak in tests to avoid prompt compaction
        self.config_patcher = patch("app.engine.config_store.get_ui_config")
        self.mock_get_ui_config = self.config_patcher.start()
        self.mock_get_ui_config.return_value = {
            "enable_machine_speak": False,
            "theme_preset": "Karl Obsidian Core",
            "layout_preset": "Focused Workbench",
        }

        # Create dummy python test script in the workspace that asserts add(2, 3) == 5
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
        self.config_patcher.stop()
        self.sandbox_dir.cleanup()

    def test_generated_smoke_suite_passes_without_test_command(self):
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create a helper module.",
            test_command=""
        )

        passed, trace = orchestrator._verify_proposals_in_temp_workspace(
            [{"filepath": "helper.py", "content": "def ok():\n    return True\n"}],
            layer_index=1,
        )

        self.assertTrue(passed)
        self.assertIn("GENERATED SMOKE TEST PASSED", trace)
        self.assertFalse(os.path.exists(os.path.join(self.workspace_path, "helper.py")))

    def test_generated_smoke_suite_fails_on_python_syntax_error(self):
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create a helper module.",
            test_command=""
        )

        passed, trace = orchestrator._verify_proposals_in_temp_workspace(
            [{"filepath": "helper.py", "content": "def broken(:\n    pass\n"}],
            layer_index=1,
        )

        self.assertFalse(passed)
        self.assertIn("GENERATED SMOKE TEST FAILED", trace)
        self.assertIn("python compile failed", trace)

    def test_backup_workspace_file_preserves_existing_content(self):
        source_path = os.path.join(self.workspace_path, "existing.py")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("VALUE = 'before'\n")

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Update an existing file.",
            test_command=""
        )

        backup_path = orchestrator._backup_workspace_file("existing.py", orchestrator._resolve_task_path("existing.py")[1])

        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "VALUE = 'before'\n")
        self.assertIn(".karl_swarm_backups", backup_path)

    def test_rollback_swarm_run_restores_existing_file(self):
        source_path = os.path.join(self.workspace_path, "existing.py")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("VALUE = 'before'\n")

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Update an existing file.",
            test_command=""
        )
        backup_path = orchestrator._backup_workspace_file("existing.py", orchestrator._resolve_task_path("existing.py")[1])
        orchestrator._record_backup_manifest("existing.py", backup_path, True)
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("VALUE = 'after'\n")

        result = rollback_swarm_run(self.workspace_path, orchestrator._run_id)

        self.assertTrue(result["ok"])
        self.assertIn("existing.py", result["restored"])
        with open(source_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "VALUE = 'before'\n")

    def test_rollback_swarm_run_removes_new_file(self):
        new_path = os.path.join(self.workspace_path, "new_file.py")
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create a new file.",
            test_command=""
        )
        backup_path = orchestrator._backup_workspace_file("new_file.py", orchestrator._resolve_task_path("new_file.py")[1])
        orchestrator._record_backup_manifest("new_file.py", backup_path, False)
        with open(new_path, "w", encoding="utf-8") as f:
            f.write("VALUE = 'new'\n")

        result = rollback_swarm_run(self.workspace_path, orchestrator._run_id)

        self.assertTrue(result["ok"])
        self.assertIn("new_file.py", result["removed"])
        self.assertFalse(os.path.exists(new_path))

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

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_multiverse_candidates_default_to_one_unchanged_behavior(self, mock_get_llm):
        """candidates_per_task defaults to 1 -- no candidate/winner signals fire,
        and exactly one LLM call happens per phase, matching pre-Swarm-2.0 behavior."""
        call_count = 0

        def stateful_mock_llm(prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "x",
                    "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            return {"choices": [{"text": "def add(a, b):\n    return a + b\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command="echo ok",
        )
        signals = {"candidates": [], "winner": None, "finished": None}
        orchestrator.candidates_generated.connect(lambda fp, n: signals["candidates"].append((fp, n)))
        orchestrator.winner_selected.connect(lambda fp, i, r: signals.update({"winner": (fp, i, r)}))
        orchestrator.finished_swarm.connect(lambda s, summary: signals.update({"finished": (s, summary)}))
        orchestrator.edits_proposed.connect(
            lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
        )

        orchestrator.run()

        self.assertEqual(call_count, 2)  # exactly: 1 architect + 1 coder call
        self.assertEqual(signals["candidates"], [])  # no multiverse signal for a single candidate
        self.assertIsNone(signals["winner"])
        self.assertTrue(signals["finished"][0])

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_multiverse_selects_best_of_n_candidates(self, mock_get_llm):
        """candidates_per_task > 1 generates N candidates and the Judge picks
        the syntactically valid one over broken ones."""
        coder_call_count = 0

        def stateful_mock_llm(prompt, **kwargs):
            nonlocal coder_call_count
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "x",
                    "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            coder_call_count += 1
            # First two candidates are syntactically broken; only the third is valid.
            if coder_call_count < 3:
                return {"choices": [{"text": "def add(a, b)\n    return a + b\n"}]}
            return {"choices": [{"text": "def add(a, b):\n    return a + b\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command="echo ok",
            hyperparams={"candidates_per_task": 3},
        )
        signals = {"candidates": [], "scores": [], "winner": None, "finished": None}
        orchestrator.candidates_generated.connect(lambda fp, n: signals["candidates"].append((fp, n)))
        orchestrator.candidate_scored.connect(lambda fp, i, sc: signals["scores"].append((i, sc["syntax_ok"])))
        orchestrator.winner_selected.connect(lambda fp, i, r: signals.update({"winner": (fp, i, r)}))
        orchestrator.finished_swarm.connect(lambda s, summary: signals.update({"finished": (s, summary)}))
        orchestrator.edits_proposed.connect(
            lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
        )

        orchestrator.run()

        self.assertEqual(signals["candidates"], [("math_utils.py", 3)])
        self.assertEqual(len(signals["scores"]), 3)
        self.assertEqual(signals["scores"][0][1], False)  # candidate 0 broken
        self.assertEqual(signals["scores"][1][1], False)  # candidate 1 broken
        self.assertEqual(signals["scores"][2][1], True)   # candidate 2 valid
        self.assertEqual(signals["winner"][1], 2)          # winner is the valid one
        self.assertTrue(signals["finished"][0])

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_inject_guidance_reaches_the_coder_tool_loop(self, mock_get_llm):
        """inject_guidance() queues a message that surfaces as a user turn in
        the Coder's next tool-loop generation."""
        seen_prompts = []

        def stateful_mock_llm(prompt, **kwargs):
            seen_prompts.append(prompt)
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "x",
                    "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            if len(seen_prompts) == 2:
                # First coder turn: emit a tool call so the loop continues to a
                # second turn (where injected guidance should be visible).
                return {"choices": [{"text": (
                    "<reasoning>thinking</reasoning>"
                    "<tool_call name='read_file'>\n  path: math_utils.py\n</tool_call>"
                )}]}
            return {"choices": [{"text": "def add(a, b):\n    return a + b\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command="echo ok",
        )
        orchestrator.edits_proposed.connect(
            lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
        )
        # Guidance injected before the run starts is still queued and drained
        # on the coder's very first tool-loop turn check.
        orchestrator.inject_guidance("math_utils.py", "Use a docstring explaining the function.")

        orchestrator.run()

        matching = [p for p in seen_prompts if "Human guidance (mid-task correction)" in p]
        self.assertTrue(matching, "expected the injected guidance to appear in a later coder prompt")
        self.assertIn("docstring", matching[0])

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_drift_detector_injects_guidance_after_repeated_failure_trace(self, mock_get_llm):
        """The same syntax error twice in a row for one file should trip the
        drift detector and auto-inject corrective guidance."""
        def stateful_mock_llm(prompt, **kwargs):
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "x",
                    "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            # Always the same broken syntax, so the resulting trace repeats verbatim.
            return {"choices": [{"text": "def add(a, b\n    return a + b\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command="echo ok",
            hyperparams={"max_loops": 3, "timeout_seconds": 60},
        )
        orchestrator.edits_proposed.connect(
            lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
        )
        drift_events = []
        orchestrator.drift_detected.connect(lambda fp, msg: drift_events.append((fp, msg)))

        orchestrator.run()

        self.assertTrue(drift_events, "expected a drift alert after repeated identical syntax errors")
        self.assertEqual(drift_events[0][0], "math_utils.py")
        self.assertIn("Drift detected", drift_events[0][1])

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_max_loops_hyperparam_limits_layer_retries(self, mock_get_llm):
        """max_loops caps how many times a failing layer is retried."""
        def stateful_mock_llm(prompt, **kwargs):
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "x",
                    "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            # Always buggy (subtraction instead of addition), so verification keeps failing.
            return {"choices": [{"text": "def add(a, b):\n    return a - b\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command=f"{sys.executable} run_tests.py",
            hyperparams={"max_loops": 1},
        )
        orchestrator.edits_proposed.connect(
            lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
        )
        test_results = []
        orchestrator.test_result.connect(lambda passed, trace: test_results.append(passed))
        finished = {}
        orchestrator.finished_swarm.connect(lambda success, summary: finished.update({"success": success}))

        orchestrator.run()

        self.assertEqual(orchestrator.max_loops, 1)
        self.assertEqual(len(test_results), 1)  # no retry beyond the single allowed loop
        self.assertFalse(finished["success"])

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_execution_timeout_stops_gracefully(self, mock_get_llm):
        """A run whose deadline has already passed should stop before doing
        any layer work instead of hanging or crashing."""
        def stateful_mock_llm(prompt, **kwargs):
            plan = {
                "explanation": "x",
                "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
            }
            return {"choices": [{"text": json.dumps(plan)}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command="echo ok",
            hyperparams={"timeout_seconds": 30},
        )
        self.assertEqual(orchestrator.timeout_seconds, 30)

        finished = {}
        orchestrator.finished_swarm.connect(
            lambda success, summary: finished.update({"success": success, "summary": summary})
        )
        # Simulate the deadline already having elapsed, without depending on
        # real wall-clock time in the test.
        orchestrator._timed_out = lambda: True

        orchestrator.run()

        self.assertEqual(finished.get("success"), False)
        self.assertIn("timed out", finished.get("summary", "").lower())

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_coder_write_blocked_outside_task_plan(self, mock_get_llm):
        """write_file calls targeting a path outside allowed_paths must be
        blocked rather than silently written to the real workspace."""
        from app.engine.swarm_agents import CoderAgent

        def stateful_mock_llm(prompt, **kwargs):
            return {"choices": [{"text": (
                "<tool_call name='write_file'>\n"
                "  path: secret.py\n"
                "  content: pwned = True\n"
                "</tool_call>"
                "<tool_call name='done'></tool_call>"
            )}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        coder = CoderAgent()
        task = {"filepath": "math_utils.py", "instructions": "Define add(a, b)."}
        coder.generate(
            task, {}, workspace_path=self.workspace_path,
            allowed_paths={"math_utils.py"},
        )

        self.assertFalse(os.path.exists(os.path.join(self.workspace_path, "secret.py")))

    def test_step_unblocks_without_disabling_pause_mode(self):
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path, objective="x", test_command="",
            hyperparams={"pause_on_step": True},
        )
        orchestrator.pause_event.clear()
        self.assertTrue(orchestrator.pause_on_step)

        orchestrator.step()

        self.assertTrue(orchestrator.pause_event.is_set())
        self.assertTrue(orchestrator.pause_on_step)  # step() re-arms for the next boundary

    def test_resume_disables_pause_mode(self):
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path, objective="x", test_command="",
            hyperparams={"pause_on_step": True},
        )
        orchestrator.pause_event.clear()

        orchestrator.resume()

        self.assertTrue(orchestrator.pause_event.is_set())
        self.assertFalse(orchestrator.pause_on_step)

    def test_record_token_telemetry_emits_with_throttle(self):
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path, objective="x", test_command="",
        )
        events = []
        orchestrator.telemetry_update.connect(lambda payload: events.append(payload))

        for _ in range(7):
            orchestrator._record_token_telemetry()

        # Emits on the 1st call and every 5th call thereafter.
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["cumulative_tokens"], 1)
        self.assertEqual(events[1]["cumulative_tokens"], 5)
        self.assertIn("tokens_per_second", events[0])
        self.assertIn("elapsed_seconds", events[0])

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_pause_on_step_emits_and_resume_unblocks(self, mock_get_llm):
        def stateful_mock_llm(prompt, **kwargs):
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "x",
                    "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            return {"choices": [{"text": "def add(a, b):\n    return a + b\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command="echo ok",
            hyperparams={"pause_on_step": True},
        )
        orchestrator.edits_proposed.connect(
            lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
        )
        paused_events = []

        def _on_paused(info):
            paused_events.append(info)
            orchestrator.resume()

        orchestrator.swarm_paused.connect(_on_paused)
        orchestrator.run()

        self.assertTrue(paused_events)
        self.assertEqual(paused_events[0]["filepath"], "math_utils.py")
        self.assertEqual(paused_events[0]["layer_index"], 1)
        self.assertFalse(orchestrator.pause_on_step)  # resume() disabled further pausing

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_override_active_task_replaces_instructions(self, mock_get_llm):
        seen_prompts = []

        def stateful_mock_llm(prompt, **kwargs):
            seen_prompts.append(prompt)
            if "Architect" in prompt or "tasks" in prompt:
                plan = {
                    "explanation": "x",
                    "tasks": [{"filepath": "math_utils.py", "instructions": "Define an add(a, b) function."}],
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            return {"choices": [{"text": "def sub(a, b):\n    return a - b\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=stateful_mock_llm)

        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="Create an add function",
            test_command="echo ok",
            hyperparams={"pause_on_step": True},
        )
        orchestrator.edits_proposed.connect(
            lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
        )

        def _on_paused(info):
            orchestrator.override_active_task(info["filepath"], "Define a subtract(a, b) function instead.")
            orchestrator.resume()

        orchestrator.swarm_paused.connect(_on_paused)
        orchestrator.run()

        coder_prompts = [p for p in seen_prompts if "Task: Edit" in p]
        self.assertTrue(coder_prompts)
        self.assertIn("Define a subtract(a, b) function instead.", coder_prompts[0])


if __name__ == "__main__":
    unittest.main()
