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
import importlib.util
import tempfile
import unittest
import shutil
from unittest.mock import patch, MagicMock

from PyQt6.QtCore import QCoreApplication
from app.engine.hot_reload import compile_and_reload
from app.engine.model_loader import ModelLoader
from app.engine.llm_thread import LLMThread
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

    @unittest.skipIf(shutil.which("rg") is None, "ripgrep (rg) not installed on this system")
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

    def test_hot_reload_keeps_previous_module_on_compile_error(self):
        module_path = os.path.join(self.workspace_path, "hackable_module.py")
        with open(module_path, "w", encoding="utf-8") as f:
            f.write("VALUE = 1\n")

        spec = importlib.util.spec_from_file_location("hackable_module_test", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        notices = []
        with open(module_path, "w", encoding="utf-8") as f:
            f.write("VALUE = \n")

        kept = compile_and_reload(module, "hackable_module.py", notices.append)
        self.assertIs(kept, module)
        self.assertEqual(kept.VALUE, 1)
        self.assertTrue(any("blocked by compile error" in notice for notice in notices))

    def test_llm_trim_history_uses_tokenizer_counts(self):
        class TokenDenseMock:
            def tokenize(self, text_bytes, add_bos=False):
                text = text_bytes.decode("utf-8")
                return [0] * len(text)

        original_n_ctx = ModelLoader.n_ctx
        ModelLoader.n_ctx = lambda: 1200
        try:
            thread = LLMThread(
                system_prompt="system",
                chat_history=[],
                hyperparams={},
            )
            history = [
                {"role": "user", "content": "seed"},
                {"role": "assistant", "content": "old" * 100},
                {"role": "user", "content": "recent"},
            ]
            kept = thread._trim_history(history, TokenDenseMock(), "system")
        finally:
            ModelLoader.n_ctx = original_n_ctx

        self.assertEqual(kept[0]["content"], "seed")
        self.assertEqual(kept[-1]["content"], "recent")
        self.assertNotIn("old" * 100, [item["content"] for item in kept])

    def test_orchestrator_rejects_unsafe_task_paths(self):
        orchestrator = SwarmOrchestratorThread(
            workspace_path=self.workspace_path,
            objective="unsafe plan",
            test_command="true",
        )

        with self.assertRaises(ValueError):
            orchestrator._validate_tasks([
                {"filepath": "../outside.py", "instructions": "write outside"}
            ])

        with self.assertRaises(ValueError):
            orchestrator._validate_tasks([
                {"filepath": os.path.join(self.workspace_path, "absolute.py"), "instructions": "write absolute"}
            ])

        with self.assertRaises(ValueError):
            orchestrator._validate_tasks([
                {"filepath": "pkg/../safe.py", "instructions": "ambiguous normalized path"}
            ])

        tasks = orchestrator._validate_tasks([
            {"filepath": "pkg/safe.py", "instructions": "write safe"}
        ])
        self.assertEqual(tasks[0]["filepath"], "pkg/safe.py")

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
        orchestrator.edits_proposed.connect(lambda proposals: orchestrator.commit_selected_edits([p["filepath"] for p in proposals]))

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

    def test_proc_maps_page_privacy(self):
        """Test Target 1: Memory Page Sharing Verification.
        Reads /proc/self/maps and asserts that all writable memory segments are private ('p'),
        not shared ('s').
        """
        if sys.platform != "linux":
            self.skipTest("Memory page privacy check is only relevant on Linux")

        maps_path = "/proc/self/maps"
        self.assertTrue(os.path.exists(maps_path), "proc maps file does not exist")

        with open(maps_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    perms = parts[1]
                    if 'w' in perms:
                        # Ignore system device drivers under /dev/ (like GPU buffers /dev/nvidia0), but keep checking /dev/shm
                        pathname = parts[5] if len(parts) >= 6 else ""
                        if pathname.startswith("/dev/") and not pathname.startswith("/dev/shm/"):
                            continue
                        if pathname.startswith("/dev/shm/sem."):
                            continue
                        if pathname.endswith("-shm") or ".db-shm" in pathname:
                            continue
                        # Ensure writable pages are private, not shared
                        self.assertNotIn('s', perms, f"Found shared writable segment: {line.strip()}")
                        self.assertIn('p', perms, f"Found non-private writable segment: {line.strip()}")

    def test_kernel_keyring_expiry_and_revocation(self):
        """Test Target 2: Keyring Expiry & Revocation Verification.
        Verifies that storing a token, auto-expiry, and explicit revocation behave correctly in the kernel.
        """
        if sys.platform != "linux":
            self.skipTest("Linux kernel keyring is only available on Linux")

        from app.utils.keychain_manager import store_session_token, revoke_session_token, _libkeyutils
        import ctypes
        import errno
        import time

        _SYS_KEYCTL = 250

        # Define keyctl_read helper using either libkeyutils or raw syscall
        def read_session_token(key_id: int) -> str:
            if _libkeyutils is not None:
                _libkeyutils.keyctl_read.argtypes = [ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
                _libkeyutils.keyctl_read.restype = ctypes.c_int32
                needed = _libkeyutils.keyctl_read(key_id, None, 0)
                if needed < 0:
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))
                buf = ctypes.create_string_buffer(needed)
                read_bytes = _libkeyutils.keyctl_read(key_id, buf, needed)
                if read_bytes < 0:
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))
                return buf.value.decode('utf-8')
            else:
                libc = ctypes.CDLL(None, use_errno=True)
                sc = libc.syscall
                sc.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
                sc.restype = ctypes.c_long
                
                # Subcommand KEYCTL_READ is 11
                needed = sc(_SYS_KEYCTL, 11, key_id, None, 0)
                if needed < 0:
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))
                buf = ctypes.create_string_buffer(needed)
                read_bytes = sc(_SYS_KEYCTL, 11, key_id, buf, needed)
                if read_bytes < 0:
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))
                return buf.value.decode('utf-8')

        # 1. Store test token with 2-second timeout
        test_token = "verification-session-token-123"
        key_id = store_session_token(test_token, 2)
        self.assertIsInstance(key_id, int)
        self.assertGreater(key_id, 0)

        # 2. Read back and verify it matches
        val = read_session_token(key_id)
        self.assertEqual(val, test_token)

        # 3. Wait 3 seconds and confirm it expires with OSError (EKEYEXPIRED or ENOKEY)
        time.sleep(3)
        with self.assertRaises(OSError) as context:
            read_session_token(key_id)
        self.assertIn(context.exception.errno, (errno.ENOKEY, errno.EKEYEXPIRED))

        # 4. Store a second token, revoke immediately, confirm failure with OSError (EKEYREVOKED or ENOKEY)
        key_id_2 = store_session_token("revocation-test-token-456", 60)
        self.assertGreater(key_id_2, 0)
        
        # Verify it exists first
        self.assertEqual(read_session_token(key_id_2), "revocation-test-token-456")
        
        # Revoke
        revoke_session_token(key_id_2)
        
        with self.assertRaises(OSError) as context:
            read_session_token(key_id_2)
        self.assertIn(context.exception.errno, (errno.ENOKEY, errno.EKEYREVOKED))


if __name__ == "__main__":
    unittest.main()
