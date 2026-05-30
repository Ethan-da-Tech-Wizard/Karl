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
    pos = 0
    text_lower = raw_text.lower()

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

    thought = "".join(thought_parts).strip()
    response = "".join(response_parts).strip()
    return thought, response
