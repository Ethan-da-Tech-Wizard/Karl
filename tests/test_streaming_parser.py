from app.engine.streaming_parser import StreamingThoughtParser


def test_streaming_parser_handles_split_close_tag():
    thought_tokens = []
    chat_tokens = []
    parser = StreamingThoughtParser(
        in_thought=True,
        thought_cb=thought_tokens.append,
        chat_cb=chat_tokens.append,
        publish_events=False,
    )

    parser.feed("reasoning</thi")
    assert thought_tokens == []
    assert chat_tokens == []

    parser.feed("nk>answer")
    assert parser.parsed_thought == "reasoning"
    assert parser.parsed_response == "answer"
    assert chat_tokens == ["answer"]


def test_streaming_parser_can_defer_answer_after_think_close():
    thought_tokens = []
    chat_tokens = []
    parser = StreamingThoughtParser(
        in_thought=True,
        thought_cb=thought_tokens.append,
        chat_cb=chat_tokens.append,
        publish_events=False,
    )

    result = parser.feed("thought</think>answer", defer_after_think_close=True)

    assert result.closed_think
    assert parser.parsed_thought == "thought"
    assert parser.parsed_response == ""
    assert chat_tokens == []

    parser.flush()
    assert parser.parsed_response == "answer"
    assert chat_tokens == ["answer"]


def test_streaming_parser_detects_adapter_think_block_after_chat_prefix():
    thought_tokens = []
    chat_tokens = []
    parser = StreamingThoughtParser(
        in_thought=False,
        thought_cb=thought_tokens.append,
        chat_cb=chat_tokens.append,
        publish_events=False,
    )

    parser.feed("prefix<think>private</think>answer")

    assert parser.parsed_response == "prefixanswer"
    assert parser.parsed_thought == "private"


def test_streaming_parser_strips_leaked_stop_token_full():
    """llm(..., stop=["<|im_end|>", ...]) is supposed to fully suppress the
    stop string from streamed output, but it can leak through as a real
    text chunk (observed live: "hi" -> "hi<|im_end>" shown to the user)."""
    chat_tokens = []
    parser = StreamingThoughtParser(
        in_thought=False,
        thought_cb=lambda t: None,
        chat_cb=chat_tokens.append,
        publish_events=False,
    )

    parser.feed("hi<|im_end|>")

    assert parser.parsed_response == "hi"
    assert "<|im_end" not in "".join(chat_tokens)


def test_streaming_parser_strips_leaked_stop_token_truncated_variants():
    """The leak observed live was missing a character ("<|im_end>", not the
    full "<|im_end|>") -- cover the truncated forms specifically, not just
    the exact token string. flush() simulates generation actually ending
    right there (as it does live), which is what forces a still-ambiguous
    trailing fragment like "<|im_end|" (itself a valid prefix of the full
    token) to resolve rather than sit pending forever."""
    for leaked in ("<|im_end>", "<|im_end|", "<|im_start|>", "<|endoftext|>", "<|end_of_text>"):
        chat_tokens = []
        parser = StreamingThoughtParser(
            in_thought=False,
            thought_cb=lambda t: None,
            chat_cb=chat_tokens.append,
            publish_events=False,
        )
        parser.feed(f"hi{leaked}")
        parser.flush()
        assert parser.parsed_response == "hi", f"leaked form {leaked!r} was not stripped"


def test_streaming_parser_strips_leaked_stop_token_on_flush():
    """defer_after_think_close leaves the post-</think> remainder sitting in
    self.buffer until flush() is called explicitly (see llm_thread.py's
    dynamic-scheduling state transition) -- the leak-stripping needs to
    apply there too, not just to text emitted immediately within feed()."""
    parser = StreamingThoughtParser(
        in_thought=True,
        thought_cb=lambda t: None,
        chat_cb=lambda t: None,
        publish_events=False,
    )

    result = parser.feed("thought</think>hi<|im_end|>", defer_after_think_close=True)
    assert result.closed_think
    assert parser.parsed_response == ""  # remainder deferred, not yet emitted

    parser.flush()

    assert parser.parsed_response == "hi"


def test_streaming_parser_strips_leaked_stop_token_fragmented_across_chunks():
    """The actual live bug: llama.cpp streams "<|im_end|>" as several
    separate chunks -- observed exactly as feed("hi"), feed("<"), feed("|"),
    feed("im"), feed("_end"), feed(">\n") -- each individually far too small
    to match a whole-token regex. Fixing only whole-chunk leaks (the tests
    above) did NOT fix the real bug; the guard mechanism itself has to hold
    back a partial ChatML-token prefix the same way it already holds back a
    partial "<think>"/"</think>", or each fragment gets emitted immediately
    as soon as it stops looking like it's building toward <think>."""
    chat_tokens = []
    parser = StreamingThoughtParser(
        in_thought=False,
        thought_cb=lambda t: None,
        chat_cb=chat_tokens.append,
        publish_events=False,
    )

    for chunk in ("hi", "<", "|", "im", "_end", ">\n"):
        parser.feed(chunk)
    parser.flush()

    assert parser.parsed_response == "hi\n"
    assert "<" not in "".join(chat_tokens)
