# THE HACKABLE AGENTIC LAYER
# Modify this file to control how Karl loops autonomously.
# This script is hot-reloaded on every agentic iteration -- no restart needed.

MAX_ITERATIONS = 20  # Generous cap -- loop runs until the model signals completion

COMPLETION_SIGNALS = [
    "FINAL ANSWER:",
    "[DONE]",
    "[END]",
    "[STOP]",
]


def should_continue(iteration: int, last_response: str) -> bool:
    """
    Stop condition. Return True to keep looping, False to stop.

    The loop runs until:
      - The model includes a completion signal in its response
      - OR we hit MAX_ITERATIONS
      - OR the user clicks Stop

    For long-context questions, the model will keep refining until
    it produces a final answer.
    """
    if iteration >= MAX_ITERATIONS:
        return False

    resp_upper = last_response.upper()

    # Stop on explicit completion signals
    for signal in COMPLETION_SIGNALS:
        if signal.upper() in resp_upper:
            return False

    # If the response is very short (model said nothing useful), stop
    if len(last_response.strip()) < 20 and iteration > 0:
        return False

    return True


def build_next_prompt(last_response: str, iteration: int) -> str:
    """
    Content of the next USER turn injected into the agentic loop.

    The goal is to push the model toward a complete, high-quality answer.
    On early iterations: ask it to continue and deepen.
    On later iterations: push it toward a final conclusion.
    """
    if iteration == 0:
        return (
            "Good start. Continue your reasoning -- go deeper into the details "
            "and fill in any gaps. Do not repeat yourself."
        )

    if iteration < 5:
        return (
            f"[Iteration {iteration + 1}] Continue. Expand on any points that need "
            "more detail. If you have covered everything thoroughly, "
            "write 'FINAL ANSWER:' followed by your complete, clean conclusion."
        )

    # Push harder toward conclusion on later iterations
    return (
        f"[Iteration {iteration + 1}] You have been working on this for {iteration + 1} "
        "iterations. Consolidate everything into your best final answer now. "
        "Write 'FINAL ANSWER:' followed by your complete response."
    )
