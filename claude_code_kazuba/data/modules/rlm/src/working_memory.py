"""Configurable working memory with LRU eviction."""

from __future__ import annotations

import threading
import time
from typing import Any

from claude_code_kazuba.data.modules.rlm.src.models import MemoryEntry


class WorkingMemory:
    """Bounded working memory with LRU-based eviction.

    Stores ``MemoryEntry`` objects up to ``capacity`` entries.
    When capacity is exceeded, the entry with the lowest eviction
    score (combining recency, importance, and access count) is removed.

    Thread-safe via a reentrant lock.

    Args:
        capacity: Maximum number of entries to retain (default: 1000).
    """

    def __init__(self, capacity: int = 1000) -> None:
        if capacity < 1:
            msg = f"capacity must be >= 1, got {capacity}"
            raise ValueError(msg)
        self._capacity = capacity
        self._entries: dict[str, MemoryEntry] = {}  # id -> entry
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add(self, entry: MemoryEntry) -> str:
        """Add an entry to working memory.

        If capacity is exceeded, the entry with the lowest eviction score
        is removed before insertion.

        Args:
            entry: The ``MemoryEntry`` to store.

        Returns:
            The entry's ``id``.
        """
        with self._lock:
            # If entry already exists, replace it (touched)
            if entry.id in self._entries:
                self._entries[entry.id] = entry
                return entry.id

            # Evict if necessary
            if len(self._entries) >= self._capacity:
                self._evict_one()

            self._entries[entry.id] = entry
            return entry.id

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve an entry by ID, updating its access timestamp.

        Args:
            entry_id: The unique entry identifier.

        Returns:
            The ``MemoryEntry`` (with updated access time), or ``None``.
        """
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return None
            touched = entry.touch()
            self._entries[entry_id] = touched
            return touched

    def remove(self, entry_id: str) -> bool:
        """Remove an entry from memory.

        Args:
            entry_id: The unique entry identifier.

        Returns:
            True if the entry was found and removed, False otherwise.
        """
        with self._lock:
            if entry_id in self._entries:
                del self._entries[entry_id]
                return True
            return False

    def clear(self) -> None:
        """Remove all entries from working memory."""
        with self._lock:
            self._entries.clear()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def search_by_tag(self, tag: str) -> list[MemoryEntry]:
        """Return all entries containing the given tag.

        Updates access time for each matched entry.

        Args:
            tag: Tag string to search for.

        Returns:
            List of matching entries, ordered by eviction score descending
            (most important / recently accessed first).
        """
        with self._lock:
            matched: list[MemoryEntry] = []
            now = time.time()
            for eid, entry in list(self._entries.items()):
                if tag in entry.tags:
                    updated = entry.model_copy(
                        update={"accessed_at": now, "access_count": entry.access_count + 1}
                    )
                    self._entries[eid] = updated
                    matched.append(updated)
            return sorted(matched, key=lambda e: e.eviction_score(), reverse=True)

    def top_k(self, k: int) -> list[MemoryEntry]:
        """Return the top-k entries by eviction score (highest = most valuable).

        Args:
            k: Number of entries to return.

        Returns:
            Up to ``k`` entries sorted by eviction score descending.
        """
        with self._lock:
            all_entries = list(self._entries.values())
            all_entries.sort(key=lambda e: e.eviction_score(), reverse=True)
            return all_entries[:k]

    def all_entries(self) -> list[MemoryEntry]:
        """Return all entries as a list (no ordering guarantee)."""
        with self._lock:
            return list(self._entries.values())

    def contains(self, entry_id: str) -> bool:
        """Check if an entry ID is present."""
        with self._lock:
            return entry_id in self._entries

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def update_importance(self, entry_id: str, importance: float) -> bool:
        """Update the importance score of an existing entry.

        Args:
            entry_id: Target entry ID.
            importance: New importance value (0.0 to 1.0).

        Returns:
            True if the entry was found and updated.
        """
        if not 0.0 <= importance <= 1.0:
            msg = f"importance must be in [0, 1], got {importance}"
            raise ValueError(msg)
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return False
            self._entries[entry_id] = entry.model_copy(update={"importance": importance})
            return True

    # ------------------------------------------------------------------
    # Stats & serialization
    # ------------------------------------------------------------------

    def size(self) -> int:
        """Return the number of entries currently in memory."""
        with self._lock:
            return len(self._entries)

    @property
    def capacity(self) -> int:
        """Maximum number of entries the memory can hold."""
        return self._capacity

    def is_full(self) -> bool:
        """True if memory is at capacity."""
        with self._lock:
            return len(self._entries) >= self._capacity

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        with self._lock:
            entries = list(self._entries.values())
            avg_importance = (
                sum(e.importance for e in entries) / len(entries) if entries else 0.0
            )
            return {
                "size": len(entries),
                "capacity": self._capacity,
                "fill_ratio": len(entries) / self._capacity,
                "avg_importance": round(avg_importance, 4),
            }

    def to_dict(self) -> dict[str, Any]:
        """Serialize memory for checkpointing."""
        with self._lock:
            return {
                "capacity": self._capacity,
                "entries": [e.to_dict() for e in self._entries.values()],
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkingMemory:
        """Reconstruct from a serialized dict."""
        mem = cls(capacity=data.get("capacity", 1000))
        for entry_data in data.get("entries", []):
            entry = MemoryEntry.from_dict(entry_data)
            mem._entries[entry.id] = entry
        return mem

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_one(self) -> None:
        """Remove the entry with the lowest eviction score (LRU + importance)."""
        if not self._entries:
            return
        worst_id = min(self._entries.keys(), key=lambda eid: self._entries[eid].eviction_score())
        del self._entries[worst_id]
