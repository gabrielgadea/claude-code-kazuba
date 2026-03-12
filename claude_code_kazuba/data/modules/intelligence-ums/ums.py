"""Unified Memory System (UMS) — 5-layer CQRS memory cascade.

UMS is the read-side facade for the ESAA event-sourced architecture.
It provides a single API to query memory across five layers ordered
by latency, falling through from L0 (fastest) to L4 (slowest).

Layers:
    L0 — Working Memory (~0ms): in-process LRU dict.
    L1 — Short-Term (~1ms): SQLite WAL read-side (events.db).
    L2 — Long-Term (~5ms): Tantivy FTS5 unified index.
    L3 — Semantic (~10ms): FAISS GPU (optional, production only).
    L4 — External: Cipher MCP (only if similarity < 0.30).

Architecture:
    ESAA writes events to events.db (SQLite WAL, append-only).
    UMS reads from events.db via L1 and Tantivy via L2.
    No synchronization needed — single source of truth.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemoryItem:
    """A single memory retrieval result."""

    content: str
    source: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UMSConfig:
    """Configuration for the Unified Memory System."""

    data_path: Path
    enable_l3_faiss: bool = False
    enable_l4_cipher: bool = True
    l0_max_size: int = 256
    l1_max_recent: int = 100
    l2_tantivy_root: Path | None = None
    similarity_threshold: float = 0.10
    cipher_threshold: float = 0.30


class UnifiedMemorySystem:
    """5-layer CQRS memory cascade.

    Args:
        data_path: Root directory for UMS data (events.db, tantivy/, etc.).
        config: Optional UMSConfig. If None, defaults are used.
    """

    def __init__(
        self,
        data_path: Path,
        config: UMSConfig | None = None,
    ) -> None:
        self._config = config or UMSConfig(data_path=data_path)
        self._data_path = data_path
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._l0_cache: dict[str, MemoryItem] = {}
        self._l0_access_order: list[str] = []
        self._l1_db_path = self._data_path / "events.db"
        self._l1_conn: sqlite3.Connection | None = None
        self._l2_root = self._config.l2_tantivy_root or (self._data_path / "tantivy")
        self._l3_available = False
        self._l4_available = self._config.enable_l4_cipher
        logger.info("UMS initialized: data_path=%s", self._data_path)

    @property
    def data_path(self) -> Path:
        """Return the data directory path."""
        return self._data_path

    @property
    def is_initialized(self) -> bool:
        """Check if UMS has been initialized with a valid data path."""
        return self._data_path.exists()

    def recall(self, query: str, top_k: int = 5, min_score: float | None = None) -> list[MemoryItem]:
        """Query memory across all available layers, fastest first."""
        threshold = min_score if min_score is not None else self._config.similarity_threshold
        results: list[MemoryItem] = []
        t0 = time.monotonic()

        for layer_fn in [self._query_l0, self._query_l1, self._query_l2]:
            remaining = top_k - len(results)
            results.extend(layer_fn(query, remaining))
            if len(results) >= top_k:
                break

        if self._l3_available and self._config.enable_l3_faiss and len(results) < top_k:
            results.extend(self._query_l3(query, top_k - len(results)))

        best_score = max((r.score for r in results), default=0.0)
        if self._l4_available and best_score < self._config.cipher_threshold and len(results) < top_k:
            results.extend(self._query_l4(query, top_k - len(results)))

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.debug("UMS recall completed in %.1fms, %d results", elapsed_ms, len(results))
        filtered = [r for r in results if r.score >= threshold]
        return sorted(filtered, key=lambda x: x.score, reverse=True)[:top_k]

    def store(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Store an item in L0 working memory with LRU eviction."""
        item = MemoryItem(content=content, source="L0", score=1.0, metadata=metadata or {})
        self._l0_cache[key] = item
        if key in self._l0_access_order:
            self._l0_access_order.remove(key)
        self._l0_access_order.append(key)
        while len(self._l0_cache) > self._config.l0_max_size:
            evict_key = self._l0_access_order.pop(0)
            self._l0_cache.pop(evict_key, None)

    def get_stats(self) -> dict[str, Any]:
        """Return statistics about each memory layer."""
        return {
            "l0_size": len(self._l0_cache),
            "l0_max_size": self._config.l0_max_size,
            "l1_db_exists": self._l1_db_path.exists(),
            "l2_index_exists": self._l2_root.exists(),
            "l3_available": self._l3_available,
            "l4_available": self._l4_available,
            "data_path": str(self._data_path),
        }

    def _query_l0(self, query: str, top_k: int) -> list[MemoryItem]:
        """Query L0 working memory via substring matching."""
        query_lower = query.lower()
        results = [
            MemoryItem(content=item.content, source="L0", score=0.9, metadata={**item.metadata, "key": key})
            for key, item in self._l0_cache.items()
            if query_lower in item.content.lower() or query_lower in key.lower()
        ]
        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]

    def _query_l1(self, query: str, top_k: int) -> list[MemoryItem]:
        """Query L1 SQLite events database."""
        if not self._l1_db_path.exists():
            return []
        try:
            if self._l1_conn is None:
                self._l1_conn = sqlite3.connect(str(self._l1_db_path), timeout=5.0)
                self._l1_conn.row_factory = sqlite3.Row
            cursor = self._l1_conn.execute(
                "SELECT * FROM events WHERE payload LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", top_k),
            )
            return [
                MemoryItem(
                    content=str(dict(row)),
                    source="L1",
                    score=0.7,
                    metadata={"event_id": row["event_id"] if "event_id" in row.keys() else ""},
                )
                for row in cursor.fetchall()
            ]
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            logger.warning("L1 query failed: %s", e)
            return []

    def _query_l2(self, query: str, top_k: int) -> list[MemoryItem]:  # noqa: ARG002
        """Query L2 Tantivy index (placeholder — requires tantivy-py)."""
        if not self._l2_root.exists():
            return []
        logger.debug("L2 Tantivy query (not yet wired): %s", query[:50])
        return []

    def _query_l3(self, query: str, top_k: int) -> list[MemoryItem]:  # noqa: ARG002
        """Query L3 FAISS semantic index (optional, GPU-accelerated)."""
        logger.debug("L3 FAISS query (not enabled): %s", query[:50])
        return []

    def _query_l4(self, query: str, top_k: int) -> list[MemoryItem]:  # noqa: ARG002
        """Query L4 Cipher MCP (external knowledge, last resort)."""
        logger.debug("L4 Cipher query (not yet wired): %s", query[:50])
        return []

    def close(self) -> None:
        """Close all open connections."""
        if self._l1_conn is not None:
            self._l1_conn.close()
            self._l1_conn = None

    def __del__(self) -> None:
        self.close()
