#!/usr/bin/env python3
"""Session State Manager - Checkpoint-based session continuity.

Event: PreCompact
Purpose: Capture session state before context compaction so it can be
         restored in the next session.

Exit codes:
  0 - Allow (always — hooks must be fail-open)

Protocol: stdin JSON -> capture state -> stdout (empty) -> exit 0
"""
from __future__ import annotations

import contextlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure lib is importable from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Attempt to import lib utilities (fail-open if not available)
# ---------------------------------------------------------------------------
try:
    from claude_code_kazuba.checkpoint import save_toon  # type: ignore[import]

    _TOON_AVAILABLE = True
except ImportError:
    _TOON_AVAILABLE = False

try:
    from claude_code_kazuba.circuit_breaker import CircuitBreaker  # type: ignore[import]

    _CB_AVAILABLE = True
except ImportError:
    _CB_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_CHECKPOINT_DIR = Path.cwd() / ".claude" / "checkpoints"
_DEFAULT_MAX_CHECKPOINTS = 10
_DEFAULT_ENV_KEYS: list[str] = [
    "CLAUDE_PROJECT_DIR",
    "VIRTUAL_ENV",
    "PYTHONPATH",
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SessionStateConfig(BaseModel, frozen=True):
    """Immutable configuration for SessionStateManager.

    Args:
        checkpoint_dir: Directory where checkpoints are stored.
        max_checkpoints: Maximum number of checkpoint files to keep.
        include_env_keys: Environment variable keys to capture.
        format: Output format — 'toon' (msgpack) or 'json'.
    """

    checkpoint_dir: Path = Field(default=_DEFAULT_CHECKPOINT_DIR)
    max_checkpoints: int = Field(default=_DEFAULT_MAX_CHECKPOINTS, ge=1)
    include_env_keys: list[str] = Field(default_factory=lambda: list(_DEFAULT_ENV_KEYS))
    format: str = Field(default="toon")


class CaptureResult(BaseModel, frozen=True):
    """Result of a session state capture operation.

    Args:
        success: Whether the capture succeeded.
        checkpoint_path: Path to the checkpoint file (None on failure).
        size_bytes: Size of the checkpoint file in bytes.
        duration_ms: Duration of the capture operation in milliseconds.
        error: Error message if capture failed.
    """

    success: bool
    checkpoint_path: Path | None = None
    size_bytes: int = 0
    duration_ms: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# SessionStateManager
# ---------------------------------------------------------------------------


class SessionStateManager:
    """Captures session state into a checkpoint before compaction.

    Uses lib.checkpoint for TOON format when available, falls back to JSON.
    Uses lib.circuit_breaker to protect the capture operation when available.
    """

    def __init__(self, config: SessionStateConfig) -> None:
        self.config = config
        self._circuit_breaker = (
            CircuitBreaker("session_state_manager") if _CB_AVAILABLE else None
        )

    def capture(self, session_data: dict[str, Any]) -> CaptureResult:
        """Capture session data to a checkpoint file.

        Args:
            session_data: Arbitrary session data to persist.

        Returns:
            CaptureResult indicating success or failure.
        """
        start = time.monotonic()

        def _do_capture() -> CaptureResult:
            return self._do_capture_internal(session_data, start)

        try:
            if self._circuit_breaker is not None:
                return self._circuit_breaker.call(_do_capture)
            return _do_capture()
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return CaptureResult(
                success=False,
                duration_ms=duration_ms,
                error=str(exc),
            )

    def _do_capture_internal(
        self, session_data: dict[str, Any], start: float
    ) -> CaptureResult:
        """Internal capture logic (may raise)."""
        self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(tz=UTC).isoformat()
        data: dict[str, Any] = {
            "captured_at": timestamp,
            "session_data": session_data,
        }

        ts_slug = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        fmt = self.config.format.lower()

        if fmt == "toon" and _TOON_AVAILABLE:
            path = self.config.checkpoint_dir / f"session_state_{ts_slug}.toon"
            self._write_toon(data, path)
        else:
            path = self.config.checkpoint_dir / f"session_state_{ts_slug}.json"
            self._write_json(data, path)

        size_bytes = path.stat().st_size
        duration_ms = int((time.monotonic() - start) * 1000)

        # Prune old checkpoints if necessary
        pruned = self.prune_old(self.config.max_checkpoints)
        _ = pruned  # informational only

        return CaptureResult(
            success=True,
            checkpoint_path=path,
            size_bytes=size_bytes,
            duration_ms=duration_ms,
        )

    def _write_toon(self, data: dict[str, Any], path: Path) -> None:
        """Write data in TOON format using lib.checkpoint.save_toon.

        Falls back to JSON if save_toon raises.

        Args:
            data: Data to write.
            path: Destination path.
        """
        try:
            save_toon(path, data)
        except Exception:
            # Fallback to JSON
            json_path = path.with_suffix(".json")
            self._write_json(data, json_path)
            # Rename so the original path points to something
            json_path.rename(path.with_suffix(".json"))

    def _write_json(self, data: dict[str, Any], path: Path) -> None:
        """Write data as formatted JSON.

        Args:
            data: Data to write.
            path: Destination path.
        """
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def list_checkpoints(self) -> list[Path]:
        """Return all checkpoint files sorted by modification time (newest first).

        Returns:
            List of checkpoint paths.
        """
        if not self.config.checkpoint_dir.exists():
            return []

        patterns = ["session_state_*.toon", "session_state_*.json"]
        files: list[Path] = []
        for pattern in patterns:
            files.extend(self.config.checkpoint_dir.glob(pattern))

        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def prune_old(self, max_keep: int) -> int:
        """Remove old checkpoint files, keeping the most recent ones.

        Args:
            max_keep: Number of checkpoints to keep.

        Returns:
            Number of files removed.
        """
        checkpoints = self.list_checkpoints()
        to_remove = checkpoints[max_keep:]
        removed = 0
        for path in to_remove:
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
        return removed


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """PreCompact hook entry point.

    Reads stdin JSON (hook event data), captures session state,
    always exits 0 (never blocks compaction).
    """
    try:
        raw = sys.stdin.read().strip()
        hook_data: dict[str, Any] = {}
        if raw:
            with contextlib.suppress(json.JSONDecodeError):
                hook_data = json.loads(raw)

        config = SessionStateConfig()
        manager = SessionStateManager(config)

        session_data: dict[str, Any] = {
            "hook_event": hook_data.get("hook_event_name", "PreCompact"),
            "session_id": hook_data.get("session_id", ""),
            "captured_at": time.time(),
        }

        result = manager.capture(session_data)

        if result.success:
            print(
                f"Session state captured: {result.checkpoint_path} "
                f"({result.size_bytes} bytes, {result.duration_ms}ms)",
                file=sys.stderr,
            )
        else:
            print(
                f"Session state capture failed (non-blocking): {result.error}",
                file=sys.stderr,
            )

    except Exception as exc:
        # Fail-open: never block compaction
        print(f"session_state_manager hook error (non-blocking): {exc}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
