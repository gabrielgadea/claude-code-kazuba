"""RLM core data models."""

from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LearningRecord(BaseModel, frozen=True):
    """A single (state, action, reward, next_state) transition record.

    Immutable after creation. Use as a value object in experience replay
    or episode logging.
    """

    state: str = Field(default="", description="State identifier")
    action: str = Field(default="", description="Action taken in state")
    reward: float = Field(default=0.0, description="Observed scalar reward")
    next_state: str = Field(default="", description="State after action (empty = terminal)")
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp of this record",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional extra context (hook name, session id, etc.)",
    )

    @field_validator("reward")
    @classmethod
    def _reward_is_finite(cls, v: float) -> float:
        """Reject NaN/Inf rewards."""
        import math

        if not math.isfinite(v):
            msg = f"reward must be finite, got {v}"
            raise ValueError(msg)
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dict for serialization."""
        return {
            "state": self.state,
            "action": self.action,
            "reward": self.reward,
            "next_state": self.next_state,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearningRecord:
        """Reconstruct from a plain dict."""
        return cls(**data)


class MemoryEntry(BaseModel, frozen=True):
    """An entry stored in working memory.

    Holds content (knowledge text), importance score for LRU eviction
    weighting, and optional tags for categorical retrieval.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique entry identifier",
    )
    content: str = Field(description="Knowledge or observation text")
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score (higher = less likely to be evicted)",
    )
    tags: tuple[str, ...] = Field(
        default=(),
        description="Categorical tags for retrieval filtering",
    )
    created_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp of entry creation",
    )
    accessed_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp of last access",
    )
    access_count: int = Field(
        default=0,
        ge=0,
        description="Number of times this entry was accessed",
    )

    def touch(self) -> MemoryEntry:
        """Return a new entry with updated access time and count."""
        return self.model_copy(
            update={
                "accessed_at": time.time(),
                "access_count": self.access_count + 1,
            }
        )

    def eviction_score(self) -> float:
        """Compute eviction priority score (lower = evict first).

        Combines recency, importance, and access frequency.
        """
        recency_factor = self.accessed_at
        freq_factor = 1.0 + float(self.access_count)
        import math

        return recency_factor * self.importance * math.log1p(freq_factor)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "content": self.content,
            "importance": self.importance,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        """Reconstruct from plain dict."""
        if "tags" in data and isinstance(data["tags"], list):
            data = {**data, "tags": tuple(data["tags"])}
        return cls(**data)


class Episode(BaseModel, frozen=True):
    """A complete RL episode: sequence of transitions from start to terminal.

    An episode groups LearningRecords between session start/reset and
    a terminal state. Used for batch updates and analysis.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique episode identifier",
    )
    session_id: str = Field(
        default="",
        description="Parent session identifier",
    )
    records: tuple[LearningRecord, ...] = Field(
        default=(),
        description="Ordered sequence of (s, a, r, s') transitions",
    )
    started_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp when the episode started",
    )
    ended_at: float | None = Field(
        default=None,
        description="Unix timestamp when the episode ended (None = still running)",
    )
    total_reward: float = Field(
        default=0.0,
        description="Sum of all rewards in the episode",
    )

    @property
    def is_complete(self) -> bool:
        """True if the episode has ended."""
        return self.ended_at is not None

    @property
    def duration(self) -> float:
        """Elapsed seconds; 0.0 if still running."""
        if self.ended_at is None:
            return 0.0
        return self.ended_at - self.started_at

    @property
    def step_count(self) -> int:
        """Number of transitions in this episode."""
        return len(self.records)

    def with_record(self, record: LearningRecord) -> Episode:
        """Return new episode with the record appended."""
        return self.model_copy(
            update={
                "records": (*self.records, record),
                "total_reward": self.total_reward + record.reward,
            }
        )

    def close(self) -> Episode:
        """Return a closed copy with ended_at set to now."""
        return self.model_copy(update={"ended_at": time.time()})

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "records": [r.to_dict() for r in self.records],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_reward": self.total_reward,
        }


class SessionMeta(BaseModel, frozen=True):
    """Metadata for an RLM session.

    A session groups one or more episodes within a single Claude Code
    invocation (e.g., one hook run or user prompt cycle).
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    started_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp when the session started",
    )
    ended_at: float | None = Field(
        default=None,
        description="Unix timestamp when the session ended",
    )
    episode_count: int = Field(
        default=0,
        ge=0,
        description="Number of episodes completed in this session",
    )
    total_steps: int = Field(
        default=0,
        ge=0,
        description="Total transition steps across all episodes",
    )
    total_reward: float = Field(
        default=0.0,
        description="Cumulative reward for the session",
    )

    @property
    def duration(self) -> float:
        """Session duration in seconds; 0.0 if still running."""
        if self.ended_at is None:
            return 0.0
        return self.ended_at - self.started_at

    def close(self) -> SessionMeta:
        """Return a closed copy with ended_at set to now."""
        return self.model_copy(update={"ended_at": time.time()})

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "episode_count": self.episode_count,
            "total_steps": self.total_steps,
            "total_reward": self.total_reward,
        }
