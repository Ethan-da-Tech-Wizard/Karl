"""
LoRA Trainer — karl_finetune
==============================
Trains a LoRA adapter on top of a base model using a formatted JSONL dataset.

Requires training dependencies (NOT in requirements.txt by design):
    pip install torch transformers peft trl datasets accelerate bitsandbytes

Config file format (configs/finetune_config.json):
    See configs/finetune_config.json for full reference.

Usage:
    python -m karl_finetune.train_lora configs/finetune_config.json
    python -m karl_finetune.train_lora configs/finetune_config.json --dry-run
"""

import argparse
import json
import sys
import time
from pathlib import Path


def _check_deps():
    missing = []
    for pkg in ("torch", "transformers", "peft", "trl", "datasets"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("  ✗  Missing training dependencies:")
        for m in missing:
            print(f"       pip install {m}")
        print("\n  Install all at once:")
        print("       pip install torch transformers peft trl datasets accelerate bitsandbytes")
        print("\n  Or use a separate venv / Google Colab to keep Karl's runtime clean.")
        sys.exit(1)


def _load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dry_run(cfg: dict):
    """Validate config and dataset without running training."""
    print("\n  ── Dry Run ─────────────────────────────────────────")
    print(f"  Model        : {cfg['model_name']}")
    print(f"  Train file   : {cfg['train_file']}")
    print(f"  Output dir   : {cfg['output_dir']}")
    print(f"  LoRA rank    : {cfg.get('lora_r', 16)}")
    print(f"  Epochs       : {cfg.get('epochs', 2)}")
    print(f"  Batch size   : {cfg.get('batch_size', 1)} × {cfg.get('gradient_accumulation_steps', 8)} grad accum")
    print(f"  Max seq len  : {cfg.get('max_seq_length', 1024)}")
    print(f"  Load in 4bit : {cfg.get('load_in_4bit', False)}")

    train_file = Path(cfg["train_file"])
    if train_file.exists():
        with open(train_file) as f:
            n = sum(1 for line in f if line.strip())
        print(f"  Train rows   : {n}")
    else:
        print(f"  ✗  Train file not found: {cfg['train_file']}")
        sys.exit(1)

    eval_file = Path(cfg.get("eval_file", ""))
    if eval_file and eval_file.exists():
        with open(eval_file) as f:
            n = sum(1 for line in f if line.strip())
        print(f"  Eval rows    : {n}")

    print("\n  ✅  Dry run passed. Remove --dry-run to start training.\n")


def train(config_path: str, dry_run: bool = False):
    cfg = _load_config(config_path)

    print(f"\n{'─' * 60}")
    print(f"  Karl Lite Fine-Tuning System")
    print(f"  Config: {config_path}")
    print(f"{'─' * 60}")

    if dry_run:
        _dry_run(cfg)
        return

    _check_deps()

    import torch
    from datasets import load_dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        BitsAndBytesConfig,
    )
    from peft import LoraConfig, get_peft_model, TaskType
    from trl import SFTTrainer, SFTConfig

    model_name   = cfg["model_name"]
    train_file   = cfg["train_file"]
    output_dir   = cfg["output_dir"]
    max_seq_len  = cfg.get("max_seq_length", 1024)
    load_in_4bit = cfg.get("load_in_4bit", False)
    epochs       = cfg.get("epochs", 2)
    lr           = cfg.get("learning_rate", 2e-4)
    batch_size   = cfg.get("batch_size", 1)
    grad_accum   = cfg.get("gradient_accumulation_steps", 8)
    lora_r       = cfg.get("lora_r", 16)
    lora_alpha   = cfg.get("lora_alpha", 32)
    lora_dropout = cfg.get("lora_dropout", 0.05)
    template     = cfg.get("template", "alpaca")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n  Loading tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"  Loading model {'(4-bit QLoRA)' if load_in_4bit else '(full precision)'}")
    model_kwargs = {}
    if load_in_4bit:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=cfg.get("target_modules", ["q_proj", "v_proj"]),
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print(f"\n  Loading dataset: {train_file}")
    raw_dataset = load_dataset("json", data_files={"train": train_file}, split="train")

    # Detect format — alpaca text field vs messages list
    sample = raw_dataset[0]
    if "text" in sample:
        # Pre-formatted alpaca/chatml text field
        formatting_func = None
        dataset_text_field = "text"
    elif "messages" in sample:
        # ShareGPT format — apply chat template
        def formatting_func(example):
            return tokenizer.apply_chat_template(
                example["messages"], tokenize=False, add_generation_prompt=False
            )
        dataset_text_field = None
    else:
        # Raw alpaca fields — format inline
        def _alpaca(ex):
            body = f"### Instruction:\n{ex.get('instruction', '')}"
            inp = ex.get("input", "").strip()
            if inp:
                body += f"\n\n### Input:\n{inp}"
            body += f"\n\n### Response:\n{ex.get('output', '')}"
            return body

        formatting_func = _alpaca
        dataset_text_field = None

    training_args = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        weight_decay=0.01,
        max_grad_norm=1.0,
        logging_steps=cfg.get("logging_steps", 10),
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",
        max_seq_length=max_seq_len,
        dataset_text_field=dataset_text_field,
    )

    trainer_kwargs = dict(
        model=model,
        tokenizer=tokenizer,
        train_dataset=raw_dataset,
        args=training_args,
    )
    if formatting_func is not None:
        trainer_kwargs["formatting_func"] = formatting_func

    trainer = SFTTrainer(**trainer_kwargs)

    print(f"\n  Starting training — {epochs} epoch(s), {len(raw_dataset)} examples")
    print(f"  Effective batch size: {batch_size * grad_accum}")
    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0

    print(f"\n  Training complete in {elapsed:.0f}s")
    print(f"  Saving adapter to {output_dir}")
    trainer.save_model(output_dir)

    # Write a training summary JSON for compare_outputs / reporting
    summary = {
        "model_name":  model_name,
        "adapter_dir": output_dir,
        "train_file":  train_file,
        "epochs":      epochs,
        "lora_r":      lora_r,
        "lora_alpha":  lora_alpha,
        "learning_rate": lr,
        "elapsed_seconds": round(elapsed, 1),
        "train_examples": len(raw_dataset),
    }
    summary_path = Path(output_dir) / "training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"  Summary saved to {summary_path}")
    print(f"\n  ✅  Adapter ready. Next: python -m karl_finetune.run_eval configs/eval_config.json\n")


def main():
    p = argparse.ArgumentParser(description="Karl LoRA trainer")
    p.add_argument("config", help="Path to finetune_config.json")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate config and dataset without training")
    args = p.parse_args()
    train(args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
