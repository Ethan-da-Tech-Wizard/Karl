# THE HACKABLE LAYER
# Modify this file to change how the application interacts with the LLM.
# Hot-reloaded before every generation -- save and click Generate, no restart needed.

from app.engine.model_loader import ModelLoader

# System prompt used when the custom_greeting adapter (or any adapter) is active.
# This matches the training data, so the adapter fires correctly.
_ADAPTER_SYSTEM_PROMPT = "Always respond in English."

_BASE_SYSTEM_PROMPT = (
    "You are Karl, a precise and thoughtful AI assistant. "
    "Always respond in English. "
    "Analyze and break down problems step-by-step. "
    "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
    "Double-check your derivations and arithmetic before writing the final answer."
)


def build_prompt(system_prompt, chat_history):
    """
    Builds the native prompt for distilled models based on loaded architecture.

    When NO adapter is active (base model):
        - Use the full system_prompt passed in from the Workbench.
        - Pre-seed <think>\n so the model immediately enters reasoning mode.
          Without this, the base model outputs garbled text.

    When an adapter IS active:
        - Use a minimal system prompt that matches the adapter's training data.
          The full Karl system prompt confuses adapters trained on simpler prompts.
        - Do NOT pre-seed <think>\n. The adapter generates its own <think>
          block from scratch if it wants one.
    """
    active_adapter = getattr(ModelLoader, "_active_adapter", None)
    adapter_active = bool(active_adapter)

    # When an adapter is active, we check if the user provided a custom system prompt
    # or if there is a RAG context. If the system prompt is empty or is one of the
    # default system prompts, we use the adapter's trained system prompt (_ADAPTER_SYSTEM_PROMPT).
    # Otherwise, we use the custom system prompt to let it affect the model.
    # We also always preserve any RAG context.
    
    rag_context = ""
    clean_sys = system_prompt
    if "\n\nRetrieved Context:\n" in system_prompt:
        parts = system_prompt.split("\n\nRetrieved Context:\n", 1)
        clean_sys = parts[0]
        rag_context = "\n\nRetrieved Context:\n" + parts[1]

    default_sys_prompts = {
        "",
        "You are Karl, a precise and thoughtful AI assistant. Always respond in English. Analyze and break down problems step-by-step. Write down your detailed thoughts and calculations inside <think>...</think> blocks. Double-check your derivations and arithmetic before writing the final answer.",
        "Always respond in English."
    }
    
    clean_sys_stripped = " ".join(clean_sys.strip().split())
    is_default = any(
        clean_sys_stripped == " ".join(p.strip().split()) 
        for p in default_sys_prompts
    )

    if adapter_active:
        if is_default:
            effective_system = _ADAPTER_SYSTEM_PROMPT + rag_context
        else:
            effective_system = clean_sys + rag_context
    else:
        if is_default:
            effective_system = _BASE_SYSTEM_PROMPT + rag_context
        else:
            effective_system = clean_sys + rag_context

    # Determine if we should pre-seed `<think>\n`
    last_user_msg = ""
    for msg in reversed(chat_history):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    def is_greeting(text: str) -> bool:
        t = text.strip().lower().rstrip(".!?")
        return t in {"hi", "hello", "hey", "yo", "greetings", "good morning", "good afternoon", "good evening"}

    preseed_think = True
    if adapter_active:
        # For the greeting adapter or any adapter, if the input is a simple greeting,
        # we don't pre-seed <think>\n, so the custom greeting fires immediately.
        # Otherwise, we pre-seed it so the model does reasoning.
        if is_greeting(last_user_msg):
            preseed_think = False

    model_name = ModelLoader.model_name().lower()

    if "llama" in model_name:
        # Llama 3 chat template format
        prompt = ""
        if effective_system:
            prompt += f"<|start_header_id|>system<|end_header_id|>\n\n{effective_system}<|eot_id|>"
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                prompt += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"

        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        if preseed_think:
            prompt += "<think>\n"

    elif "qwen" in model_name or "1.5b" in model_name or "7b" in model_name or "14b" in model_name:
        # ChatML format (Qwen-based distilled models)
        prompt = ""
        if effective_system:
            prompt += f"<|im_start|>system\n{effective_system}<|im_end|>\n"
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"

        prompt += "<|im_start|>assistant\n"
        if preseed_think:
            prompt += "<think>\n"

    else:
        # Native DeepSeek format fallback
        prompt = ""
        if effective_system:
            prompt += f"{effective_system}"
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt += f"<｜User｜>{content}"
            elif role == "assistant":
                prompt += f"<｜Assistant｜>{content}<｜end\u2581of\u2581sentence｜>"

        if preseed_think:
            prompt += "<｜Assistant｜><think>\n"
        else:
            prompt += "<｜Assistant｜>"

    return prompt

