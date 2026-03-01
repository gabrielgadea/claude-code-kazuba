"""Tests for modules/config-hypervisor/src/hypervisor_bridge.py — Phase 15."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Load hypervisor_bridge from hyphenated directory using importlib
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_HB_PATH = _PROJECT_ROOT / "modules" / "config-hypervisor" / "src" / "hypervisor_bridge.py"
_spec = importlib.util.spec_from_file_location("hypervisor_bridge", _HB_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules.setdefault("hypervisor_bridge", _mod)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

HypervisorBridge = _mod.HypervisorBridge
LearningEvent = _mod.LearningEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockResult:
    """Minimal mock for ExecutionResult."""

    def __init__(self, success: bool = True, duration_ms: int = 100) -> None:
        self.success = success
        self.duration_ms = duration_ms


# ---------------------------------------------------------------------------
# LearningEvent
# ---------------------------------------------------------------------------


def test_learning_event_creation():
    """LearningEvent must be constructable with required fields."""
    event = LearningEvent(event_type="phase_start", phase_id=1)
    assert event.event_type == "phase_start"
    assert event.phase_id == 1
    assert event.duration_ms == 0
    assert event.success is False
    assert isinstance(event.metadata, dict)
    assert isinstance(event.timestamp, str)


def test_learning_event_frozen():
    """LearningEvent must be immutable (frozen=True)."""
    event = LearningEvent(event_type="phase_end", phase_id=2, success=True)
    with pytest.raises((TypeError, AttributeError, Exception)):
        event.success = False  # type: ignore[misc]


def test_learning_event_to_dict():
    """LearningEvent.to_dict must return a serializable dictionary."""
    event = LearningEvent(
        event_type="phase_end",
        phase_id=5,
        duration_ms=200,
        success=True,
        metadata={"key": "value"},
    )
    d = event.to_dict()
    assert d["event_type"] == "phase_end"
    assert d["phase_id"] == 5
    assert d["duration_ms"] == 200
    assert d["success"] is True
    assert d["metadata"] == {"key": "value"}
    assert "timestamp" in d


# ---------------------------------------------------------------------------
# HypervisorBridge — init
# ---------------------------------------------------------------------------


def test_bridge_init():
    """HypervisorBridge must initialise with enabled=True by default."""
    bridge = HypervisorBridge()
    assert bridge.enabled is True
    assert bridge.get_history() == []


def test_bridge_disabled():
    """HypervisorBridge with enabled=False must record nothing."""
    bridge = HypervisorBridge(enabled=False)
    assert bridge.enabled is False

    bridge.record_phase_start(1)
    bridge.record_phase_end(1, _MockResult(success=True))

    assert len(bridge.get_history()) == 0


# ---------------------------------------------------------------------------
# HypervisorBridge — recording
# ---------------------------------------------------------------------------


def test_bridge_record_phase_start():
    """record_phase_start must append a phase_start event to history."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(3)
    history = bridge.get_history()
    assert len(history) == 1
    assert history[0].event_type == "phase_start"
    assert history[0].phase_id == 3


def test_bridge_record_phase_end_success():
    """record_phase_end with success=True must add a phase_end event."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(4)
    bridge.record_phase_end(4, _MockResult(success=True, duration_ms=250))

    events = bridge.get_history()
    end_events = [e for e in events if e.event_type == "phase_end"]
    assert len(end_events) == 1
    assert end_events[0].success is True
    assert end_events[0].phase_id == 4


def test_bridge_record_phase_end_failure():
    """record_phase_end with success=False must add a phase_failed event."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(7)
    bridge.record_phase_end(7, _MockResult(success=False, duration_ms=50))

    events = bridge.get_history()
    failed_events = [e for e in events if e.event_type == "phase_failed"]
    assert len(failed_events) == 1
    assert failed_events[0].success is False


def test_bridge_record_phase_end_dict_result():
    """record_phase_end must accept a dict as the result argument."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(9)
    bridge.record_phase_end(9, {"success": True, "duration_ms": 100})

    events = bridge.get_history()
    assert any(e.event_type == "phase_end" for e in events)


# ---------------------------------------------------------------------------
# HypervisorBridge — history
# ---------------------------------------------------------------------------


def test_bridge_get_history():
    """get_history must return all events across multiple phases."""
    bridge = HypervisorBridge()
    for i in range(1, 4):
        bridge.record_phase_start(i)
        bridge.record_phase_end(i, _MockResult(success=True))

    history = bridge.get_history()
    # 3 start + 3 end events
    assert len(history) == 6

    start_events = [e for e in history if e.event_type == "phase_start"]
    end_events = [e for e in history if e.event_type == "phase_end"]
    assert len(start_events) == 3
    assert len(end_events) == 3


def test_bridge_get_history_returns_copy():
    """get_history must return a copy that doesn't mutate internal state."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(1)
    history = bridge.get_history()
    history.clear()
    # Internal history must be unchanged
    assert len(bridge.get_history()) == 1


