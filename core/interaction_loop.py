# THE HACKABLE LAYER
# Modify this file to change how the application interacts with the LLM.
# Hot-reloaded before every generation -- save and click Generate, no restart needed.

import logging
import os
import re
from app.engine.model_loader import ModelLoader

# System prompt used when the custom_greeting adapter (or any adapter) is active.
# This matches the training data, so the adapter fires correctly.
logger = logging.getLogger("karl.codex_injector")


_ADAPTER_SYSTEM_PROMPT = "Always respond in English."
_RECENCY_INSTRUCTION = (
    "Treat the latest user message as the active request; "
    "use earlier turns only as context when relevant."
)

_BASE_SYSTEM_PROMPT = (
    "You are Karl, a precise and thoughtful AI assistant. "
    "Always respond in English. "
    f"{_RECENCY_INSTRUCTION} "
    "Analyze and break down problems step-by-step. "
    "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
    "Double-check your derivations and arithmetic before writing the final answer."
)

_CODEX_KEYWORD_MAP = {
    "python": "Python.html",
    "c++": "C++.html",
    "cpp": "C++.html",
    "sql": "SQL.html",
    "rust": "Rust.html",
    "react": "React.html",
    "node": "Nodejs.html",
    "nodejs": "Nodejs.html",
    "node.js": "Nodejs.html",
    "go": "Go.html",
    "golang": "Go.html",
    "agile": "Agile.html",
    "xcode": "Xcode.html",
    "swift": "Swift.html",
    "fortran": "Fortran.html",
    "c#": "C#.html",
    "csharp": "C#.html",
    "c": "C.html",
    "docker": "Docker.html",
    "kubernetes": "Kubernetes.html",
    "k8s": "Kubernetes.html",
    "css": "CSS.html",
    "html": "HTML.html",
    "typescript": "TypeScript.html",
    "ts": "TypeScript.html",
    "java": "Java.html",
    "javascript": "JavaScript.html",
    "js": "JavaScript.html",
    "api": "APIs.html",
    "apis": "APIs.html",
    "uvicorn": "Uvicorn.html",
    "fastapi": "FastAPI.html"
}

def strip_html_tags(html: str) -> str:
    # Remove script and style elements first
    text = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)</\1>', '', html)
    # Replace block-level element tags with newlines or spaces to preserve spacing
    text = re.sub(r'</?(div|p|h[1-6]|li|ul|ol|table|tr|td|thead|tbody|br|pre|code)\b[^>]*>', '\n', text)
    # Remove any other tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities (optional, but good for common ones like &lt;, &gt;, &amp;, &quot;)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    # Clean up excess whitespace/newlines
    lines = [line.strip() for line in text.split('\n')]
    cleaned = []
    last_empty = False
    for line in lines:
        if line:
            cleaned.append(line)
            last_empty = False
        elif not last_empty:
            cleaned.append("")
            last_empty = True
    return '\n'.join(cleaned).strip()

def matches_keyword(text: str, keyword: str) -> bool:
    if keyword == "c":
        # Match 'c' but not 'c++' or 'c#'
        pattern = r'\bc\b(?![+#])'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    # Escape regex special chars in the keyword
    pattern = re.escape(keyword)
    # Check if keyword starts with a word character to apply word boundary
    start_boundary = r'\b' if keyword[0].isalnum() or keyword[0] == '_' else ''
    # Check if keyword ends with a word character to apply word boundary
    end_boundary = r'\b' if keyword[-1].isalnum() or keyword[-1] == '_' else ''
    
    full_pattern = start_boundary + pattern + end_boundary
    return bool(re.search(full_pattern, text, re.IGNORECASE))

def _get_codex_context(chat_history):
    last_user_msg = ""
    for msg in reversed(chat_history):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    if not last_user_msg:
        return ""

    matched_filenames = []
    for kw, filename in _CODEX_KEYWORD_MAP.items():
        if matches_keyword(last_user_msg, kw):
            if filename not in matched_filenames:
                matched_filenames.append(filename)
            if len(matched_filenames) >= 2:
                break

    if not matched_filenames:
        return ""

    context_parts = []
    library_dir = "data/codex_library"
    for filename in matched_filenames:
        filepath = os.path.join(library_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                stripped = strip_html_tags(content)
                topic = os.path.splitext(filename)[0]
                context_parts.append(f"[{topic}]\n{stripped}")
            except Exception as e:
                logger.warning(f"Error reading {filename}: {e}")

    if not context_parts:
        return ""

    return "\n\nCodex Reference Context:\n" + "\n\n".join(context_parts)


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
        "You are Karl, a precise and thoughtful AI assistant. Always respond in English. Treat the latest user message as the active request; use earlier turns only as context when relevant. Analyze and break down problems step-by-step. Write down your detailed thoughts and calculations inside <think>...</think> blocks. Double-check your derivations and arithmetic before writing the final answer.",
        "Always respond in English."
    }
    
    clean_sys_stripped = " ".join(clean_sys.strip().split())
    is_default = any(
        clean_sys_stripped == " ".join(p.strip().split()) 
        for p in default_sys_prompts
    )

    # Get dynamic Codex reference context based on keyword matching
    codex_context = _get_codex_context(chat_history)

    if adapter_active:
        if is_default:
            effective_system = _ADAPTER_SYSTEM_PROMPT + rag_context + codex_context
        else:
            effective_system = clean_sys + rag_context + codex_context
    else:
        if is_default:
            effective_system = _BASE_SYSTEM_PROMPT + rag_context + codex_context
        else:
            effective_system = clean_sys + rag_context + codex_context

    if _RECENCY_INSTRUCTION not in effective_system:
        effective_system = (effective_system + "\n" if effective_system else "") + _RECENCY_INSTRUCTION

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
