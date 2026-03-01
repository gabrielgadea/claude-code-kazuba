"""RLM facade — single entry point for hook integration.

Provides a high-level API that wires together QTable, WorkingMemory,
SessionManager, and RewardCalculator. Designed to be instantiated once
per hook invocation and reused across calls within the same session.

Usage::

    from lib.rlm import RLMFacade, RLMFacadeConfig

    rlm = RLMFacade()
    rlm.start_session("sess-001")

    # Record a learning step
    rlm.record_step(state="hook_start", action="cache_hit", reward=0.8)

    # Query best action for a state
    best = rlm.best_action("hook_start")

    # Add to working memory
    rlm.remember("Prompt context was about Python code", importance=0.8, tags=["python"])

    # End session (saves checkpoint if configured)
    summary = rlm.end_session()
"""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path  # noqa: TCH003
from typing import Any

from pydantic import BaseModel, Field

from modules.rlm.src.config import RLMConfig
from modules.rlm.src.models import MemoryEntry
from modules.rlm.src.q_table import QTable
from modules.rlm.src.reward_calculator import RewardCalculator, RewardComponent
from modules.rlm.src.session_manager import SessionManager
from modules.rlm.src.working_memory import WorkingMemory

logger = logging.getLogger(__name__)


class RLMFacadeConfig(BaseModel, frozen=True):
    """Thin config wrapper accepted by RLMFacade.

    Delegates core hyperparameters to ``RLMConfig`` while exposing
    convenience fields for facade-level behaviour.
    """

    rlm: RLMConfig = Field(default_factory=RLMConfig.defaults)
    reward_components: list[dict[str, Any]] = Field(  # type: ignore[assignment]
        default_factory=list,
        description="List of RewardComponent dicts (model_dump format)",
    )
    enable_epsilon_greedy: bool = Field(
        default=True,
        description="Use epsilon-greedy action selection in best_action()",
    )
    config_yaml_path: Path | None = Field(
        default=None,
        description="Optional path to override rlm.yaml",
    )

    @classmethod
    def from_yaml(cls, path: Path) -> RLMFacadeConfig:
        """Load facade config from a YAML file via RLMConfig."""
        rlm_cfg = RLMConfig.from_yaml(path)
        return cls(rlm=rlm_cfg)


