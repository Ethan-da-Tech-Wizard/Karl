# THE HACKABLE LAYER
# Modify this file to change how the application interacts with the LLM.

def build_prompt(system_prompt, chat_history):
    """
    Builds the prompt string from the system prompt and chat history.
    Currently uses ChatML format which works for many modern models.
    """
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
    
    # Prompt the assistant to reply
    prompt += "<|im_start|>assistant\n"
    return prompt
