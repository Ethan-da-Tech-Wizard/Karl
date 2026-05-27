"""
Quick raw model test -- bypasses all UI/threading.
Run: python raw_test.py
"""
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

os.environ["HF_HUB_OFFLINE"] = "1"

from llama_cpp import Llama

MODEL = "data/models/deepseek-r1-1.5b.gguf"

print("Loading model...")
llm = Llama(model_path=MODEL, n_ctx=4096, verbose=False)
print("Model loaded.\n")

# Build a minimal ChatML prompt, pre-seeding <think> so the model
# immediately enters reasoning mode instead of outputting garbage.
SYSTEM = "You are Karl, a helpful AI assistant. Answer the user's question clearly and directly."
USER   = "What is 2 + 2? Explain your answer briefly."

prompt = (
    f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"
    f"<|im_start|>user\n{USER}<|im_end|>\n"
    f"<|im_start|>assistant\n<think>\n"
)

print("Prompt sent:")
print(repr(prompt))
print("\n--- RAW OUTPUT ---")

output = llm(
    prompt,
    max_tokens=512,
    temperature=0.7,
    top_p=0.95,
    repeat_penalty=1.1,
    stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>"],
    echo=False,
    stream=False,
)

raw = output["choices"][0]["text"]
finish = output["choices"][0]["finish_reason"]
print(raw)
print(f"\n--- finish_reason: {finish} ---")
print(f"--- token count: {output['usage']} ---")
