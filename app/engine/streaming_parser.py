from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from app.engine.event_broker import EventBroker


_THINK_TAGS = ["<think>", "</think>"]

# ChatML control tokens (stop sequences passed to llm(..., stop=[...]) in
# llm_thread.py/agentic_thread.py). llama.cpp streams generation a few bytes
# at a time, and these can arrive fragmented across many separate chunks --
# e.g. "<|im_end|>" observed live as five separate feed() calls: "<", "|",
# "im", "_end", ">\n". A regex over each individual chunk can never catch
# that (no single chunk contains the full pattern), so the guard mechanism
# below has to hold back anything that *might still become* one of these
# tokens, the same way it already holds back a partial "<think>"/"</think>",
# until the full token (or a clear divergence from it) is visible.
_CHATML_CONTROL_TOKENS = ["<|im_end|>", "<|im_start|>", "<|endoftext|>", "<|end_of_text|>"]

_PROTECTED_SEQUENCES = _THINK_TAGS + _CHATML_CONTROL_TOKENS

# Every proper prefix of every protected sequence, e.g. for "<|im_end|>":
# "<", "<|", "<|i", "<|im", "<|im_", "<|im_e", "<|im_en", "<|im_end", "<|im_end|".
# If the buffer's tail is one of these, more incoming text could still turn
# it into a full protected sequence, so emission must wait.
OPEN_GUARDS = sorted({seq[:i] for seq in _PROTECTED_SEQUENCES for i in range(1, len(seq))})
CLOSE_GUARDS = OPEN_GUARDS

# Complete (or truncated-by-one -- see the leak this was written for, which
# dropped exactly one character) forms of the control tokens, stripped from
# whatever's about to be emitted once the buffer has grown enough to no
# longer be a mere prefix.
_SPECIAL_TOKEN_LEAK_RE = re.compile(
    r"<\|(?:im_end|im_start|endoftext|end_of_text)\|?>?"
)


def _strip_special_token_leaks(text: str) -> str:
    return _SPECIAL_TOKEN_LEAK_RE.sub("", text)


@dataclass
class ParserFeedResult:
    closed_think: bool = False


class StreamingThoughtParser:
    """Incremental router for DeepSeek-style <think> streams."""

    def __init__(
        self,
        *,
        in_thought: bool,
        thought_cb: Callable[[str], None],
        chat_cb: Callable[[str], None],
        publish_events: bool = True,
    ):
        self.in_thought = in_thought
        self.buffer = ""
        self.parsed_thought = ""
        self.parsed_response = ""
        self._thought_cb = thought_cb
        self._chat_cb = chat_cb
        self._publish_events = publish_events

    def feed(self, text: str, defer_after_think_close: bool = False) -> ParserFeedResult:
        self.buffer += text
        closed_think = False

        if "<think>" in self.buffer and not self.in_thought:
            self.in_thought = True
            pre_think = self.buffer.split("<think>")[0]
            if pre_think:
                self._emit_chat(pre_think)
            self.buffer = self.buffer.split("<think>", 1)[1]

        if self.in_thought and "</think>" in self.buffer:
            self.in_thought = False
            thought, remainder = self.buffer.split("</think>", 1)
            if thought:
                self._emit_thought(thought)
            self.buffer = remainder
            closed_think = True
            if defer_after_think_close:
                return ParserFeedResult(closed_think=True)

        if self.in_thought:
            if not any(self.buffer.endswith(s) for s in CLOSE_GUARDS):
                self._emit_thought(self.buffer)
                self.buffer = ""
        else:
            if not any(self.buffer.endswith(s) for s in OPEN_GUARDS):
                self._emit_chat(self.buffer)
                self.buffer = ""

        return ParserFeedResult(closed_think=closed_think)

    def flush(self) -> None:
        if not self.buffer:
            return
        if self.in_thought:
            self._emit_thought(self.buffer)
        else:
            self._emit_chat(self.buffer)
        self.buffer = ""

    def _emit_thought(self, token: str) -> None:
        token = _strip_special_token_leaks(token)
        if not token:
            return
        self._thought_cb(token)
        if self._publish_events:
            EventBroker.get_instance().publish("tokens:thought", {"token": token})
        self.parsed_thought += token

    def _emit_chat(self, token: str) -> None:
        token = _strip_special_token_leaks(token)
        if not token:
            return
        self._chat_cb(token)
        if self._publish_events:
            EventBroker.get_instance().publish("tokens:chat", {"token": token})
        self.parsed_response += token
