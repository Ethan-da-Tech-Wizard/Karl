#!/usr/bin/env python3
"""
LoRA Adapter Evaluation & Performance Benchmark
===============================================
Loads an evaluation suite, tests baseline models vs. adapter models, and logs
differences in syntax accuracy (AST validation) and generation speed (TPS).
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("karl.evaluate_adapters")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.model_loader import ModelLoader

# Default mock tasks if evaluation files are missing
FALLBACK_TASKS = [
    {
        "instruction": "Write a python function to check if a number is prime.",
        "test_code": "def check_prime(n):\n    if n < 2: return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0: return False\n    return True"
    },
    {
        "instruction": "Write a python class representing a 2D Vector with x and y coordinates.",
        "test_code": "class Vector2D:\n    def __init__(self, x, y):\n        self.x = x\n        self.y = y"
    },
    {
        "instruction": "Write a python function to compute the factorial of a number using recursion.",
        "test_code": "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"
    }
]


def extract_code_block(text: str) -> str:
    """Extract code block wrapped in triple backticks."""
    import re
    match = re.search(r"```(?:python)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    return (match.group(1) if match else text).strip()


def evaluate_model_performance(
    adapter_name: Optional[str] = None,
    dataset_path: Optional[str] = None,
    limit: int = 10
) -> dict[str, Any]:
    """
    Runs generations across a benchmark dataset and returns performance statistics.
    """
    # Reset and reload the model with the specified adapter name
    ModelLoader.reset_instance()
    llm = ModelLoader.get_instance(adapter_name=adapter_name)
    
    # Load dataset
    tasks = []
    if dataset_path and os.path.exists(dataset_path):
        try:
            with open(dataset_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        tasks.append(json.loads(line))
        except Exception as exc:
            logger.warning("Could not read dataset: %s. Using mock fallback.", exc)
            tasks = FALLBACK_TASKS
    else:
        tasks = FALLBACK_TASKS
        
    tasks = tasks[:limit]
    
    eval_cases = 0
    total_tps = 0.0
    syntax_passed = 0
    
    for idx, task in enumerate(tasks, 1):
        instruction = task.get("instruction") or task.get("prompt") or ""
        if not instruction:
            continue
            
        eval_cases += 1
        prompt = f"<|im_start|>user\n{instruction}<|im_end|>\n<|im_start|>assistant\n<think>\n"
        
        start_time = time.perf_counter()
        
        # Call the local model
        chunks = []
        for chunk in llm(
            prompt,
            max_tokens=512,
            temperature=0.2,
            top_p=0.95,
            stream=True,
            stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"]
        ):
            if "choices" in chunk and chunk["choices"]:
                chunks.append(chunk["choices"][0].get("text", ""))
        
        elapsed = time.perf_counter() - start_time
        raw_output = "".join(chunks)
        
        # Tokenize using model tokenizer to get exact count
        try:
            tokens = llm.tokenize(raw_output.encode("utf-8"))
            token_count = len(tokens)
        except Exception:
            token_count = len(raw_output.split())
            
        tps = token_count / max(elapsed, 0.001)
        total_tps += tps
        
        # Check syntax accuracy
        code_block = extract_code_block(raw_output)
        try:
            ast.parse(code_block)
            syntax_passed += 1
        except SyntaxError:
            pass
            
    # Clean up model resources
    ModelLoader.reset_instance()
    
    # Estimate memory footprint
    vram_mb = 0.0
    if adapter_name:
        adapter_path = ModelLoader._adapter_path(adapter_name)
        if adapter_path and os.path.exists(adapter_path):
            vram_mb = os.path.getsize(adapter_path) / (1024 * 1024)
            
    avg_tps = total_tps / max(eval_cases, 1)
    syntax_accuracy = (syntax_passed / max(eval_cases, 1)) * 100.0
    
    return {
        "adapter": adapter_name,
        "eval_cases": eval_cases,
        "avg_tps": round(avg_tps, 2),
        "syntax_accuracy": round(syntax_accuracy, 2),
        "vram_delta_mb": round(vram_mb, 2)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate code accuracy and inference speed delta for adapters.")
    parser.add_argument("--adapter", required=True, help="Directory name of the target adapter inside data/adapters/")
    parser.add_argument("--dataset", default=None, help="Evaluation dataset JSONL path")
    parser.add_argument("--limit", type=int, default=3, help="Number of test samples to run")
    args = parser.parse_args()

    logger.info("Evaluating baseline performance...")
    baseline_stats = evaluate_model_performance(adapter_name=None, dataset_path=args.dataset, limit=args.limit)
    
    logger.info("Evaluating adapter performance for '%s'...", args.adapter)
    adapter_stats = evaluate_model_performance(adapter_name=args.adapter, dataset_path=args.dataset, limit=args.limit)
    
    report = {
        "adapter_name": args.adapter,
        "baseline": baseline_stats,
        "adapted": adapter_stats,
        "tps_improvement_percent": round(
            ((adapter_stats["avg_tps"] - baseline_stats["avg_tps"]) / max(baseline_stats["avg_tps"], 0.1)) * 100.0,
            2
        ),
        "accuracy_improvement_percent": round(
            adapter_stats["syntax_accuracy"] - baseline_stats["syntax_accuracy"],
            2
        )
    }
    
    out_dir = ROOT / "data" / "adapters"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"eval_report_{args.adapter}.json"
    
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        
    logger.info("Evaluation report successfully written to %s", out_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
