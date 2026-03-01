"""Tests for lib.event_bus — Phase 11 shared infrastructure."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from claude_code_kazuba.event_bus import Event, EventBus


class TestEvent:
    """Tests for Event dataclass."""

    def test_event_creation(self) -> None:
        ev = Event(event_type="test", data={"k": "v"}, timestamp=1000.0, source="src")
        assert ev.event_type == "test"
        assert ev.data == {"k": "v"}
        assert ev.timestamp == 1000.0
        assert ev.source == "src"

    def test_event_is_frozen(self) -> None:
        ev = Event(event_type="test", data={}, timestamp=0.0, source="")
        with pytest.raises(AttributeError):
            ev.event_type = "other"  # type: ignore[misc]

    def test_event_source(self) -> None:
        ev = Event(event_type="test", data={}, timestamp=0.0, source="my-hook")
        assert ev.source == "my-hook"

    def test_event_timestamp(self) -> None:
        now = time.time()
        ev = Event(event_type="test", data={}, timestamp=now, source="")
        assert ev.timestamp == now


class TestEventBus:
    """Tests for EventBus class."""

    def test_subscribe_and_publish(self) -> None:
        bus = EventBus()
        received: list[Event] = []
        bus.subscribe("test.event", received.append)
        bus.publish("test.event", {"key": "val"})
        assert len(received) == 1
        assert received[0].event_type == "test.event"
        assert received[0].data == {"key": "val"}

    def test_multiple_subscribers(self) -> None:
        bus = EventBus()
        r1: list[Event] = []
        r2: list[Event] = []
        bus.subscribe("evt", r1.append)
        bus.subscribe("evt", r2.append)
        bus.publish("evt", {})
        assert len(r1) == 1
        assert len(r2) == 1

    def test_unsubscribe(self) -> None:
        bus = EventBus()
        received: list[Event] = []
        handler = received.append
        bus.subscribe("evt", handler)
        bus.unsubscribe("evt", handler)
        bus.publish("evt", {})
        assert len(received) == 0

    def test_priority_ordering(self) -> None:
        bus = EventBus()
        order: list[int] = []
        bus.subscribe("evt", lambda e: order.append(3), priority=3)
        bus.subscribe("evt", lambda e: order.append(1), priority=1)
        bus.subscribe("evt", lambda e: order.append(2), priority=2)
        bus.publish("evt", {})
        assert order == [1, 2, 3]

    def test_publish_no_subscribers(self) -> None:
        bus = EventBus()
        # Should not raise
        bus.publish("unknown.event", {"data": 42})

    def test_event_data_passed(self) -> None:
        bus = EventBus()
        received: list[Event] = []
        bus.subscribe("evt", received.append)
        bus.publish("evt", {"x": 1, "y": 2}, source="test-src")
        assert received[0].data == {"x": 1, "y": 2}
        assert received[0].source == "test-src"

    def test_event_types_property(self) -> None:
        bus = EventBus()
        bus.subscribe("type_a", lambda e: None)
        bus.subscribe("type_b", lambda e: None)
        assert bus.event_types == {"type_a", "type_b"}

    def test_subscribers_list(self) -> None:
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe("evt", handler)
        subs = bus.subscribers("evt")
        assert len(subs) == 1

    def test_clear_all(self) -> None:
        bus = EventBus()
        bus.subscribe("a", lambda e: None)
        bus.subscribe("b", lambda e: None)
        bus.clear()
        assert bus.event_types == set()

    def test_error_in_handler_continues(self) -> None:
        bus = EventBus()
        call_order: list[str] = []

        def bad_handler(e: Event) -> None:
            call_order.append("bad")
            msg = "handler error"
            raise RuntimeError(msg)

        def good_handler(e: Event) -> None:
            call_order.append("good")

        bus.subscribe("evt", bad_handler, priority=1)
        bus.subscribe("evt", good_handler, priority=2)
        bus.publish("evt", {})
        assert "bad" in call_order
        assert "good" in call_order

    def test_thread_safety(self) -> None:
        bus = EventBus()
        counter: list[int] = []
        lock = threading.Lock()

        def handler(e: Event) -> None:
            with lock:
                counter.append(1)

        bus.subscribe("evt", handler)

        threads = []
        for _ in range(20):
            t = threading.Thread(target=lambda: bus.publish("evt", {}))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        assert len(counter) == 20

    def test_publish_returns_none(self) -> None:
        bus = EventBus()
        result = bus.publish("evt", {})
        assert result is None

    def test_subscribe_same_handler_twice(self) -> None:
        bus = EventBus()
        received: list[Event] = []
        bus.subscribe("evt", received.append)
        bus.subscribe("evt", received.append)
        bus.publish("evt", {})
        # Handler registered twice means called twice
        assert len(received) == 2

    def test_publish_async(self) -> None:
        bus = EventBus()
        received: list[Event] = []
        lock = threading.Lock()

        def handler(e: Event) -> None:
            with lock:
                received.append(e)

        bus.subscribe("evt", handler)
        bus.publish_async("evt", {"async": True})
        # Give thread pool time to execute
        time.sleep(0.1)
        assert len(received) == 1
        assert received[0].data == {"async": True}

    def test_unsubscribe_nonexistent(self) -> None:
        bus = EventBus()
        # Should not raise
        bus.unsubscribe("nonexistent", lambda e: None)
