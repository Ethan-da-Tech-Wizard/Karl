import os
import time
from llama_cpp import Llama
from app.utils.trace_logger import TraceLogger
from core.cognitive_parser import parse_thought_stream

def test_introspection_engine():
    model_path = "data/models/deepseek-r1-1.5b.gguf"
    
    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}.")
        print("Run: python download_test_model.py")
        return

    print("Initializing Introspection Engine...")
    
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,
        verbose=False
    )

    logger = TraceLogger()

    # Create a prompt that encourages "thinking"
    system_prompt = "You are an analytical assistant. Always wrap your internal reasoning inside <think> and </think> tags before answering."
    user_prompt = "If a tree falls in a forest and no one is around to hear it, does it make a sound? Think step by step."
    
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n<think>\n"
    
    hyperparams = {
        "max_tokens": 150,
        "temperature": 0.7,
        "top_p": 0.95
    }

    print("\n--- Sending Prompt to LLM ---")
    start_time = time.time()
    
    # We use non-streaming for this headless test to easily capture the whole output
    response = llm(
        prompt,
        max_tokens=hyperparams["max_tokens"],
        temperature=hyperparams["temperature"],
        top_p=hyperparams["top_p"],
        stop=["<|im_end|>"]
    )
    
    raw_output = "<think>\n" + response['choices'][0]['text']
    execution_time = time.time() - start_time
    
    # Parse the output
    thought, final_response = parse_thought_stream(raw_output)
    
    print("\n--- MODEL THOUGHT STREAM ---")
    print(thought if thought else "[No explicit thought process detected]")
    
    print("\n--- FINAL MODEL RESPONSE ---")
    print(final_response)
    
    # Log the trace
    log_file = logger.log_generation(
        compiled_prompt=prompt,
        hyperparams=hyperparams,
        raw_output=raw_output,
        parsed_thought=thought,
        parsed_response=final_response,
        execution_time=execution_time
    )
    
    print(f"\n--- LOG WRITTEN ---")
    print(f"Trace fully logged to: {log_file}")

if __name__ == "__main__":
    test_introspection_engine()
