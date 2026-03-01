"""Tests for modules/rlm/src/working_memory.py — WorkingMemory."""

from __future__ import annotations

import time

import pytest

from modules.rlm.src.models import MemoryEntry
from modules.rlm.src.working_memory import WorkingMemory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_entry(
    content: str = "test content",
    importance: float = 0.5,
    tags: list[str] | None = None,
    entry_id: str | None = None,
) -> MemoryEntry:
    kwargs: dict[str, object] = {
        "content": content,
        "importance": importance,
        "tags": tuple(tags or []),
    }
    if entry_id is not None:
        kwargs["id"] = entry_id
    return MemoryEntry(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_add_and_retrieve_entry() -> None:
    mem = WorkingMemory(capacity=10)
    entry = make_entry("hello", entry_id="e1")
    eid = mem.add(entry)
    assert eid == "e1"
    retrieved = mem.get("e1")
    assert retrieved is not None
    assert retrieved.content == "hello"


def test_get_unknown_returns_none() -> None:
    mem = WorkingMemory(capacity=10)
    assert mem.get("nonexistent") is None


def test_get_updates_access_count() -> None:
    mem = WorkingMemory(capacity=10)
    entry = make_entry("data", entry_id="e1")
    mem.add(entry)
    retrieved = mem.get("e1")
    assert retrieved is not None
    assert retrieved.access_count == 1


def test_eviction_when_capacity_exceeded() -> None:
    mem = WorkingMemory(capacity=3)
    for i in range(5):
        mem.add(make_entry(f"content {i}", importance=0.5, entry_id=f"e{i}"))
    assert mem.size() <= 3


def test_high_importance_survives_eviction() -> None:
    mem = WorkingMemory(capacity=3)
    # Add 3 low-importance entries first
    for i in range(3):
        mem.add(make_entry(f"low {i}", importance=0.1, entry_id=f"low{i}"))
    # Add one high-importance entry (should evict a low-importance one)
    high_entry = make_entry("critical", importance=1.0, entry_id="high")
    time.sleep(0.01)  # ensure timestamp differs
    mem.add(high_entry)
    assert mem.contains("high"), "High-importance entry should survive eviction"


def test_remove_existing_entry() -> None:
    mem = WorkingMemory(capacity=10)
    mem.add(make_entry("data", entry_id="e1"))
    result = mem.remove("e1")
    assert result is True
    assert mem.get("e1") is None


def test_remove_nonexistent_returns_false() -> None:
    mem = WorkingMemory(capacity=10)
    assert mem.remove("ghost") is False


def test_clear_empties_memory() -> None:
    mem = WorkingMemory(capacity=10)
    for i in range(5):
        mem.add(make_entry(f"entry {i}", entry_id=f"e{i}"))
    mem.clear()
    assert mem.size() == 0


def test_search_by_tag_returns_matching() -> None:
    mem = WorkingMemory(capacity=10)
    mem.add(make_entry("python code", tags=["python", "code"], entry_id="e1"))
    mem.add(make_entry("rust code", tags=["rust", "code"], entry_id="e2"))
    mem.add(make_entry("docs", tags=["docs"], entry_id="e3"))

    results = mem.search_by_tag("code")
    ids = {e.id for e in results}
    assert "e1" in ids
    assert "e2" in ids
    assert "e3" not in ids


def test_search_by_tag_empty_when_no_match() -> None:
    mem = WorkingMemory(capacity=10)
    mem.add(make_entry("content", tags=["other"], entry_id="e1"))
    assert mem.search_by_tag("missing") == []


def test_top_k_returns_highest_score_entries() -> None:
    mem = WorkingMemory(capacity=10)
    mem.add(make_entry("low", importance=0.1, entry_id="low"))
    mem.add(make_entry("high", importance=0.9, entry_id="high"))
    mem.add(make_entry("mid", importance=0.5, entry_id="mid"))

    top = mem.top_k(1)
    assert len(top) == 1
    assert top[0].id == "high"


def test_update_importance_success() -> None:
    mem = WorkingMemory(capacity=10)
    mem.add(make_entry("data", importance=0.3, entry_id="e1"))
    result = mem.update_importance("e1", 0.9)
    assert result is True
    entry = mem.get("e1")
    assert entry is not None
    assert entry.importance == pytest.approx(0.9)


def test_update_importance_invalid_raises() -> None:
    mem = WorkingMemory(capacity=10)
    mem.add(make_entry("data", entry_id="e1"))
    with pytest.raises(ValueError):
        mem.update_importance("e1", 1.5)


def test_stats_returns_correct_keys() -> None:
    mem = WorkingMemory(capacity=100)
    mem.add(make_entry("data", entry_id="e1"))
    stats = mem.stats()
    assert "size" in stats
    assert "capacity" in stats
    assert "fill_ratio" in stats
    assert "avg_importance" in stats


def test_serialization_roundtrip() -> None:
    mem = WorkingMemory(capacity=20)
    mem.add(make_entry("entry A", importance=0.8, tags=["a"], entry_id="ea"))
    mem.add(make_entry("entry B", importance=0.4, tags=["b"], entry_id="eb"))

    data = mem.to_dict()
    restored = WorkingMemory.from_dict(data)

    assert restored.size() == mem.size()
    assert restored.get("ea") is not None
    assert restored.get("eb") is not None


def test_capacity_invalid_raises() -> None:
    with pytest.raises(ValueError):
        WorkingMemory(capacity=0)
