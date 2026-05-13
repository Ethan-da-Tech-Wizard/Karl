"""
Karl Fine-Tuning Script — powered by Unsloth

Usage:
    python finetune.py
    python finetune.py --input data/training/export_unsloth.jsonl
    python finetune.py --input data/training/export_unsloth.jsonl --output data/models/karl-v2

What this does:
    1. Loads your curated training examples from the Karl UI (thumbs-up + corrections)
    2. Fine-tunes DeepSeek R1 1.5B using LoRA (trains a small adapter, not the full model)
    3. Saves a merged GGUF file you can drop straight into data/models/ and use in Karl

Requirements:
    pip install -r requirements-finetune.txt
    (Needs an NVIDIA GPU with at least 6 GB VRAM — won't run on CPU)
"""

import argparse
import json
import os
import sys


MIN_EXAMPLES = 10  # Warn if fewer than this — model won't learn much


def load_dataset(path: str):
    if not os.path.exists(path):
        print(f"[ERROR] Training file not found: {path}")
        print("  → Open Karl, rate some responses with 👍 or 👎, then click 'Export for Unsloth'.")
        sys.exit(1)

    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[WARN] Skipping malformed line {i}: {e}")

    print(f"[INFO] Loaded {len(examples)} training examples from {path}")

    if len(examples) < MIN_EXAMPLES:
        print(f"[WARN] Only {len(examples)} examples — fine-tuning works best with 50+.")
        print("       Continuing anyway, but expect limited improvement.")

    return examples


def format_conversations(examples: list, tokenizer) -> list:
    """Convert Karl's chat format to Unsloth's expected input."""
    formatted = []
    for ex in examples:
        messages = ex.get("messages", [])
        # apply_chat_template expects a list of {"role": ..., "content": ...} dicts
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )
        formatted.append({"text": text})
    return formatted


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Karl's model on curated examples")
    parser.add_argument(
        "--input",
        default="data/training/export_unsloth.jsonl",
        help="Path to the exported JSONL from Karl's Training Data Curator"
    )
    parser.add_argument(
        "--output",
        default="data/models/karl-finetuned",
        help="Output directory for the fine-tuned model"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs (default: 3)"
    )
    parser.add_argument(
        "--gguf-name",
        default="karl-finetuned.gguf",
        help="Filename for the exported GGUF (goes into --output dir)"
    )
    args = parser.parse_args()

    # ── Import Unsloth (fail loudly with a helpful message) ──────────────────
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("[ERROR] Unsloth is not installed.")
        print("  → Run:  pip install -r requirements-finetune.txt")
        sys.exit(1)

    try:
        from trl import SFTTrainer, SFTConfig
        import torch
        from datasets import Dataset
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("  → Run:  pip install -r requirements-finetune.txt")
        sys.exit(1)

    # ── Load data ────────────────────────────────────────────────────────────
    raw_examples = load_dataset(args.input)

    # ── Load base model via Unsloth ──────────────────────────────────────────
    print("[INFO] Loading base model (DeepSeek R1 1.5B) via Unsloth…")
    print("       First run will download ~3 GB from HuggingFace.")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/DeepSeek-R1-Distill-Qwen-1.5B",
        max_seq_length=2048,
        load_in_4bit=True,   # 4-bit quantization — fits in 6 GB VRAM
        dtype=None,          # auto-detect
    )

    # ── Attach LoRA adapter ──────────────────────────────────────────────────
    # LoRA only trains a small set of weight deltas — much faster and cheaper
    # than full fine-tuning, and the result can be merged back into the base weights.
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,                     # LoRA rank — higher = more capacity, more VRAM
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",  # saves VRAM
        random_state=42,
    )

    # ── Format dataset ───────────────────────────────────────────────────────
    print("[INFO] Formatting dataset…")
    formatted = format_conversations(raw_examples, tokenizer)
    dataset = Dataset.from_list(formatted)

    # ── Train ────────────────────────────────────────────────────────────────
    print(f"[INFO] Starting training — {args.epochs} epoch(s) on {len(dataset)} examples…")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=2048,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,   # effective batch size = 8
            num_train_epochs=args.epochs,
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            output_dir=args.output,
            save_strategy="no",              # we'll export GGUF at the end
            warmup_ratio=0.1,
            lr_scheduler_type="cosine",
            seed=42,
        ),
    )

    trainer.train()
    print("[INFO] Training complete.")

    # ── Save as GGUF ─────────────────────────────────────────────────────────
    os.makedirs(args.output, exist_ok=True)
    gguf_path = os.path.join(args.output, args.gguf_name)
    print(f"[INFO] Exporting GGUF to {gguf_path}…")
    print("       Using Q4_K_M quantization (good balance of size and quality).")

    model.save_pretrained_gguf(
        args.output,
        tokenizer,
        quantization_method="q4_k_m",
    )

    # Unsloth names the file automatically — find it and rename if needed
    produced = [f for f in os.listdir(args.output) if f.endswith(".gguf")]
    if produced and produced[0] != args.gguf_name:
        src = os.path.join(args.output, produced[0])
        os.rename(src, gguf_path)

    print()
    print("=" * 60)
    print("  DONE")
    print("=" * 60)
    print(f"  Model saved to:  {gguf_path}")
    print()
    print("  To use in Karl:")
    print(f"    1. Copy {gguf_path}")
    print(f"       → data/models/{args.gguf_name}")
    print("    2. Edit app/engine/model_loader.py and change:")
    print(f'         model_path="data/models/deepseek-r1-1.5b.gguf"')
    print(f'       to:')
    print(f'         model_path="data/models/{args.gguf_name}"')
    print("    3. Restart Karl.")
    print()


if __name__ == "__main__":
    main()
