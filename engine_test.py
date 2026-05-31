"""
engine_test.py — Karl headless introspection engine smoke test.

Runs a single generation against the active GGUF model (as configured in
data/active_model.json or the fallback deepseek-r1-1.5b.gguf), exercises the
cognitive parser, and writes a trace log entry.

Usage:
    python engine_test.py

If no model is present, download one first:
    python download_test_model.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.engine.model_loader import ModelLoader
from app.utils.trace_logger import TraceLogger
from core.cognitive_parser import parse_thought_stream


def test_introspection_engine():
    # ------------------------------------------------------------------
    # 1. Model loading — honours data/active_model.json, falls back to
    #    the 1.5b GGUF if absent.  Uses the registry-aware n_ctx.
    # ------------------------------------------------------------------
    print("Initialising ModelLoader …")
    try:
        llm = ModelLoader.get_instance()
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}")
        print("Run:  python download_test_model.py")
        sys.exit(1)

    print(f"Model : {ModelLoader.model_name()}")
    print(f"n_ctx : {ModelLoader.n_ctx()}")

    # ------------------------------------------------------------------
    # 2. Build a minimal ChatML prompt that pre-seeds the <think> block
    # ------------------------------------------------------------------
    system_prompt = (
        "You are an analytical assistant. "
        "Always wrap your internal reasoning inside <think> and </think> "
        "tags before answering."
    )
    user_prompt = (
        "If a tree falls in a forest and no one is around to hear it, "
        "does it make a sound? Think step by step."
    )
    prompt = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n<think>\n"
    )

    hyperparams = {
        "max_tokens": 150,
        "temperature": 0.7,
        "top_p": 0.95,
    }

    # ------------------------------------------------------------------
    # 3. Inference (non-streaming for this headless test)
    # ------------------------------------------------------------------
    print("\n--- Sending prompt to LLM ---")
    start_time = time.time()

    response = llm(
        prompt,
        max_tokens=hyperparams["max_tokens"],
        temperature=hyperparams["temperature"],
        top_p=hyperparams["top_p"],
        stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"],
    )

    raw_output = "<think>\n" + response["choices"][0]["text"]
    execution_time = time.time() - start_time

    # ------------------------------------------------------------------
    # 4. Parse thinking vs. response
    # ------------------------------------------------------------------
    thought, final_response = parse_thought_stream(raw_output)

    print("\n--- MODEL THOUGHT STREAM ---")
    print(thought if thought else "[No explicit thought process detected]")
    print("\n--- FINAL MODEL RESPONSE ---")
    print(final_response)

    # ------------------------------------------------------------------
    # 5. Write trace log
    # ------------------------------------------------------------------
    logger = TraceLogger()
    log_file = logger.log_generation(
        model_name=ModelLoader.model_name(),
        compiled_prompt=prompt,
        hyperparams=hyperparams,
        raw_output=raw_output,
        parsed_thought=thought,
        parsed_response=final_response,
        execution_time=execution_time,
    )

    print(f"\n--- LOG WRITTEN ---")
    print(f"Trace fully logged to: {log_file}")


if __name__ == "__main__":
    test_introspection_engine()
