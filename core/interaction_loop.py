# THE HACKABLE LAYER
# Modify this file to change how the application interacts with the LLM.
# Hot-reloaded before every generation -- save and click Generate, no restart needed.

from app.engine.model_loader import ModelLoader

# System prompt used when the custom_greeting adapter (or any adapter) is active.
# This matches the training data, so the adapter fires correctly.
_ADAPTER_SYSTEM_PROMPT = "Always respond in English."


def build_prompt(system_prompt, chat_history):
    """
    Builds the native DeepSeek-R1 prompt for distilled models.

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

    Native DeepSeek Template format:
        {system_prompt}<｜User｜>{user_message}<｜Assistant｜><think>
    """
    active_adapter = getattr(ModelLoader, "_active_adapter", None)
    adapter_active = bool(active_adapter)

    # When an adapter is active, use the minimal system prompt it was trained on
    effective_system = _ADAPTER_SYSTEM_PROMPT if adapter_active else system_prompt

    # Note: llama-cpp-python automatically prepends the BOS token (<｜begin of sentence｜>)
    # by default, so we do not prepend it here to avoid duplicate BOS token warnings.
    prompt = f"{effective_system}"
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Map ChatML roles to DeepSeek native tags
        if role == "user":
            prompt += f"<｜User｜>{content}"
        elif role == "assistant":
            prompt += f"<｜Assistant｜>{content}<｜end\u2581of\u2581sentence｜>"

    if adapter_active and active_adapter != "math_solver":
        # Adapter generates <think> from scratch if its training included one.
        # Pre-seeding forces mid-thought mode and causes it to skip its response.
        prompt += "<｜Assistant｜>"
    else:
        # Pre-seed <think> so the base model or math_solver immediately enters reasoning mode.
        # LLMThread's parser expects the stream to start inside the thought block.
        prompt += "<｜Assistant｜><think>\n"

    return prompt
