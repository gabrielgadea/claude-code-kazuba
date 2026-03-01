"""Tests for lib.trace_manager — Phase 11 shared infrastructure."""

from __future__ import annotations

import json
import threading
import time

import pytest

from lib.trace_manager import TraceManager, TraceSpan


class TestTraceSpan:
    """Tests for the TraceSpan dataclass."""

    def test_create_span(self) -> None:
        span = TraceSpan(
            name="test",
            start_time=1000.0,
            duration_ms=50.0,
            children=(),
            metadata={},
        )
        assert span.name == "test"
        assert span.start_time == 1000.0
        assert span.duration_ms == 50.0

    def test_span_is_frozen(self) -> None:
        span = TraceSpan(
            name="test",
            start_time=0.0,
            duration_ms=0.0,
            children=(),
            metadata={},
        )
        with pytest.raises(AttributeError):
            span.name = "other"  # type: ignore[misc]

    def test_span_with_metadata(self) -> None:
        span = TraceSpan(
            name="test",
            start_time=0.0,
            duration_ms=0.0,
            children=(),
            metadata={"key": "value"},
        )
        assert span.metadata == {"key": "value"}


class TestTraceManager:
    """Tests for the TraceManager class."""

    def test_create_trace_manager(self) -> None:
        tm = TraceManager("test-session")
        assert tm.session_name == "test-session"

    def test_session_name(self) -> None:
        tm = TraceManager("my-session")
        assert tm.session_name == "my-session"

    def test_start_and_end_span(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("op1"):
            pass
        result = tm.to_dict()
        assert len(result["spans"]) == 1
        assert result["spans"][0]["name"] == "op1"

    def test_nested_spans(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("parent"):
            with tm.start_span("child"):
                pass
        result = tm.to_dict()
        assert len(result["spans"]) == 1
        parent = result["spans"][0]
        assert parent["name"] == "parent"
        assert len(parent["children"]) == 1
        assert parent["children"][0]["name"] == "child"

    def test_span_duration_tracked(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("slow"):
            time.sleep(0.02)
        result = tm.to_dict()
        duration = result["spans"][0]["duration_ms"]
        assert duration >= 15.0  # At least 15ms

    def test_record_event(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("op"):
            tm.record("file_read", {"path": "/test.py"})
        result = tm.to_dict()
        span = result["spans"][0]
        assert len(span["events"]) == 1
        assert span["events"][0]["name"] == "file_read"
        assert span["events"][0]["metadata"] == {"path": "/test.py"}

    def test_to_dict_structure(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("op"):
            pass
        result = tm.to_dict()
        assert "session_name" in result
        assert "spans" in result
        assert result["session_name"] == "test"

    def test_to_json_valid(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("op"):
            tm.record("ev", {"key": "val"})
        json_str = tm.to_json()
        parsed = json.loads(json_str)
        assert parsed["session_name"] == "test"

    def test_reset_clears_spans(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("op"):
            pass
        assert len(tm.to_dict()["spans"]) == 1
        tm.reset()
        assert len(tm.to_dict()["spans"]) == 0

    def test_context_manager_span(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("ctx") as span_ctx:
            assert span_ctx is not None
        result = tm.to_dict()
        assert result["spans"][0]["name"] == "ctx"

    def test_metadata_in_span(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("op"):
            tm.record("event1", {"a": 1})
            tm.record("event2", {"b": 2})
        result = tm.to_dict()
        assert len(result["spans"][0]["events"]) == 2

    def test_empty_trace(self) -> None:
        tm = TraceManager("test")
        result = tm.to_dict()
        assert result["spans"] == []

    def test_multiple_root_spans(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("first"):
            pass
        with tm.start_span("second"):
            pass
        result = tm.to_dict()
        assert len(result["spans"]) == 2
        assert result["spans"][0]["name"] == "first"
        assert result["spans"][1]["name"] == "second"

    def test_span_name_preserved(self) -> None:
        tm = TraceManager("test")
        with tm.start_span("my-specific-name"):
            pass
        result = tm.to_dict()
        assert result["spans"][0]["name"] == "my-specific-name"

    def test_thread_local_spans(self) -> None:
        tm = TraceManager("test")
        results: list[dict[str, str]] = []

        def worker(name: str) -> None:
            with tm.start_span(name):
                time.sleep(0.01)
            results.append({"name": name})

        t1 = threading.Thread(target=worker, args=("t1",))
        t2 = threading.Thread(target=worker, args=("t2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2
        trace = tm.to_dict()
        span_names = {s["name"] for s in trace["spans"]}
        assert "t1" in span_names
        assert "t2" in span_names
