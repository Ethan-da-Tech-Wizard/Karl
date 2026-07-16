# THE HACKABLE LAYER — modify to change how thoughts are parsed from raw LLM output.
#
# This module is used for BATCH POST-PROCESSING only (e.g. engine_test.py).
# The live streaming threads (LLMThread, AgenticThread) contain their own
# inline state machines that route tokens in real time without calling this function.

_OPEN  = "<think>"
_CLOSE = "</think>"


def parse_thought_stream(raw_text: str, start_in_thought: bool = False) -> tuple[str, str]:
    """
    State-machine parser for DeepSeek-R1 style ``<think>…</think>`` blocks.

    Handles:
    - Any capitalisation variant of the open/close tags (case-insensitive search).
    - Multiple ``<think>`` blocks in a single output (all thought segments merged).
    - Unclosed tags — if generation was cut off mid-thought, the remaining text
      is classified as thought content rather than response.
    - Pre-seeded think blocks — when the prompt ends with ``<think>\\n``, the raw
      model output begins *inside* a thought block (no opening tag present). The
      parser detects this by checking whether a ``</think>`` appears before any
      ``<think>`` and initialises ``in_thought = True`` accordingly.
    - Quantization/hallucination artifact removal — the token sequence
      ``"overposting"`` is a known artefact of some quantised DeepSeek weights
      that leaks through reasoning and response text. It is stripped from both
      sections before returning.

    Args:
        raw_text: The complete raw string returned by ``llm()["choices"][0]["text"]``.
        start_in_thought: If True, indicates the generation sequence was pre-seeded
          in thought mode.

    Returns:
        A ``(thought_text, response_text)`` tuple. Both parts are stripped of
        leading/trailing whitespace. Either may be an empty string.
    """
    thought_parts: list[str] = []
    response_parts: list[str] = []
    in_thought = start_in_thought
    
    # Check if we should start in thought mode.
    # This happens when the model starts generating inside a think block
    # (e.g. because <think> was pre-seeded in the prompt).
    text_lower = raw_text.lower()
    open_idx = text_lower.find(_OPEN)
    close_idx = text_lower.find(_CLOSE)
    
    if close_idx != -1 and (open_idx == -1 or close_idx < open_idx):
        in_thought = True

    pos = 0
    while pos < len(raw_text):
        if not in_thought:
            open_idx = text_lower.find(_OPEN, pos)
            if open_idx == -1:
                response_parts.append(raw_text[pos:])
                break
            response_parts.append(raw_text[pos:open_idx])
            in_thought = True
            pos = open_idx + len(_OPEN)
        else:
            close_idx = text_lower.find(_CLOSE, pos)
            if close_idx == -1:
                thought_parts.append(raw_text[pos:])
                break
            thought_parts.append(raw_text[pos:close_idx])
            in_thought = False
            pos = close_idx + len(_CLOSE)

    import re
    thought = "".join(thought_parts).strip()
    response = "".join(response_parts).strip()
    
    # Strip known quantization/hallucination artifacts like 'overposting'
    thought = re.sub(r'(?i)\s*\boverposting\b[.\s]*', '', thought).strip()
    response = re.sub(r'(?i)\s*\boverposting\b[.\s]*', '', response).strip()
    
    return thought, response

