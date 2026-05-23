# THE HACKABLE LAYER
# Modify this file to change how the application interacts with the LLM.
# Hot-reloaded before every generation -- save and click Generate, no restart needed.

def build_prompt(system_prompt, chat_history):
    """
    Builds the ChatML prompt for DeepSeek-R1-Distill-Qwen models.

    CRITICAL: We pre-seed <think>\n at the end of the assistant turn.
    Without this, the model has no cue to enter reasoning mode and outputs
    garbled text (e.g. 'end of code'). With it, the model immediately
    begins its thought chain and produces a clean answer after </think>.
    """
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"

    # Pre-seed <think> so the model immediately enters reasoning mode.
    # LLMThread's parser expects the stream to start inside the thought block.
    prompt += "<|im_start|>assistant\n<think>\n"
    return prompt
