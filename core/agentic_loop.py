# THE HACKABLE AGENTIC LAYER
# Modify this file to control how Karl loops autonomously.
# This script is hot-reloaded on every agentic run — no restart needed.

MAX_ITERATIONS = 10  # Hard cap to prevent infinite loops

_COMPLETION_PHRASES = [
    "final answer:",
    "[done]", "[end]", "[stop]",
    "task complete", "task completed",
    "i have completed", "i've completed",
    "the answer is complete",
    "in conclusion,", "to summarize,",
    "therefore, the answer is",
    "the solution is",
]


def should_continue(iteration: int, last_response: str) -> bool:
    """
    Return True to keep looping, False to stop.
    Checks for natural completion signals (case-insensitive).
    """
    if iteration >= MAX_ITERATIONS:
        return False
    lower = last_response.lower().strip()
    return not any(phrase in lower for phrase in _COMPLETION_PHRASES)


def build_next_prompt(last_response: str, iteration: int) -> str:
    """
    Builds the next USER turn injected into the agentic loop.
    Gets progressively more directive as iterations increase.
    """
    remaining = MAX_ITERATIONS - iteration

    if iteration == 1:
        return (
            "Review your response above carefully. "
            "Is the task fully and correctly solved? "
            "If yes, restate the solution clearly and begin with 'FINAL ANSWER: '. "
            "If not, fix any gaps or errors, then end with 'FINAL ANSWER: <solution>'."
        )

    if remaining <= 2:
        return (
            f"[Step {iteration + 1}/{MAX_ITERATIONS}] URGENT: only {remaining} steps left. "
            f"You MUST provide your best complete answer NOW. "
            f"Begin your response with 'FINAL ANSWER: ' followed by the full solution."
        )

    return (
        f"[Step {iteration + 1}/{MAX_ITERATIONS}] "
        f"Continue working toward a complete solution. "
        f"Once fully solved, respond with 'FINAL ANSWER: ' followed by your complete answer."
    )
