import json
import ast

from tools.generate_self_correction_dataset import (
    CodingProblem,
    build_correction_prompt,
    build_self_correction_row,
    code_diff,
    extract_code_block,
    extract_thought_block,
    normalize_problem_record,
)
from tools.generate_code_sft_dataset import DefinitionVisitor, build_user_prompt


def test_normalize_problem_record_accepts_verifiable_task():
    record = {
        "id": "task-1",
        "problem_statement": "Write solve(x).",
        "verification_script": "def verify(response): return True",
        "code": "def solve(x): pass",
    }

    problem = normalize_problem_record(record)

    assert problem is not None
    assert problem.problem_id == "task-1"
    assert "Write solve" in problem.prompt
    assert "Context/code" in problem.prompt
    assert problem.verification_script.startswith("def verify")


def test_normalize_problem_record_rejects_missing_verifier():
    assert normalize_problem_record({"prompt": "Write code"}) is None


def test_extract_code_and_thought_blocks():
    text = "<think>\nfix off by one\n</think>\n```python\ndef solve():\n    return 1\n```"

    assert extract_thought_block(text) == "fix off by one"
    assert extract_code_block(text) == "def solve():\n    return 1"


def test_code_diff_tracks_correction():
    before = "```python\ndef solve():\n    return 1\n```"
    after = "```python\ndef solve():\n    return 2\n```"

    diff = code_diff(before, after)

    assert "--- failed_attempt.py" in diff
    assert "+++ corrected_attempt.py" in diff
    assert "-    return 1" in diff
    assert "+    return 2" in diff


def test_build_self_correction_row_format():
    problem = CodingProblem(
        problem_id="p1",
        prompt="Return 2.",
        verification_script="def verify(response): return '2' in response",
    )
    attempts = [
        {
            "iteration": 1,
            "thought": "try one",
            "response": "```python\ndef solve():\n    return 1\n```",
            "raw": "<think>try one</think>",
            "passed": False,
            "trace": "AssertionError",
        },
        {
            "iteration": 2,
            "thought": "fix constant",
            "response": "```python\ndef solve():\n    return 2\n```",
            "raw": "<think>fix constant</think>",
            "passed": True,
            "trace": "",
        },
    ]

    row = build_self_correction_row(problem, attempts)

    assert row["origin"] == "self_correction_star"
    assert row["iterations"] == 2
    assert row["messages"][0]["role"] == "system"
    assert row["messages"][1]["role"] == "user"
    assert row["messages"][2]["role"] == "assistant"
    assistant = row["messages"][2]["content"]
    assert "<think>" in assistant
    assert "correction_diff" in assistant
    assert "+    return 2" in assistant
    json.loads(assistant.split("```json\n", 1)[1].split("\n```", 1)[0])


def test_build_correction_prompt_includes_traceback():
    problem = CodingProblem("p1", "Write solve().", "def verify(response): return False")

    prompt = build_correction_prompt(problem, "bad response", "NameError: solve")

    assert "bad response" in prompt
    assert "NameError: solve" in prompt
    assert "<think>" in prompt


def test_code_scrape_docstring_parsing_feeds_prompt_formatting():
    source = '''
def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b
'''
    tree = ast.parse(source)
    visitor = DefinitionVisitor(source, "pkg/math_utils.py")
    visitor.visit(tree)

    assert len(visitor.definitions) == 1
    entry = visitor.definitions[0]
    assert entry["docstring"] == "Return the sum of two integers."
    assert entry["args"] == "a: int, b: int"
    assert entry["returns"] == "int"
    prompt = build_user_prompt(entry)
    assert "Return the sum of two integers." in prompt
    assert "pkg/math_utils.py" in prompt
