"""
Local span tracing for Karl.

This module intentionally stays dependency-free. It records hierarchical spans
with contextvars so traces remain isolated across worker threads and async tasks,
then writes completed root traces as JSONL for offline inspection.
"""

from __future__ import annotations

import contextvars
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Tracer:
    """Context-local span manager that persists completed root traces."""

    def __init__(self, trace_dir: str | os.PathLike[str] = "data/logs/traces") -> None:
        self.trace_dir = Path(trace_dir)
        self._stack: contextvars.ContextVar[list[Span]] = contextvars.ContextVar(
            "karl_span_stack",
            default=[],
        )

    def span(self, name: str, attributes: dict[str, Any] | None = None) -> "Span":
        return Span(name, attributes=attributes, tracer=self)

    def _push(self, span: "Span") -> None:
        stack = list(self._stack.get())
        stack.append(span)
        self._stack.set(stack)

    def _pop(self, span: "Span") -> None:
        stack = list(self._stack.get())
        if stack and stack[-1] is span:
            stack.pop()
        elif span in stack:
            stack.remove(span)
        self._stack.set(stack)

    def current_span(self) -> "Span | None":
        stack = self._stack.get()
        return stack[-1] if stack else None

    def _record_root(self, span: "Span") -> None:
        """Append a completed root span to today's JSONL file.

        One file per UTC day: ``spans_YYYY-MM-DD.jsonl``.
        No file locking — concurrent root spans from different threads may
        interleave their writes.  Each span is a single line so partial
        interleaving produces at most a corrupted line, not a corrupted file.
        """
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        path = self.trace_dir / f"spans_{datetime.now(timezone.utc).date().isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(span.to_dict(), ensure_ascii=False) + "\n")


DEFAULT_TRACER = Tracer()


class Span:
    """Context manager representing one timed operation in a trace tree."""

    def __init__(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self.name = name
        self.attributes = dict(attributes or {})
        self.tracer = tracer or DEFAULT_TRACER
        self.trace_id: str = ""
        self.span_id: str = ""
        self.parent_span_id: str | None = None
        self.start_time: str = ""
        self.duration_sec: float = 0.0
        self.status = "OK"
        self.error: dict[str, str] | None = None
        self.children: list[Span] = []
        self._parent: Span | None = None
        self._start_perf = 0.0

    def __enter__(self) -> "Span":
        self._parent = self.tracer.current_span()
        self.trace_id = self._parent.trace_id if self._parent else str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.parent_span_id = self._parent.span_id if self._parent else None
        self.start_time = datetime.now(timezone.utc).isoformat()
        self._start_perf = time.perf_counter()
        if self._parent is not None:
            self._parent.children.append(self)
        self.tracer._push(self)
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.duration_sec = round(time.perf_counter() - self._start_perf, 6)
        if exc_type is not None:
            self.status = "ERROR"
            self.error = {
                "type": exc_type.__name__,
                "message": str(exc),
            }
        self.tracer._pop(self)
        if self._parent is None:
            self.tracer._record_root(self)
        return False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "start_time": self.start_time,
            "duration_sec": self.duration_sec,
            "status": self.status,
            "attributes": self.attributes,
            "children": [child.to_dict() for child in self.children],
        }
        if self.parent_span_id is not None:
            payload["parent_span_id"] = self.parent_span_id
        if self.error is not None:
            payload["error"] = self.error
        return payload
