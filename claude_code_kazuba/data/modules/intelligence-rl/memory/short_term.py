"""Short-Term Memory with JSON storage and retention policy.

Stores items for up to N days (configurable), then expires them.
Uses file-based JSON storage with thread-safe access.
"""

import json
import threading
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..core.config import LearningConfig, StorageConfig
from ..core.exceptions import StorageError
from ..core.models import PatternMatch


class ShortTermMemory:
    """Short-term memory with configurable retention and JSON persistence.

    Features:
    - Automatic expiration based on retention_days
    - FIFO eviction when max_items exceeded
    - Thread-safe file operations
    """

    def __init__(
        self,
        config: LearningConfig,
        storage_config: StorageConfig | None = None,
    ) -> None:
        self._config = config
        self._storage_config = storage_config or StorageConfig()
        self._lock = threading.RLock()

        self._items: list[dict[str, Any]] = []
        self._embeddings: dict[str, list[float]] = {}

        self._load()

    @property
    def size(self) -> int:
        """Current number of items."""
        with self._lock:
            return len(self._items)

    def _load(self) -> None:
        """Load items from storage."""
        path = self._storage_config.short_term_path

        if not path.exists():
            return

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._items = data.get("items", [])
                self._embeddings = data.get("embeddings", {})

            # Clean expired items on load
            self._cleanup_expired()
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in {path}: {e}") from e

    def _save(self) -> None:
        """Save items to storage."""
        path = self._storage_config.short_term_path
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "items": self._items,
            "embeddings": self._embeddings,
            "last_saved": datetime.utcnow().isoformat(),
        }

        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except OSError as e:
            raise StorageError(f"Failed to save to {path}: {e}") from e

    def _cleanup_expired(self) -> None:
        """Remove items older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self._config.short_term_retention_days)
        cutoff_str = cutoff.isoformat()

        original_count = len(self._items)

        self._items = [item for item in self._items if item.get("created_at", "") >= cutoff_str]

        # Clean up embeddings for removed items
        valid_ids = {item.get("id") for item in self._items}
        self._embeddings = {k: v for k, v in self._embeddings.items() if k in valid_ids}

        if len(self._items) < original_count:
            self._save()

    def store(
        self,
        item_id: str,
        content: dict[str, Any],
        embedding: NDArray[np.float32] | None = None,
    ) -> bool:
        """Store item in short-term memory.

        Args:
            item_id: Unique identifier
            content: Content dict
            embedding: Optional vector embedding

        Returns:
            True if stored successfully
        """
        with self._lock:
            # Check for duplicates
            existing_ids = {item.get("id") for item in self._items}
            if item_id in existing_ids:
                # Update existing
                for item in self._items:
                    if item.get("id") == item_id:
                        item.update(content)
                        item["updated_at"] = datetime.utcnow().isoformat()
                        break
            else:
                # Add new item
                item = {
                    "id": item_id,
                    **content,
                    "created_at": datetime.utcnow().isoformat(),
                }
                self._items.append(item)

                # FIFO eviction if exceeded
                while len(self._items) > self._config.short_term_max_items:
                    removed = self._items.pop(0)
                    removed_id = removed.get("id")
                    if removed_id in self._embeddings:
                        del self._embeddings[removed_id]

            # Store embedding
            if embedding is not None:
                self._embeddings[item_id] = embedding.tolist()

            self._save()
            return True

    def get(self, item_id: str) -> dict[str, Any] | None:
        """Retrieve item by ID."""
        with self._lock:
            for item in self._items:
                if item.get("id") == item_id:
                    return item
            return None

    def find_similar(
        self,
        query_embedding: NDArray[np.float32],
        top_k: int = 10,
        min_similarity: float = 0.3,
    ) -> list[PatternMatch]:
        """Find similar items by embedding similarity.

        Args:
            query_embedding: Query vector
            top_k: Maximum results
            min_similarity: Minimum threshold

        Returns:
            List of PatternMatch objects
        """
        with self._lock:
            if not self._embeddings:
                return []

            similarities: list[tuple[str, float, dict[str, Any]]] = []

            for item in self._items:
                item_id = item.get("id")
                if item_id not in self._embeddings:
                    continue

                embedding = np.array(self._embeddings[item_id], dtype=np.float32)
                similarity = self._cosine_similarity(query_embedding, embedding)

                if similarity >= min_similarity:
                    similarities.append((item_id, similarity, item))

            similarities.sort(key=lambda x: x[1], reverse=True)

            return [
                PatternMatch(
                    pattern_id=item_id,
                    similarity_score=sim,
                    source="short_term",
                    content=content,
                    created_at=datetime.fromisoformat(content.get("created_at", datetime.utcnow().isoformat())),
                    access_count=content.get("access_count", 0),
                )
                for item_id, sim, content in similarities[:top_k]
            ]

    def _cosine_similarity(
        self,
        a: NDArray[np.float32],
        b: NDArray[np.float32],
    ) -> float:
        """Calculate cosine similarity."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))

    def cleanup(self) -> int:
        """Manually trigger cleanup of expired items.

        Returns:
            Number of items removed
        """
        with self._lock:
            original_count = len(self._items)
            self._cleanup_expired()
            return original_count - len(self._items)

    def clear_expired(self) -> int:
        """Clear expired items from short-term memory.

        Alias for cleanup() for compatibility.

        Returns:
            Number of items removed
        """
        return self.cleanup()

    def stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            return {
                "size": len(self._items),
                "max_items": self._config.short_term_max_items,
                "embeddings_count": len(self._embeddings),
                "retention_days": self._config.short_term_retention_days,
            }
