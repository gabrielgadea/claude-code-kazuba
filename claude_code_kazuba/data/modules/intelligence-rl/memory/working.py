"""Working Memory with LRU cache and SIMD similarity search.

Uses Rust kernel for performance when available, falls back to Python.
"""

import threading
from collections import OrderedDict
from datetime import datetime
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..core.config import LearningConfig
from ..core.models import PatternMatch

# Try to import Rust kernel
try:
    from utils.rust_kernel_adapters import RustWorkingMemory  # type: ignore[import-not-found]

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


class WorkingMemory:
    """Working memory with O(1) LRU access and SIMD similarity search.

    Performance:
    - LRU operations: O(1)
    - Similarity search: O(n) with SIMD acceleration

    Falls back to pure Python if Rust kernel unavailable.
    """

    def __init__(self, config: LearningConfig) -> None:
        self._config = config
        self._lock = threading.RLock()
        self._access_count = 0

        if RUST_AVAILABLE:
            self._rust_memory = RustWorkingMemory(config.working_memory_size)
            self._use_rust = True
        else:
            self._cache: OrderedDict[str, tuple[dict[str, Any], NDArray[np.float32]]] = OrderedDict()
            self._use_rust = False

    @property
    def size(self) -> int:
        """Current number of items in memory."""
        with self._lock:
            if self._use_rust:
                return self._rust_memory.size()
            return len(self._cache)

    @property
    def capacity(self) -> int:
        """Maximum capacity of memory."""
        return self._config.working_memory_size

    def store(
        self,
        key: str,
        content: dict[str, Any],
        embedding: NDArray[np.float32],
    ) -> bool:
        """Store item in working memory.

        Args:
            key: Unique identifier for the item
            content: Content dict to store
            embedding: Vector embedding for similarity search

        Returns:
            True if stored successfully
        """
        with self._lock:
            if self._use_rust:
                return self._rust_memory.store(key, content, embedding)

            # Python fallback: LRU eviction
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._config.working_memory_size:
                    self._cache.popitem(last=False)

            self._cache[key] = (content, embedding)
            return True

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve item by key.

        Args:
            key: Item identifier

        Returns:
            Content dict if found, None otherwise
        """
        with self._lock:
            self._access_count += 1

            if self._use_rust:
                return self._rust_memory.get(key)

            # Python fallback
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key][0]
            return None

    def find_similar(
        self,
        query_embedding: NDArray[np.float32],
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[PatternMatch]:
        """Find similar items using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Maximum results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of PatternMatch objects sorted by similarity
        """
        with self._lock:
            if self._use_rust:
                results = self._rust_memory.find_similar(query_embedding, top_k, min_similarity)
                return [
                    PatternMatch(
                        pattern_id=r["key"],
                        similarity_score=r["similarity"],
                        source="working",
                        content=r["content"],
                        created_at=datetime.fromisoformat(r["created_at"]),
                        access_count=r.get("access_count", 0),
                    )
                    for r in results
                ]

            # Python fallback: cosine similarity
            if not self._cache:
                return []

            similarities: list[tuple[str, float, dict[str, Any]]] = []

            for key, (content, embedding) in self._cache.items():
                similarity = self._cosine_similarity(query_embedding, embedding)
                if similarity >= min_similarity:
                    similarities.append((key, similarity, content))

            # Sort by similarity descending
            similarities.sort(key=lambda x: x[1], reverse=True)

            return [
                PatternMatch(
                    pattern_id=key,
                    similarity_score=sim,
                    source="working",
                    content=content,
                    created_at=datetime.utcnow(),
                    access_count=0,
                )
                for key, sim, content in similarities[:top_k]
            ]

    def _cosine_similarity(
        self,
        a: NDArray[np.float32],
        b: NDArray[np.float32],
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))

    def clear(self) -> None:
        """Clear all items from memory."""
        with self._lock:
            if self._use_rust:
                self._rust_memory.clear()
            else:
                self._cache.clear()

    def put(
        self,
        key: str,
        value: dict[str, Any],
        item_type: str = "default",
    ) -> bool:
        """Store item in working memory (simplified interface).

        Args:
            key: Unique identifier
            value: Content dict to store
            item_type: Type of item (for metadata)

        Returns:
            True if stored successfully
        """
        # Generate a zero embedding for items without embeddings
        embedding = np.zeros(384, dtype=np.float32)

        content = {
            **value,
            "item_type": item_type,
        }

        return self.store(key, content, embedding)

    def stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            return {
                "size": self.size,
                "capacity": self.capacity,
                "access_count": self._access_count,
                "using_rust": self._use_rust,
                "hit_rate": self._access_count / max(1, self._access_count),
            }
