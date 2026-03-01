"""Session lifecycle management with TOON-format checkpointing."""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from modules.rlm.src.models import Episode, LearningRecord, SessionMeta

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages RLM session lifecycle and TOON checkpoints.

    A session represents one invocation context (e.g., a single Claude Code
    hook run). Within a session, one or more episodes are tracked.

    Usage::

        manager = SessionManager(checkpoint_dir=Path("checkpoints/rlm"))
        manager.start("sess-001")

        ep_id = manager.start_episode()
        manager.record_step(ep_id, state="s1", action="a1", reward=0.5)
        manager.end_episode(ep_id)

        manager.end()  # saves checkpoint

    Args:
        checkpoint_dir: Directory for TOON checkpoints. None = no persistence.
    """

    def __init__(self, checkpoint_dir: Path | None = None) -> None:
        self._checkpoint_dir = checkpoint_dir
        self._session: SessionMeta | None = None
        self._episodes: dict[str, Episode] = {}
        self._active_episode: str | None = None

        if checkpoint_dir is not None:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start(self, session_id: str | None = None) -> str:
        """Start a new session.

        Args:
            session_id: Optional explicit ID; generated if omitted.

        Returns:
            The session ID.

        Raises:
            RuntimeError: If a session is already active.
        """
        if self._session is not None:
            msg = f"Session '{self._session.id}' is already active; call end() first"
            raise RuntimeError(msg)

        sid = session_id or str(uuid.uuid4())
        self._session = SessionMeta(id=sid)
        self._episodes.clear()
        self._active_episode = None
        logger.info("RLM session started: %s", sid)
        return sid

    def end(self) -> SessionMeta:
        """End the current session and save a checkpoint.

        Returns:
            The completed ``SessionMeta``.

        Raises:
            RuntimeError: If no session is active.
        """
        if self._session is None:
            msg = "No active session to end"
            raise RuntimeError(msg)

        # Auto-close any open episode
        if self._active_episode is not None:
            try:
                self.end_episode(self._active_episode)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to auto-close active episode", exc_info=True)

        closed = self._session.close()
        self._session = closed

        # Save checkpoint
        if self._checkpoint_dir is not None:
            self._save_checkpoint()

        logger.info(
            "RLM session ended: %s (episodes=%d, steps=%d, reward=%.3f)",
            closed.id,
            closed.episode_count,
            closed.total_steps,
            closed.total_reward,
        )
        return closed

    @property
    def is_active(self) -> bool:
        """True if a session is currently open."""
        return self._session is not None and self._session.ended_at is None

    @property
    def session_id(self) -> str | None:
        """Current session ID, or None if no session is active."""
        return self._session.id if self._session is not None else None

    def current_session(self) -> SessionMeta | None:
        """Return the current session metadata snapshot."""
        return self._session

    # ------------------------------------------------------------------
    # Episode lifecycle
    # ------------------------------------------------------------------

    def start_episode(self, episode_id: str | None = None) -> str:
        """Start a new episode within the current session.

        Args:
            episode_id: Optional explicit ID; generated if omitted.

        Returns:
            The episode ID.

        Raises:
            RuntimeError: If no session is active.
        """
        if self._session is None:
            msg = "Cannot start episode: no active session"
            raise RuntimeError(msg)

        eid = episode_id or str(uuid.uuid4())
        session_id = self._session.id
        episode = Episode(id=eid, session_id=session_id)
        self._episodes[eid] = episode
        self._active_episode = eid
        logger.debug("Episode started: %s (session=%s)", eid, session_id)
        return eid

    def end_episode(self, episode_id: str) -> Episode:
        """End an episode and update session metadata.

        Args:
            episode_id: The episode to close.

        Returns:
            The completed ``Episode``.

        Raises:
            KeyError: If the episode ID is not found.
            RuntimeError: If no session is active.
        """
        if self._session is None:
            msg = "Cannot end episode: no active session"
            raise RuntimeError(msg)

        episode = self._episodes.get(episode_id)
        if episode is None:
            msg = f"Episode '{episode_id}' not found"
            raise KeyError(msg)

        closed_ep = episode.close()
        self._episodes[episode_id] = closed_ep

        # Update session stats
        self._session = self._session.model_copy(
            update={
                "episode_count": self._session.episode_count + 1,
                "total_steps": self._session.total_steps + closed_ep.step_count,
                "total_reward": self._session.total_reward + closed_ep.total_reward,
            }
        )

        if self._active_episode == episode_id:
            self._active_episode = None

        logger.debug(
            "Episode ended: %s (steps=%d, reward=%.3f)",
            episode_id,
            closed_ep.step_count,
            closed_ep.total_reward,
        )
        return closed_ep

    def get_episode(self, episode_id: str) -> Episode | None:
        """Return episode by ID, or None if not found."""
        return self._episodes.get(episode_id)

    def all_episodes(self) -> list[Episode]:
        """Return all episodes in the current session."""
        return list(self._episodes.values())

    @property
    def active_episode_id(self) -> str | None:
        """ID of the currently open episode, or None."""
        return self._active_episode

    # ------------------------------------------------------------------
    # Step recording
    # ------------------------------------------------------------------

    def record_step(
        self,
        episode_id: str,
        state: str,
        action: str,
        reward: float,
        next_state: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> LearningRecord:
        """Record a (s, a, r, s') transition in an episode.

        Args:
            episode_id: Target episode.
            state: Current state identifier.
            action: Action taken.
            reward: Observed reward.
            next_state: Resulting state (empty string = terminal).
            metadata: Optional extra context dict.

        Returns:
            The created ``LearningRecord``.

        Raises:
            KeyError: If the episode is not found.
            RuntimeError: If the episode is already closed.
        """
        episode = self._episodes.get(episode_id)
        if episode is None:
            msg = f"Episode '{episode_id}' not found"
            raise KeyError(msg)

        if episode.is_complete:
            msg = f"Episode '{episode_id}' is already closed"
            raise RuntimeError(msg)

        record = LearningRecord(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            metadata=metadata or {},
        )
        updated_ep = episode.with_record(record)
        self._episodes[episode_id] = updated_ep
        return record

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_checkpoint(self) -> Path | None:
        """Save session to TOON checkpoint via lib/checkpoint.py."""
        if self._checkpoint_dir is None or self._session is None:
            return None

        try:
            from claude_code_kazuba.checkpoint import save_toon

            session_data = self._session.to_dict()
            episodes_data = [ep.to_dict() for ep in self._episodes.values()]

            payload: dict[str, Any] = {
                "schema_version": "1.0",
                "saved_at": time.time(),
                "session": session_data,
                "episodes": episodes_data,
            }

            filename = f"rlm_session_{self._session.id}.toon"
            path = self._checkpoint_dir / filename
            save_toon(path, payload)
            logger.info("Session checkpoint saved: %s", path)
            return path
        except Exception:  # noqa: BLE001
            logger.warning("Failed to save checkpoint", exc_info=True)
            return None

    def load_checkpoint(self, path: Path) -> dict[str, Any]:
        """Load a session checkpoint from a TOON file.

        Args:
            path: Path to the TOON file.

        Returns:
            The raw checkpoint payload dictionary.
        """
        from claude_code_kazuba.checkpoint import load_toon

        return load_toon(path)

    def stats(self) -> dict[str, Any]:
        """Return current session statistics."""
        if self._session is None:
            return {"active": False}

        return {
            "active": self.is_active,
            "session_id": self._session.id,
            "episode_count": self._session.episode_count,
            "total_steps": self._session.total_steps,
            "total_reward": self._session.total_reward,
            "duration": self._session.duration,
            "open_episode": self._active_episode,
        }
