from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.engine.event_broker import EventBroker


OPEN_GUARDS = ["<", "<t", "<th", "<thi", "<thin", "<think"]
CLOSE_GUARDS = ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]


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
        if not token:
            return
        self._thought_cb(token)
        if self._publish_events:
            EventBroker.get_instance().publish("tokens:thought", {"token": token})
        self.parsed_thought += token

    def _emit_chat(self, token: str) -> None:
        if not token:
            return
        self._chat_cb(token)
        if self._publish_events:
            EventBroker.get_instance().publish("tokens:chat", {"token": token})
        self.parsed_response += token
