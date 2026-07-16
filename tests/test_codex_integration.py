import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interaction_loop import strip_html_tags, matches_keyword, build_prompt
from core.default_prompts import DEFAULT_SYSTEM_PROMPT

class TestCodexIntegration(unittest.TestCase):
    def test_strip_html_tags(self):
        html_input = """
        <h2 style='color:#00C2FF;'>⚡ FastAPI</h2>
        <p>A fast web framework.</p>
        <pre>
        from fastapi import FastAPI
        app = FastAPI()
        </pre>
        """
        expected_output = (
            "⚡ FastAPI\n\n"
            "A fast web framework.\n\n"
            "from fastapi import FastAPI\n"
            "app = FastAPI()"
        )
        stripped = strip_html_tags(html_input)
        self.assertEqual(stripped, expected_output)

    def test_matches_keyword_word_boundaries(self):
        # Test C++ matching
        self.assertTrue(matches_keyword("I write C++ code", "c++"))
        self.assertTrue(matches_keyword("cpp developer needed", "cpp"))
        
        # Test React matching
        self.assertTrue(matches_keyword("using React hooks", "react"))
        self.assertFalse(matches_keyword("that is a reactive system", "react"))
        
        # Test C matching (must not match C++ or C#)
        self.assertTrue(matches_keyword("I program in C.", "c"))
        self.assertFalse(matches_keyword("I program in C++.", "c"))
        self.assertFalse(matches_keyword("I program in C#.", "c"))
        self.assertFalse(matches_keyword("A cat is here.", "c"))

    def test_build_prompt_codex_injection(self):
        # We need to make sure data/codex_library exists for this test,
        # or we can mock/write temp files if we want, but since they are seeded,
        # let's just make sure there is a mocked/real file on disk.
        # Let's write a mock file under data/codex_library/TestTopic.html
        os.makedirs("data/codex_library", exist_ok=True)
        mock_file_path = "data/codex_library/Python.html"
        
        # Keep track of original content if it exists
        original_content = None
        if os.path.exists(mock_file_path):
            with open(mock_file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

        try:
            # Seed a simple content for the test
            with open(mock_file_path, "w", encoding="utf-8") as f:
                f.write("<h2>Python Guide</h2><p>Advanced decorators and generator loops.</p>")

            # Test prompt compilation when keyword matches
            chat_history = [
                {"role": "user", "content": "How do I use python decorators?"}
            ]
            prompt = build_prompt("", chat_history)
            
            # Since "python" is matched, Python guide should be injected
            self.assertIn("Codex Reference Context:", prompt)
            self.assertIn("[Python]", prompt)
            self.assertIn("Python Guide", prompt)
            self.assertIn("Advanced decorators and generator loops.", prompt)

            # Test prompt compilation when NO keyword matches
            chat_history_no_match = [
                {"role": "user", "content": "Hello there, what is your name?"}
            ]
            prompt_no_match = build_prompt("", chat_history_no_match)
            self.assertNotIn("Codex Reference Context:", prompt_no_match)

        finally:
            # Restore original content
            if original_content is not None:
                with open(mock_file_path, "w", encoding="utf-8") as f:
                    f.write(original_content)

    def test_build_prompt_limits(self):
        # Verify safety limit is enforced (at most 2 sheets)
        os.makedirs("data/codex_library", exist_ok=True)
        files_to_seed = ["Python.html", "React.html", "Rust.html"]
        originals = {}
        for f_name in files_to_seed:
            path = os.path.join("data/codex_library", f_name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    originals[f_name] = f.read()
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"<h2>{f_name.split('.')[0]} Guide</h2>")

        try:
            chat_history = [
                {"role": "user", "content": "I want to learn python, react and rust."}
            ]
            prompt = build_prompt("", chat_history)
            
            # Check how many guides are in the prompt
            count = 0
            if "[Python]" in prompt:
                count += 1
            if "[React]" in prompt:
                count += 1
            if "[Rust]" in prompt:
                count += 1
                
            # It should have matched at most 2 due to the safety limit
            self.assertLessEqual(count, 2)
            self.assertGreaterEqual(count, 1)

        finally:
            # Restore originals
            for f_name, content in originals.items():
                path = os.path.join("data/codex_library", f_name)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

    def test_build_prompt_greetings_and_reasoning(self):
        # 1. Test greeting input: should NOT pre-seed <think> and should use clean system prompt
        greeting_history = [{"role": "user", "content": "hello there"}]
        prompt_greeting = build_prompt(DEFAULT_SYSTEM_PROMPT, greeting_history)
        self.assertNotIn("<think>", prompt_greeting)
        self.assertNotIn("think step-by-step", prompt_greeting)

        # 2. Test reasoning query input: should pre-seed <think>
        reasoning_history = [{"role": "user", "content": "explain how decorators work in python"}]
        prompt_reasoning = build_prompt(DEFAULT_SYSTEM_PROMPT, reasoning_history)
        self.assertIn("<think>", prompt_reasoning)
        self.assertIn("think step-by-step", prompt_reasoning)

if __name__ == "__main__":
    unittest.main()
