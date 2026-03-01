"""Pub/sub event bus for decoupled inter-hook communication.

Provides synchronous and asynchronous event dispatching with priority
ordering and error isolation. Handlers that raise exceptions are logged
and skipped — remaining handlers still execute.

Thread-safe via threading.Lock for subscription management.

Usage:
    bus = EventBus()
    bus.subscribe("hook.completed", my_handler, priority=0)
    bus.publish("hook.completed", {"hook_name": "validator"}, source="system")

    # Async dispatch (returns immediately):
    bus.publish_async("hook.started", {"phase": 1})

Priority ordering: lower number = higher priority (0 = first).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Type alias for event handler functions
EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """An immutable event dispatched through the event bus.

    Args:
        event_type: String identifier for the event category.
        data: Arbitrary payload data.
        timestamp: Unix timestamp when the event was created.
        source: Identifier of the event producer.
    """

    event_type: str
    data: dict[str, Any]
    timestamp: float
    source: str


@dataclass
class _Subscription:
    """Internal subscription record with priority ordering."""

    handler: EventHandler
    priority: int


class EventBus:
    """Thread-safe pub/sub event bus with priority ordering.

    Handlers are dispatched synchronously in priority order (lower = first).
    If a handler raises an exception, the error is logged and the next
    handler is called — no exception propagates to the publisher.

    For non-blocking dispatch, use publish_async() which runs handlers
    in a thread pool.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[_Subscription]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        priority: int = 0,
    ) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Event type string to listen for.
            handler: Callable that receives an Event object.
            priority: Dispatch priority (lower = earlier). Default 0.
        """
        sub = _Subscription(handler=handler, priority=priority)
        with self._lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            self._subscriptions[event_type].append(sub)
            self._subscriptions[event_type].sort(key=lambda s: s.priority)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler from an event type.

        If the handler is not found, this is a no-op.

        Args:
            event_type: Event type string.
            handler: Handler to remove.
        """
        with self._lock:
            if event_type not in self._subscriptions:
                return
            self._subscriptions[event_type] = [
                s for s in self._subscriptions[event_type] if s.handler is not handler
            ]
            if not self._subscriptions[event_type]:
                del self._subscriptions[event_type]

    def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        source: str = "",
    ) -> None:
        """Dispatch event to all subscribers synchronously, ordered by priority.

        If a handler raises, the error is logged and remaining handlers
        continue to execute.

        Args:
            event_type: Event type string.
            data: Payload data dict.
            source: Identifier of the event producer.
        """
        event = Event(
            event_type=event_type,
            data=data,
            timestamp=time.time(),
            source=source,
        )
        with self._lock:
            subs = list(self._subscriptions.get(event_type, []))

        for sub in subs:
            try:
                sub.handler(event)
            except Exception:
                logger.exception(
                    "Handler %r raised for event '%s'",
                    sub.handler,
                    event_type,
                )

    def publish_async(
        self,
        event_type: str,
        data: dict[str, Any],
        source: str = "",
    ) -> None:
        """Dispatch event to subscribers in a thread pool (non-blocking).

        Args:
            event_type: Event type string.
            data: Payload data dict.
            source: Identifier of the event producer.
        """
        self._executor.submit(self.publish, event_type, data, source)

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._subscriptions.clear()

    def subscribers(self, event_type: str) -> list[EventHandler]:
        """Return list of handlers for an event type.

        Args:
            event_type: Event type string.

        Returns:
            List of registered handler callables.
        """
        with self._lock:
            subs = self._subscriptions.get(event_type, [])
            return [s.handler for s in subs]

    @property
    def event_types(self) -> set[str]:
        """Return set of all event types that have subscribers."""
        with self._lock:
            return set(self._subscriptions.keys())
