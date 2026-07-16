import core.agentic_loop as agentic_loop


def test_should_continue_stops_on_explicit_final_answer():
    assert not agentic_loop.should_continue(
        1,
        "FINAL ANSWER: The clean final response.",
    )


def test_should_continue_does_not_stop_on_ordinary_summary_phrase():
    assert agentic_loop.should_continue(
        1,
        "In summary, this intermediate pass has identified the main tradeoffs.",
    )
