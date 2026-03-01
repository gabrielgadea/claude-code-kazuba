"""PostToolUse hook: track tool usage for compliance and audit.

Records tool invocation statistics, monitors block/allow ratios,
and maintains an audit log for compliance review.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from claude_code_kazuba.hook_base import fail_open

# --- Configuration ---
DEFAULT_LOG_DIR: str = os.path.expanduser("~/.claude/compliance")
MAX_LOG_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB


@dataclass(frozen=True)
class ComplianceEvent:
    """A single compliance tracking event."""

    timestamp: float
    session_id: str
    tool_name: str
    hook_event: str
    decision: str  # "allow", "block", "deny", "error"
    file_path: str = ""
    details: str = ""


@dataclass
class ComplianceStats:
    """Aggregated compliance statistics."""

    total_events: int = 0
    tool_counts: dict[str, int] = field(default_factory=dict)
    block_count: int = 0
    allow_count: int = 0
    error_count: int = 0

    def record(self, event: ComplianceEvent) -> None:
        """Record an event into the statistics.

        Args:
            event: The compliance event to record.
        """
        self.total_events += 1
        tool_name = event.tool_name
        self.tool_counts[tool_name] = self.tool_counts.get(tool_name, 0) + 1

        if event.decision == "block":
            self.block_count += 1
        elif event.decision == "allow":
            self.allow_count += 1
        elif event.decision == "error":
            self.error_count += 1

    @property
    def compliance_score(self) -> float:
        """Calculate compliance score (0-1).

        Returns:
            Ratio of allowed events to total events.
        """
        if self.total_events == 0:
            return 1.0
        return self.allow_count / self.total_events


# Module-level stats (reset per process, but logs persist)
_stats = ComplianceStats()


def get_log_dir() -> Path:
    """Get the compliance log directory.

    Returns:
        Path to the compliance log directory.
    """
    log_dir = Path(os.environ.get("COMPLIANCE_LOG_DIR", DEFAULT_LOG_DIR))
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def log_event(event: ComplianceEvent) -> None:
    """Append a compliance event to the log file.

    Args:
        event: The compliance event to log.
    """
    log_dir = get_log_dir()
    log_file = log_dir / "audit.jsonl"

    # Rotate if too large
    if log_file.exists() and log_file.stat().st_size > MAX_LOG_SIZE_BYTES:
        rotated = log_dir / f"audit_{int(time.time())}.jsonl"
        log_file.rename(rotated)

    entry = asdict(event)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def create_event(data: dict[str, Any]) -> ComplianceEvent:
    """Create a ComplianceEvent from hook input data.

    Args:
        data: The hook input JSON data.

    Returns:
        A ComplianceEvent instance.
    """
    tool_input = data.get("tool_input", {})
    tool_result = data.get("tool_result", {})

    return ComplianceEvent(
        timestamp=time.time(),
        session_id=data.get("session_id", ""),
        tool_name=data.get("tool_name", ""),
        hook_event=data.get("hook_event_name", "PostToolUse"),
        decision="allow",  # PostToolUse means tool was allowed
        file_path=tool_input.get("file_path", ""),
        details=str(tool_result.get("exit_code", ""))[:100],
    )


@fail_open
def main() -> None:
    """Main hook entry point: read stdin, log compliance event."""
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    data: dict[str, Any] = json.loads(raw)

    # Create and log the compliance event
    event = create_event(data)
    _stats.record(event)
    log_event(event)

    # PostToolUse hooks should not produce output — just log and exit
    sys.exit(0)


if __name__ == "__main__":
    main()
