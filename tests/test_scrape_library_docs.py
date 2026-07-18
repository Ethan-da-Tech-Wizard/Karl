"""Tests for tools/scrape_library_docs.py — library signature scraping and
LLM-driven instruction/response synthesis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
for _path in (str(ROOT), str(TOOLS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import scrape_library_docs as m  # noqa: E402


class TestScrapePackage(unittest.TestCase):
    def test_scrapes_real_installed_package(self):
        results = m.scrape_package("requests", max_examples=12)

        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 12)
        for entry in results:
            self.assertEqual(entry["package"], "requests")
            self.assertTrue(entry["qualname"])
            self.assertTrue(entry["docstring"])
            self.assertIn(entry["kind"], {"function", "class", "method"})

    def test_prioritizes_functions_before_exception_classes(self):
        results = m.scrape_package("requests", max_examples=15)
        kinds_in_order = [r["kind"] for r in results]
        first_class_index = kinds_in_order.index("class") if "class" in kinds_in_order else len(kinds_in_order)
        # requests.get/.post/etc. are top-level functions and should be
        # collected before the alphabetically-earlier exception classes.
        function_names = {r["qualname"] for r in results[:first_class_index]}
        self.assertTrue({"get", "post"} & function_names)

    def test_returns_empty_list_for_unimportable_package(self):
        results = m.scrape_package("definitely_not_a_real_package_xyz")
        self.assertEqual(results, [])

    def test_skips_undocumented_members(self):
        results = m.scrape_package("requests", max_examples=50)
        for entry in results:
            self.assertTrue(entry["docstring"].strip())


class TestMetaPromptAndParsing(unittest.TestCase):
    def test_build_meta_prompt_includes_signature_and_docstring(self):
        entry = {
            "package": "numpy", "qualname": "arange", "kind": "function",
            "signature": "(start, stop, step)", "docstring": "Return evenly spaced values.",
        }
        prompt = m._build_meta_prompt(entry)
        self.assertIn("numpy", prompt)
        self.assertIn("arange", prompt)
        self.assertIn("Return evenly spaced values.", prompt)
        self.assertIn("INSTRUCTION:", prompt)

    def test_truncates_long_docstrings(self):
        entry = {
            "package": "x", "qualname": "y", "kind": "function",
            "signature": "()", "docstring": "z" * 5000,
        }
        prompt = m._build_meta_prompt(entry)
        self.assertLess(len(prompt), 3000)

    def test_parse_llm_output_extracts_instruction_and_response(self):
        raw = (
            "INSTRUCTION: How do I use arange?\n"
            "RESPONSE:\n"
            "```python\nimport numpy as np\nnp.arange(5)\n```"
        )
        pair = m._parse_llm_output(raw)
        self.assertIsNotNone(pair)
        instruction, response = pair
        self.assertEqual(instruction, "How do I use arange?")
        self.assertIn("np.arange(5)", response)

    def test_parse_llm_output_returns_none_when_markers_missing(self):
        self.assertIsNone(m._parse_llm_output("just some free text, no markers"))

    def test_parse_llm_output_returns_none_on_empty_instruction(self):
        raw = "INSTRUCTION:   \nRESPONSE:\n```python\nx = 1\n```"
        self.assertIsNone(m._parse_llm_output(raw))


class TestGenerateSftQa(unittest.TestCase):
    @patch("scrape_library_docs.ModelLoader.get_instance")
    def test_builds_sft_row_from_well_formed_output(self, mock_get_instance):
        mock_llm = MagicMock(return_value={"choices": [{"text": (
            "INSTRUCTION: How do I create a range using numpy.arange?\n"
            "RESPONSE:\n```python\nimport numpy as np\narr = np.arange(0, 10, 2)\n```"
        )}]})
        mock_get_instance.return_value = mock_llm

        entry = {
            "package": "numpy", "qualname": "arange", "kind": "function",
            "signature": "(start, stop, step)", "docstring": "Return evenly spaced values.",
        }
        row = m.generate_sft_qa(entry)

        self.assertIsNotNone(row)
        self.assertEqual(row["source"], "library_scrape")
        self.assertEqual(row["package"], "numpy")
        self.assertEqual(row["qualname"], "arange")
        messages = row["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("arange", messages[1]["content"])
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertIn("np.arange(0, 10, 2)", messages[2]["content"])

    @patch("scrape_library_docs.ModelLoader.get_instance")
    def test_returns_none_when_output_unparsable(self, mock_get_instance):
        mock_llm = MagicMock(return_value={"choices": [{"text": "not in the expected format at all"}]})
        mock_get_instance.return_value = mock_llm

        entry = {"package": "numpy", "qualname": "arange", "kind": "function", "signature": "()", "docstring": "doc"}
        row = m.generate_sft_qa(entry)

        self.assertIsNone(row)

    @patch("scrape_library_docs.ModelLoader.get_instance", side_effect=RuntimeError("no model loaded"))
    def test_returns_none_when_model_load_fails(self, _mock):
        entry = {"package": "numpy", "qualname": "arange", "kind": "function", "signature": "()", "docstring": "doc"}
        row = m.generate_sft_qa(entry)
        self.assertIsNone(row)

    @patch("scrape_library_docs.ModelLoader.get_instance")
    def test_returns_none_when_llm_call_raises(self, mock_get_instance):
        mock_llm = MagicMock(side_effect=RuntimeError("generation failed"))
        mock_get_instance.return_value = mock_llm

        entry = {"package": "numpy", "qualname": "arange", "kind": "function", "signature": "()", "docstring": "doc"}
        row = m.generate_sft_qa(entry)
        self.assertIsNone(row)


if __name__ == "__main__":
    unittest.main()
