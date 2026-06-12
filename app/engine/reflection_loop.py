import re
from app.engine.model_loader import ModelLoader

def run_reflection_loop(task: dict, failed_thought: str, failed_response: str, error_traceback: str) -> tuple[str, str]:
    """
    Queries the local LLM to fix the failed code using the traceback.
    Returns (corrected_thoughts, corrected_code).
    """
    system_prompt = (
        "You are an expert code debugger. You are given a problem, a failed solution, "
        "and the compiler error traceback. Identify the bug, write a detailed self-reflection, "
        "and write the corrected code inside a python code block."
    )
    user_message = (
        f"Problem: {task['problem_statement']}\n\n"
        f"Failed Code:\n{failed_response}\n\n"
        f"Traceback:\n{error_traceback}\n\n"
        "Find the bug, output your reflection, and write the final correct solution."
    )
    
    model = ModelLoader.get_instance()
    
    # Pre-seed the think block for deepseek models
    prompt = f"<system>\n{system_prompt}\n</system>\n<user>\n{user_message}\n</user>\n<think>\n"
    
    try:
        res = model(
            prompt,
            max_tokens=2048,
            temperature=0.1,
            stop=["<|im_end|>", "</user>"]
        )
        raw_output = res["choices"][0]["text"]
    except Exception as e:
        return f"Error during reflection LLM execution: {e}", ""

    # Clean up double think tags if model outputs them
    raw_output_clean = raw_output.replace("<think>", "").strip()
    
    if "</think>" in raw_output_clean:
        parts = raw_output_clean.split("</think>", 1)
        corrected_thoughts = parts[0].strip()
        corrected_code = parts[1].strip()
    else:
        # If no closing tag, assume the entire output is the reflection/thoughts and code is extracted if code blocks are present
        corrected_thoughts = raw_output_clean
        # Try to find a python code block if present
        code_block = re.search(r"```python\n([\s\S]*?)```", raw_output_clean)
        if code_block:
            corrected_code = code_block.group(0)
        else:
            corrected_code = ""
        
    return corrected_thoughts, corrected_code
