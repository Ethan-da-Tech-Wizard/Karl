"""
Dataset Formatter — karl_finetune
===================================
Converts raw instruction/input/output JSONL into formatted training text.

Supported templates:
  alpaca   — ### Instruction / ### Input / ### Response blocks
  chat     — messages list (ShareGPT / ChatML compatible)
  chatml   — <|im_start|> / <|im_end|> token format

Output is a JSONL file with one field per line:
  alpaca  → {"text": "### Instruction: ..."}
  chat    → {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}

Usage:
  python -m karl_finetune.format_dataset data/train.jsonl --template alpaca
  python -m karl_finetune.format_dataset data/train.jsonl --template chat --output data/train_chat.jsonl
"""

import argparse
import json
import sys
from pathlib import Path


# ── Templates ─────────────────────────────────────────────────────────────────

def alpaca_template(instruction: str, input_text: str, output: str) -> dict:
    """Alpaca-style block format — wide model compatibility."""
    body = f"### Instruction:\n{instruction}"
    if input_text.strip():
        body += f"\n\n### Input:\n{input_text}"
    body += f"\n\n### Response:\n{output}"
    return {"text": body}


def chat_template(instruction: str, input_text: str, output: str,
                  system_prompt: str = "") -> dict:
    """ShareGPT / messages format — for chat-tuned models."""
    user_content = instruction
    if input_text.strip():
        user_content += f"\n\n{input_text}"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user",      "content": user_content})
    messages.append({"role": "assistant", "content": output})
    return {"messages": messages}


def chatml_template(instruction: str, input_text: str, output: str,
                    system_prompt: str = "You are a helpful assistant.") -> dict:
    """ChatML token format — for models using <|im_start|> delimiters."""
    user_content = instruction
    if input_text.strip():
        user_content += f"\n\n{input_text}"

    text = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_content}<|im_end|>\n"
        f"<|im_start|>assistant\n{output}<|im_end|>"
    )
    return {"text": text}


TEMPLATES = {
    "alpaca": alpaca_template,
    "chat":   chat_template,
    "chatml": chatml_template,
}


# ── Formatter ─────────────────────────────────────────────────────────────────

def format_dataset(
    input_path: str,
    template_name: str = "alpaca",
    output_path: str | None = None,
    system_prompt: str = "",
) -> str:
    """
    Convert a raw JSONL dataset to a formatted training JSONL.

    Args:
        input_path:    Path to source JSONL (instruction/input/output format).
        template_name: One of 'alpaca', 'chat', 'chatml'.
        output_path:   Destination path. Defaults to input stem + _TEMPLATE.jsonl.
        system_prompt: Optional system message injected for chat/chatml templates.

    Returns:
        Path of the written output file.
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template '{template_name}'. Choose: {list(TEMPLATES)}")

    fn = TEMPLATES[template_name]
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if output_path is None:
        output_path = str(src.parent / f"{src.stem}_{template_name}.jsonl")

    records_in  = 0
    records_out = 0
    skipped     = 0

    with open(src, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for i, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            records_in += 1

            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  ⚠  Line {i}: JSON error — {e}. Skipping.", file=sys.stderr)
                skipped += 1
                continue

            instruction = rec.get("instruction", "").strip()
            input_text  = rec.get("input", "").strip()
            output      = rec.get("output", "").strip()

            if not instruction or not output:
                print(f"  ⚠  Line {i}: missing instruction or output. Skipping.", file=sys.stderr)
                skipped += 1
                continue

            # Pass system_prompt only to templates that accept it
            if template_name in ("chat", "chatml"):
                formatted = fn(instruction, input_text, output, system_prompt)
            else:
                formatted = fn(instruction, input_text, output)

            fout.write(json.dumps(formatted, ensure_ascii=False) + "\n")
            records_out += 1

    print(f"\n  Template  : {template_name}")
    print(f"  Input     : {input_path}  ({records_in} lines)")
    print(f"  Output    : {output_path}  ({records_out} formatted)")
    if skipped:
        print(f"  Skipped   : {skipped}")
    print()

    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Format a JSONL dataset for LoRA training")
    p.add_argument("path",       help="Input JSONL file (instruction/input/output format)")
    p.add_argument("--template", default="alpaca",
                   choices=list(TEMPLATES),
                   help="Prompt template to apply (default: alpaca)")
    p.add_argument("--output",   default=None,
                   help="Output path (default: input_stem_TEMPLATE.jsonl)")
    p.add_argument("--system",   default="",
                   help="System prompt for chat/chatml templates")
    args = p.parse_args()
    format_dataset(args.path, args.template, args.output, args.system)


if __name__ == "__main__":
    main()
