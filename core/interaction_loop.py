# THE HACKABLE LAYER
# Modify this file to change how the application interacts with the LLM.
# Hot-reloaded before every generation -- save and click Generate, no restart needed.

from app.engine.model_loader import ModelLoader

# System prompt used when the custom_greeting adapter (or any adapter) is active.
# This matches the training data, so the adapter fires correctly.
_ADAPTER_SYSTEM_PROMPT = "Always respond in English."


def build_prompt(system_prompt, chat_history):
    """
    Builds the ChatML prompt for DeepSeek-R1-Distill-Qwen models.

    When NO adapter is active (base model):
        - Use the full system_prompt passed in from the Workbench.
        - Pre-seed <think>\\n so the model immediately enters reasoning mode.
          Without this, the base model outputs garbled text.

    When an adapter IS active:
        - Use a minimal system prompt that matches the adapter's training data.
          The full Karl system prompt confuses adapters trained on simpler prompts.
        - Do NOT pre-seed <think>\\n. The adapter generates its own <think>
          block from scratch if it wants one.

    NOTE on DeepSeek-R1 1.5B (Qwen2.5 base):
    This model was trained on a large proportion of Chinese text. Without
    an explicit "respond in English" instruction in the system prompt, it
    will often output Chinese characters.

    ChatML format:
        <|im_start|>system
        {system_prompt}<|im_end|>
        <|im_start|>user
        {user_message}<|im_end|>
        <|im_start|>assistant
        <think>                   ← only for base model
        {model begins reasoning}
    """
    active_adapter = getattr(ModelLoader, "_active_adapter", None)
    adapter_active = bool(active_adapter)

    # When an adapter is active, use the minimal system prompt it was trained on
    effective_system = _ADAPTER_SYSTEM_PROMPT if adapter_active else system_prompt

    prompt = f"<|im_start|>system\n{effective_system}<|im_end|>\n"
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"

    if adapter_active and active_adapter != "math_solver":
        # Adapter generates <think> from scratch if its training included one.
        # Pre-seeding forces mid-thought mode and causes it to skip its response.
        prompt += "<|im_start|>assistant\n"
    else:
        # Pre-seed <think> so the base model or math_solver immediately enters reasoning mode.
        # LLMThread's parser expects the stream to start inside the thought block.
        prompt += "<|im_start|>assistant\n<think>\n"

    return prompt
