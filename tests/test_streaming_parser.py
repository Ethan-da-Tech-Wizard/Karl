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
