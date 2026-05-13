# THE HACKABLE LAYER
# Modify this file to change how the application parses "thoughts" from the LLM.

def parse_thought_stream(raw_text):
    """
    Parses a raw text output from the LLM into a 'thought' block and a 'response' block.
    This assumes the model uses <think> and </think> tags, which is common for reasoning models like DeepSeek-R1.
    """
    thought = ""
    response = raw_text

    # Basic extraction logic
    if "<think>" in raw_text:
        parts = raw_text.split("<think>", 1)
        after_think = parts[1]
        
        if "</think>" in after_think:
            thought_parts = after_think.split("</think>", 1)
            thought = thought_parts[0].strip()
            response = parts[0] + thought_parts[1].strip()
        else:
            # The generation stopped before closing the think tag
            thought = after_think.strip()
            response = parts[0].strip()
            
    return thought, response.strip()