# ---------------------------------------------------------------------------
# HypervisorBridge — export_jsonl
# ---------------------------------------------------------------------------


def test_bridge_export_jsonl(tmp_path):
    """export_jsonl must write valid JSON lines and return the correct count."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(1)
    bridge.record_phase_end(1, _MockResult(success=True, duration_ms=100))
    bridge.record_phase_start(2)
    bridge.record_phase_end(2, _MockResult(success=False, duration_ms=50))

    output = tmp_path / "events.jsonl"
    count = bridge.export_jsonl(output)

    assert count == 4  # 2 starts + 2 ends
    lines = output.read_text().splitlines()
    assert len(lines) == 4

    for line in lines:
        parsed = json.loads(line)
        assert "event_type" in parsed
        assert "phase_id" in parsed
        assert "timestamp" in parsed


def test_bridge_export_jsonl_empty(tmp_path):
    """export_jsonl with no events must write an empty file and return 0."""
    bridge = HypervisorBridge()
    output = tmp_path / "empty.jsonl"
    count = bridge.export_jsonl(output)

    assert count == 0
    assert output.exists()
    assert output.read_text() == ""


# ---------------------------------------------------------------------------
# HypervisorBridge — additional coverage
# ---------------------------------------------------------------------------


def test_bridge_record_phase_end_fallback_duration():
    """record_phase_end must calculate duration from start time when duration_ms=0."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(10)
    # Pass result with duration_ms=0 to trigger fallback calculation
    bridge.record_phase_end(10, _MockResult(success=True, duration_ms=0))

    events = bridge.get_history()
    end_events = [e for e in events if e.event_type == "phase_end"]
    assert len(end_events) == 1
    # Duration may be 0 or small but must be non-negative
    assert end_events[0].duration_ms >= 0


def test_bridge_record_phase_end_unknown_result_type():
    """record_phase_end must handle result without known attributes gracefully."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(11)
    # Pass an integer — no .success, not a dict
    bridge.record_phase_end(11, 42)  # type: ignore[arg-type]

    events = bridge.get_history()
    # Should record a phase_failed event (success=False fallback)
    end_events = [e for e in events if e.event_type == "phase_failed"]
    assert len(end_events) == 1


def test_bridge_get_events_for_phase():
    """get_events_for_phase must return only events for the specified phase."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(1)
    bridge.record_phase_start(2)
    bridge.record_phase_end(1, _MockResult(success=True))
    bridge.record_phase_end(2, _MockResult(success=False))

    phase1_events = bridge.get_events_for_phase(1)
    phase2_events = bridge.get_events_for_phase(2)

    assert all(e.phase_id == 1 for e in phase1_events)
    assert all(e.phase_id == 2 for e in phase2_events)
    assert len(phase1_events) == 2  # start + end


def test_bridge_get_stats():
    """get_stats must return accurate aggregate statistics."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(1)
    bridge.record_phase_end(1, _MockResult(success=True))
    bridge.record_phase_start(2)
    bridge.record_phase_end(2, _MockResult(success=False))

    stats = bridge.get_stats()
    assert stats["total_events"] == 4
    assert stats["phases_started"] == 2
    assert stats["phases_succeeded"] == 1
    assert stats["phases_failed"] == 1


def test_bridge_clear():
    """clear must remove all events and reset internal state."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(1)
    bridge.record_phase_end(1, _MockResult(success=True))

    assert len(bridge.get_history()) == 2

    bridge.clear()

    assert bridge.get_history() == []
    stats = bridge.get_stats()
    assert stats["total_events"] == 0


def test_bridge_make_event_with_extra_kwargs():
    """_make_event must include extra kwargs in the metadata dict."""
    bridge = HypervisorBridge()
    event = bridge._make_event(
        "custom_event",
        phase_id=99,
        success=True,
        duration_ms=500,
        source="unit-test",
    )
    assert event.event_type == "custom_event"
    assert event.phase_id == 99
    assert event.success is True
    assert event.metadata.get("source") == "unit-test"


def test_bridge_export_jsonl_creates_parent_dirs(tmp_path):
    """export_jsonl must create parent directories if they don't exist."""
    bridge = HypervisorBridge()
    bridge.record_phase_start(5)

    nested_path = tmp_path / "a" / "b" / "c" / "events.jsonl"
    count = bridge.export_jsonl(nested_path)

    assert count == 1
    assert nested_path.exists()
