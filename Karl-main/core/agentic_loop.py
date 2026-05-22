# THE HACKABLE AGENTIC LAYER
# Modify this file to control how Karl loops autonomously.
# This script is hot-reloaded on every agentic run — no restart needed.

MAX_ITERATIONS = 5  # Hard cap to prevent infinite loops

def should_continue(iteration: int, last_response: str) -> bool:
    """
    The stop condition. Karl calls this after every iteration.
    Return True to keep looping. Return False to stop.

    Ideas to try:
      - return "DONE" not in last_response
      - return iteration < 3
      - return len(last_response) > 50 and iteration < MAX_ITERATIONS
    """
    if iteration >= MAX_ITERATIONS:
        return False
    # Stop if the model signals it is finished
    stop_signals = ["[DONE]", "[END]", "[STOP]", "FINAL ANSWER:"]
    for signal in stop_signals:
        if signal in last_response:
            return False
    return True


def build_next_prompt(last_response: str, iteration: int) -> str:
    """
    Builds the content of the next USER turn in the agentic loop.
    This message is appended to the chat history and sent back to Karl.

    Ideas to try:
      - Critique the previous answer: "What is wrong with your last answer?"
      - Refine: "Improve on your previous response."
      - Chain of thought: "Continue your reasoning from where you left off."
    """
    return (
        f"[Iteration {iteration + 1}] "
        f"Reflect on your previous response and either refine it or conclude with 'FINAL ANSWER:' "
        f"if you are satisfied with your answer."
    )
