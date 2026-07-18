#!/usr/bin/env python3
"""Download and format a public programming instruction dataset for Karl fine-tuning."""

from __future__ import annotations

import ast
import json
import logging
import re
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("karl.download_public_sft")

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data/training/code/public_code_sft.jsonl"


def is_python_code(text: str) -> bool:
    """Return True if the text contains syntactically valid Python code."""
    # Find code blocks if present
    code_blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    snippets = code_blocks if code_blocks else [text]
    for snippet in snippets:
        try:
            ast.parse(snippet)
            return True
        except SyntaxError:
            continue
    return False


def main() -> int:
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("HuggingFace 'datasets' library is not installed. Install requirements.txt first.")
        return 1

    logger.info("Downloading sahil2801/CodeAlpaca-20k from HuggingFace...")
    try:
        dataset = load_dataset("sahil2801/CodeAlpaca-20k", split="train")
    except Exception as exc:
        logger.error("Failed to download dataset: %s", exc)
        return 1

    logger.info("Filtering and formatting programming instructions...")
    formatted_count = 0
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_PATH.open("w", encoding="utf-8") as fh:
        for item in dataset:
            instruction = item.get("instruction", "")
            input_context = item.get("input", "")
            output = item.get("output", "")

            # Ensure we are capturing Python programming queries
            is_python = (
                "python" in instruction.lower()
                or "python" in input_context.lower()
                or is_python_code(output)
            )
            if not is_python:
                continue

            user_content = instruction
            if input_context:
                user_content += f"\n\nInput Context:\n{input_context}"

            # Format to conversational system/user/assistant block
            sft_entry = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Python software engineer. Prioritise correctness, "
                            "idiomatic style, and minimal complexity."
                        )
                    },
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": output}
                ],
                "source": "public_codealpaca"
            }

            fh.write(json.dumps(sft_entry, ensure_ascii=False) + "\n")
            formatted_count += 1

    logger.info("Successfully wrote %d SFT examples to %s", formatted_count, OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
