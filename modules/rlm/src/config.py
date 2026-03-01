"""RLM configuration models using Pydantic v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class RLMConfig(BaseModel, frozen=True):
    """Core RLM hyperparameters and operational settings.

    All fields are immutable after construction (frozen=True).
    Use `model_copy(update={...})` to derive variants.
    """

    # Q-learning hyperparameters
    learning_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Learning rate alpha for Q-value updates",
    )
    discount_factor: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Discount factor gamma for future rewards",
    )
    epsilon: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Epsilon for epsilon-greedy exploration",
    )
    lambda_trace: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Eligibility trace decay lambda",
    )

    # Memory settings
    max_history: int = Field(
        default=1000,
        ge=1,
        description="Maximum entries in working memory",
    )
    max_q_table_size: int = Field(
        default=10_000,
        ge=1,
        description="Maximum (state, action) pairs in Q-table",
    )

    # Persistence
    persist_path: Path | None = Field(
        default=None,
        description="Path to persist Q-table as JSON; None = in-memory only",
    )
    auto_save_interval: int = Field(
        default=100,
        ge=1,
        description="Auto-save Q-table every N updates",
    )

    # Reward settings
    reward_clip_min: float = Field(
        default=-1.0,
        description="Minimum reward value (clipping)",
    )
    reward_clip_max: float = Field(
        default=1.0,
        description="Maximum reward value (clipping)",
    )

    # Session settings
    session_checkpoint_dir: Path | None = Field(
        default=None,
        description="Directory for session TOON checkpoints; None = skip",
    )

    @field_validator("persist_path", "session_checkpoint_dir", mode="before")
    @classmethod
    def _coerce_path(cls, v: Any) -> Path | None:
        """Allow string paths to be converted to Path objects."""
        if v is None:
            return None
        return Path(v)

    @model_validator(mode="after")
    def _validate_reward_clip(self) -> RLMConfig:
        """Ensure clip_min < clip_max."""
        if self.reward_clip_min >= self.reward_clip_max:
            msg = (
                f"reward_clip_min ({self.reward_clip_min}) must be "
                f"< reward_clip_max ({self.reward_clip_max})"
            )
            raise ValueError(msg)
        return self

    @classmethod
    def from_yaml(cls, path: Path) -> RLMConfig:
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Validated RLMConfig instance.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If YAML content fails validation.
        """
        with path.open() as fh:
            data: dict[str, Any] = yaml.safe_load(fh) or {}
        return cls(**data)

    @classmethod
    def defaults(cls) -> RLMConfig:
        """Return configuration with all default values."""
        return cls()

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a plain dictionary (JSON-serializable)."""
        data: dict[str, Any] = self.model_dump()
        # Convert Path objects to strings for serialization
        if data.get("persist_path"):
            data["persist_path"] = str(data["persist_path"])
        if data.get("session_checkpoint_dir"):
            data["session_checkpoint_dir"] = str(data["session_checkpoint_dir"])
        return data