class RLMFacade:
    """Unified facade for Reinforcement Learning Memory integration.

    Wires together the four RLM subsystems:

    - ``QTable``: Persistent Q-value store with TD(λ) learning
    - ``WorkingMemory``: LRU-bounded episodic memory
    - ``SessionManager``: Session/episode lifecycle + TOON checkpoints
    - ``RewardCalculator``: Composite reward from performance metrics

    Thread-safety: the underlying subsystems use their own locks.
    The facade itself is NOT thread-safe at the session level; use
    one facade per concurrent session.

    Args:
        config: Optional ``RLMFacadeConfig``; uses defaults if omitted.
    """

    def __init__(self, config: RLMFacadeConfig | None = None) -> None:
        cfg = config or RLMFacadeConfig()
        rlm = cfg.rlm

        self._cfg = cfg
        self._rlm_cfg = rlm

        # Q-table
        self._q_table = QTable(
            learning_rate=rlm.learning_rate,
            discount_factor=rlm.discount_factor,
            lambda_trace=rlm.lambda_trace,
            max_size=rlm.max_q_table_size,
            persist_path=rlm.persist_path,
            auto_save_interval=rlm.auto_save_interval,
        )

        # Working memory
        self._memory = WorkingMemory(capacity=rlm.max_history)

        # Session manager
        self._session = SessionManager(checkpoint_dir=rlm.session_checkpoint_dir)

        # Reward calculator
        components: list[RewardComponent] = []
        for comp_data in cfg.reward_components:
            try:
                components.append(RewardComponent(**comp_data))
            except Exception:  # noqa: BLE001
                logger.warning("Invalid reward component, skipping: %s", comp_data)
        self._reward = RewardCalculator(
            components=components,
            clip_min=rlm.reward_clip_min,
            clip_max=rlm.reward_clip_max,
        )

        # Internal state
        self._current_episode_id: str | None = None
        self._rng = random.Random()  # noqa: S311  # used for epsilon-greedy, not crypto

    # ------------------------------------------------------------------
    # Session API
    # ------------------------------------------------------------------

    def start_session(self, session_id: str | None = None) -> str:
        """Start a new RLM session and open the first episode.

        Args:
            session_id: Optional explicit session ID.

        Returns:
            The session ID string.
        """
        sid = self._session.start(session_id)
        self._current_episode_id = self._session.start_episode()
        logger.debug("RLM facade session started: %s", sid)
        return sid

    def end_session(self) -> dict[str, Any]:
        """End the current session and return a summary dict.

        Closes the active episode and saves a TOON checkpoint if configured.

        Returns:
            Session statistics dictionary.
        """
        if self._current_episode_id is not None:
            try:
                self._session.end_episode(self._current_episode_id)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to close episode cleanly", exc_info=True)
            self._current_episode_id = None

        try:
            meta = self._session.end()
            return meta.to_dict()
        except RuntimeError:
            return {"error": "No active session"}

    @property
    def is_session_active(self) -> bool:
        """True if a session is currently open."""
        return self._session.is_active

    # ------------------------------------------------------------------
    # Learning API
    # ------------------------------------------------------------------

    def record_step(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str = "",
        metrics: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a (s, a, r, s') step and update Q-table.

        If ``metrics`` is provided, the reward is computed via the
        RewardCalculator instead of using the raw ``reward`` argument.

        Args:
            state: Current state identifier.
            action: Action taken.
            reward: Raw scalar reward (used if metrics is None).
            next_state: Resulting state (empty = terminal).
            metrics: Optional performance metrics dict for reward computation.
            metadata: Optional extra context.

        Returns:
            Dict with td_error, new_q_value, effective_reward.
        """
        # Compute reward from metrics if provided
        effective_reward = self._reward.compute(metrics) if metrics is not None else reward

        # Update Q-table
        update_result = self._q_table.update(
            state=state,
            action=action,
            reward=effective_reward,
            next_state=next_state,
        )

        # Record in active episode
        if self._current_episode_id is not None:
            try:
                self._session.record_step(
                    episode_id=self._current_episode_id,
                    state=state,
                    action=action,
                    reward=effective_reward,
                    next_state=next_state,
                    metadata=metadata,
                )
            except Exception:  # noqa: BLE001
                logger.debug("Session step recording failed", exc_info=True)

        return {
            "effective_reward": effective_reward,
            "td_error": update_result["td_error"],
            "new_q_value": update_result["new_q_value"],
            "states_updated": update_result["states_updated"],
        }

    def best_action(self, state: str, actions: list[str] | None = None) -> str | None:
        """Select the best action for a state (with optional epsilon-greedy).

        Args:
            state: State identifier.
            actions: Optional list of known actions; if provided, random
                     exploration will sample from this list.

        Returns:
            Best action string, or None if no Q-values for this state.
        """
        if self._cfg.enable_epsilon_greedy and self._rng.random() < self._rlm_cfg.epsilon:
            # Explore
            if actions:
                return self._rng.choice(actions)
            return None

        return self._q_table.best_action(state)

    def get_q_value(self, state: str, action: str) -> float:
        """Return Q(state, action); 0.0 if unseen."""
        return self._q_table.get(state, action)

    # ------------------------------------------------------------------
    # Working memory API
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
        entry_id: str | None = None,
    ) -> str:
        """Store a knowledge entry in working memory.

        Args:
            content: Text content to remember.
            importance: Eviction resistance score (0.0-1.0).
            tags: Optional categorical tags.
            entry_id: Optional explicit entry ID; generated if omitted.

        Returns:
            The entry ID.
        """
        entry = MemoryEntry(
            content=content,
            importance=importance,
            tags=tuple(tags or []),
            **({"id": entry_id} if entry_id else {}),  # type: ignore[arg-type]
        )
        return self._memory.add(entry)

    def recall(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID."""
        return self._memory.get(entry_id)

    def recall_by_tag(self, tag: str) -> list[MemoryEntry]:
        """Return all memory entries matching a tag."""
        return self._memory.search_by_tag(tag)

    def top_memories(self, k: int = 5) -> list[MemoryEntry]:
        """Return the top-k highest-value memory entries."""
        return self._memory.top_k(k)

    def forget(self, entry_id: str) -> bool:
        """Remove a memory entry."""
        return self._memory.remove(entry_id)

    # ------------------------------------------------------------------
    # Reward API
    # ------------------------------------------------------------------

    def compute_reward(self, metrics: dict[str, float]) -> float:
        """Compute composite reward from performance metrics.

        Args:
            metrics: Dict of metric name -> observed float value.

        Returns:
            Clipped composite reward.
        """
        return self._reward.compute(metrics)

    def compute_reward_breakdown(self, metrics: dict[str, float]) -> dict[str, Any]:
        """Compute reward with per-component breakdown."""
        return self._reward.compute_breakdown(metrics)

    def add_reward_component(
        self,
        metric_key: str,
        weight: float = 1.0,
        target: float = 1.0,
        scale: float = 1.0,
    ) -> None:
        """Add a reward component at runtime.

        Args:
            metric_key: Name of the metric.
            weight: Contribution weight.
            target: Ideal metric value.
            scale: Width of the reward curve.
        """
        self._reward.add_component(
            RewardComponent(metric_key=metric_key, weight=weight, target=target, scale=scale)
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_q_table(self, path: Path | None = None) -> Path | None:
        """Persist the Q-table to disk.

        Args:
            path: Target path; falls back to configured ``persist_path``.

        Returns:
            Path written to, or None.
        """
        return self._q_table.save(path)

    def load_q_table(self, path: Path) -> None:
        """Load Q-table from a JSON file."""
        self._q_table.load(path)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return a comprehensive stats snapshot."""
        return {
            "q_table_size": self._q_table.size(),
            "q_table_updates": self._q_table.update_count(),
            "memory_size": self._memory.size(),
            "memory_capacity": self._memory.capacity,
            "memory_stats": self._memory.stats(),
            "session_stats": self._session.stats(),
            "reward_components": len(self._reward.components),
            "epsilon": self._rlm_cfg.epsilon,
            "learning_rate": self._rlm_cfg.learning_rate,
            "discount_factor": self._rlm_cfg.discount_factor,
            "timestamp": time.time(),
        }

    def __repr__(self) -> str:
        return (
            f"RLMFacade("
            f"q_size={self._q_table.size()}, "
            f"mem_size={self._memory.size()}/{self._memory.capacity}, "
            f"session_active={self.is_session_active})"
        )
