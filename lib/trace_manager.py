"""Trace tree for hook execution debugging.

Provides structured tracing with nested spans for recording hook
execution flow. Each span tracks duration, child spans, and events.

Thread-local storage ensures span stacks do not collide across threads.

Usage:
    tm = TraceManager("my-session")
    with tm.start_span("phase_1"):
        tm.record("file_read", {"path": "/test.py"})
        with tm.start_span("sub_phase"):
            pass
    print(tm.to_json())
"""

from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass(frozen=True)
class TraceSpan:
    """An immutable snapshot of a completed trace span.

    Args:
        name: Human-readable span name.
        start_time: Monotonic timestamp when span started.
        duration_ms: Duration in milliseconds.
        children: Tuple of child spans (immutable).
        metadata: Additional metadata dict.
    """

    name: str
    start_time: float
    duration_ms: float
    children: tuple[TraceSpan, ...]
    metadata: dict[str, Any]


@dataclass
class _MutableSpan:
    """Internal mutable span used during recording.

    Converted to frozen TraceSpan when the span ends.
    """

    name: str
    start_time: float
    children: list[_MutableSpan] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_span(self, end_time: float) -> TraceSpan:
        """Convert to immutable TraceSpan with computed duration."""
        duration_ms = (end_time - self.start_time) * 1000.0
        return TraceSpan(
            name=self.name,
            start_time=self.start_time,
            duration_ms=duration_ms,
            children=tuple(c.to_span(end_time) for c in self.children),
            metadata={"events": list(self.events)},
        )


def _span_to_dict(span: TraceSpan) -> dict[str, Any]:
    """Recursively convert a TraceSpan to a serializable dict."""
    return {
        "name": span.name,
        "start_time": span.start_time,
        "duration_ms": span.duration_ms,
        "children": [_span_to_dict(c) for c in span.children],
        "events": span.metadata.get("events", []),
    }


class TraceManager:
    """Trace tree manager for hook execution debugging.

    Records nested spans with duration tracking and event recording.
    Uses thread-local storage for span stacks to be safe across threads.

    Args:
        session_name: Name for this trace session.
    """

    def __init__(self, session_name: str) -> None:
        self._session_name = session_name
        self._completed_spans: list[TraceSpan] = []
        self._lock = threading.Lock()
        self._local = threading.local()

    @property
    def session_name(self) -> str:
        """Return the session name."""
        return self._session_name

    def _get_stack(self) -> list[_MutableSpan]:
        """Get the thread-local span stack."""
        if not hasattr(self._local, "stack"):
            self._local.stack = []
        return self._local.stack  # type: ignore[no-any-return]

    @contextmanager
    def start_span(self, name: str) -> Generator[_MutableSpan, None, None]:
        """Start a new span as a context manager.

        If there is a current active span, the new span becomes its child.
        Otherwise it becomes a root span.

        Args:
            name: Human-readable name for the span.

        Yields:
            The mutable span object (for adding events).
        """
        stack = self._get_stack()
        span = _MutableSpan(name=name, start_time=time.monotonic())

        if stack:
            stack[-1].children.append(span)

        stack.append(span)
        try:
            yield span
        finally:
            stack.pop()
            if not stack:
                # Root span completed — convert and store
                end_time = time.monotonic()
                completed = span.to_span(end_time)
                with self._lock:
                    self._completed_spans.append(completed)

    def record(self, event_name: str, metadata: dict[str, Any]) -> None:
        """Record an event in the current active span.

        Args:
            event_name: Name of the event.
            metadata: Additional data for the event.
        """
        stack = self._get_stack()
        if stack:
            stack[-1].events.append({"name": event_name, "metadata": metadata})

    def to_dict(self) -> dict[str, Any]:
        """Serialize full trace tree to a dictionary.

        Returns:
            Dict with session_name and list of span dicts.
        """
        with self._lock:
            return {
                "session_name": self._session_name,
                "spans": [_span_to_dict(s) for s in self._completed_spans],
            }

    def to_json(self) -> str:
        """Serialize full trace tree to JSON string.

        Returns:
            JSON string representation of the trace.
        """
        return json.dumps(self.to_dict(), default=str)

    def reset(self) -> None:
        """Clear all completed spans."""
        with self._lock:
            self._completed_spans.clear()
