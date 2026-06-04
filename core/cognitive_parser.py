# THE HACKABLE LAYER — modify to change how thoughts are parsed from raw LLM output.

_OPEN  = "<think>"
_CLOSE = "</think>"


def parse_thought_stream(raw_text: str) -> tuple[str, str]:
    """
    State-machine parser: handles any capitalisation variant of <think> tags,
    multiple think blocks, and unclosed tags (model stopped mid-thought).

    Returns:
        (thought_text, response_text)
    """
    thought_parts: list[str] = []
    response_parts: list[str] = []
    in_thought = False
    
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

