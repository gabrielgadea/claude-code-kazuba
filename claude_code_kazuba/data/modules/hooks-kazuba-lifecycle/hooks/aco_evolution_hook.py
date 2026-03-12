#!/usr/bin/env python3
"""ACO Evolution Hook — Stop event hook.

Event: Stop
Purpose: At session end, creates a minimal evolution package checkpoint
capturing session metadata for future ACO learning. Standalone — does not
import any project modules.

Protocol:
  1. Reads JSON from stdin (session_id, transcript_path)
  2. Optionally reads transcript if path exists
  3. Creates evolution package JSON in .claude/checkpoints/
  4. Always exits 0 (never blocks session shutdown)

Input (stdin): {"session_id": "...", "transcript_path": "..."}
Output: Checkpoint file at .claude/checkpoints/aco_evolution_{timestamp}.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Exit codes
ALLOW = 0

# Checkpoint directory — .claude/checkpoints/ (3 levels up from lifecycle/)
_CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "checkpoints"


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code Stop event."""

    session_id: str
    transcript_path: str

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON from stdin.

        Returns:
            HookInput with session metadata.
            On parse error, exits with ALLOW (never blocks).
        """
        try:
            data: dict[str, Any] = json.load(sys.stdin)
            return cls(
                session_id=data.get("session_id", ""),
                transcript_path=data.get("transcript_path", ""),
            )
        except (json.JSONDecodeError, EOFError, ValueError):
            sys.exit(ALLOW)
            return cls(  # unreachable, for type checker
                session_id="",
                transcript_path="",
            )


@dataclass
class EvolutionPackage:
    """Minimal evolution data captured at session end.

    Standalone dataclass — no external model dependencies.
    """

    session_id: str
    timestamp: str
    learned_patterns: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    system_upgrades: list[str] = field(default_factory=list)
    transcript_available: bool = False
    transcript_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output.

        Returns:
            Dictionary representation of the evolution package.
        """
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "learned_patterns": self.learned_patterns,
            "anti_patterns": self.anti_patterns,
            "system_upgrades": self.system_upgrades,
            "transcript_available": self.transcript_available,
            "transcript_lines": self.transcript_lines,
        }


def read_transcript_metadata(transcript_path: str) -> tuple[bool, int]:
    """Read basic metadata from transcript file.

    Args:
        transcript_path: Path to transcript file.

    Returns:
        Tuple of (file_exists, line_count).
    """
    if not transcript_path:
        return False, 0

    path = Path(transcript_path)
    if not path.exists() or not path.is_file():
        return False, 0

    try:
        content = path.read_text(encoding="utf-8")
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return True, line_count
    except OSError:
        return False, 0


def create_evolution_package(hook_input: HookInput) -> EvolutionPackage:
    """Create an evolution package from session data.

    Args:
        hook_input: Parsed input from Claude Code.

    Returns:
        EvolutionPackage with session metadata.
    """
    now = datetime.now(tz=UTC)
    transcript_available, transcript_lines = read_transcript_metadata(
        hook_input.transcript_path,
    )

    return EvolutionPackage(
        session_id=hook_input.session_id,
        timestamp=now.isoformat(),
        transcript_available=transcript_available,
        transcript_lines=transcript_lines,
    )


def save_checkpoint(package: EvolutionPackage) -> Path | None:
    """Save evolution package to checkpoint file.

    Args:
        package: Evolution package to save.

    Returns:
        Path to saved checkpoint, or None on failure.
    """
    try:
        _CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now(tz=UTC)
        filename = f"aco_evolution_{now.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = _CHECKPOINT_DIR / filename
        filepath.write_text(
            json.dumps(package.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return filepath
    except OSError:
        return None


def process(hook_input: HookInput) -> None:
    """Process Stop event and save evolution checkpoint.

    Args:
        hook_input: Parsed input from Claude Code.
    """
    package = create_evolution_package(hook_input)
    saved = save_checkpoint(package)
    if saved:
        print(
            f"ACO Evolution checkpoint saved: {saved.name}",
            file=sys.stderr,
        )


def main() -> None:
    """Entry point for Stop hook."""
    try:
        hook_input = HookInput.from_stdin()
        process(hook_input)
    except Exception:
        pass  # fail-open: any error -> silent allow
    sys.exit(ALLOW)


if __name__ == "__main__":
    main()
