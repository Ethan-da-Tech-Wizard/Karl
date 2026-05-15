"""
Eval Runner — karl_finetune
=============================
Runs evaluation prompts against a model (base or fine-tuned) and saves outputs.

Produces a JSONL results file for compare_outputs.py to diff.

Eval dataset format (data/eval.jsonl):
  {"id": "e001", "instruction": "...", "input": "...", "expected_keywords": ["sorry", "help"]}

Usage:
  python -m karl_finetune.run_eval configs/eval_config.json --mode base
  python -m karl_finetune.run_eval configs/eval_config.json --mode tuned
"""

import argparse
import json
import sys
import time
from pathlib import Path


def _check_deps():
    for pkg in ("torch", "transformers"):
        try:
            __import__(pkg)
        except ImportError:
            print(f"  ✗  Missing: {pkg}. Run: pip install torch transformers peft")
            sys.exit(1)


def _load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_prompt(instruction: str, input_text: str, template: str = "alpaca") -> str:
    if template == "alpaca":
        body = f"### Instruction:\n{instruction}"
        if input_text.strip():
            body += f"\n\n### Input:\n{input_text}"
        body += "\n\n### Response:\n"
        return body
    # chatml / default fallback
    user = instruction
    if input_text.strip():
        user += f"\n\n{input_text}"
    return (
        f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{user}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def run_eval(config_path: str, mode: str = "base") -> str:
    """
    Run eval prompts. mode='base' uses the base model; mode='tuned' loads the adapter.
    Returns path to the results JSONL.
    """
    _check_deps()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    cfg = _load_config(config_path)
    model_name  = cfg["model_name"]
    eval_file   = cfg.get("eval_file", "data/eval.jsonl")
    adapter_dir = cfg.get("adapter_dir", cfg.get("output_dir", "outputs/adapters/karl_lora"))
    template    = cfg.get("template", "alpaca")
    max_new     = cfg.get("max_new_tokens", 256)

    output_dir = Path(cfg.get("reports_dir", "outputs/reports"))
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / f"eval_{mode}.jsonl"

    print(f"\n{'─' * 60}")
    print(f"  Karl Eval Runner — mode: {mode}")
    print(f"  Model   : {model_name}")
    if mode == "tuned":
        print(f"  Adapter : {adapter_dir}")
    print(f"  Eval    : {eval_file}")
    print(f"{'─' * 60}\n")

    print("  Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("  Loading model...")
    model = AutoModelForCausalLM.from_pretrained(model_name)

    if mode == "tuned":
        from peft import PeftModel
        adapter_path = Path(adapter_dir)
        if not adapter_path.exists():
            print(f"  ✗  Adapter not found: {adapter_dir}")
            print("     Run training first: python -m karl_finetune.train_lora configs/finetune_config.json")
            sys.exit(1)
        print(f"  Loading LoRA adapter from {adapter_dir}...")
        model = PeftModel.from_pretrained(model, adapter_dir)

    model.eval()
    gen_pipeline = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_new,
        do_sample=False,
        temperature=1.0,
    )

    eval_cases = []
    with open(eval_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    eval_cases.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    print(f"  Running {len(eval_cases)} eval cases...\n")
    results = []

    for i, case in enumerate(eval_cases, 1):
        case_id     = case.get("id", f"eval_{i:03d}")
        instruction = case.get("instruction", "")
        input_text  = case.get("input", "")

        prompt = _build_prompt(instruction, input_text, template)

        t0 = time.time()
        raw = gen_pipeline(prompt)[0]["generated_text"]
        latency = round(time.time() - t0, 2)

        # Extract only the new text (after the prompt)
        output = raw[len(prompt):].strip()

        # Strip trailing stop tokens
        for stop in ["<|im_end|>", "### Instruction:", "### Input:"]:
            if stop in output:
                output = output.split(stop)[0].strip()

        results.append({
            "id":          case_id,
            "mode":        mode,
            "instruction": instruction,
            "input":       input_text,
            "output":      output,
            "latency_s":   latency,
            "expected_keywords": case.get("expected_keywords", []),
        })

        kw_hits = [k for k in case.get("expected_keywords", []) if k.lower() in output.lower()]
        kw_score = len(kw_hits) / len(case["expected_keywords"]) if case.get("expected_keywords") else None
        score_str = f"  kw={len(kw_hits)}/{len(case.get('expected_keywords', []))}" if kw_score is not None else ""
        print(f"  [{i}/{len(eval_cases)}] {case_id}  ({latency:.1f}s){score_str}")

    with open(results_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n  ✅  Results saved to {results_path}")
    print(f"  Next: python -m karl_finetune.compare_outputs --reports {output_dir}\n")
    return str(results_path)


def main():
    p = argparse.ArgumentParser(description="Run eval prompts against base or fine-tuned model")
    p.add_argument("config", help="Path to eval_config.json")
    p.add_argument("--mode", choices=["base", "tuned"], default="base",
                   help="Which model to evaluate (default: base)")
    args = p.parse_args()
    run_eval(args.config, args.mode)


if __name__ == "__main__":
    main()
