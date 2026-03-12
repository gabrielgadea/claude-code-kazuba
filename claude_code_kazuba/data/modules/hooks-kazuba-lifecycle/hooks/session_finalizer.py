#!/usr/bin/env python3
"""
Stop Hook: Session Finalizer.

This hook intercepts Stop events to perform cleanup operations,
export knowledge to Cipher MCP, and create final session summary.

Exit codes:
  0 - Finalization successful
  1 - Finalization failed (non-blocking)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# ============================================================================
# EXIT CODES
# ============================================================================

ALLOW = 0
BLOCK = 1

# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass(frozen=True)
class FinalizerConfig:
    """Configuration for session finalization."""

    summaries_dir: str = ".claude/session_summaries"
    export_knowledge: bool = True
    create_summary: bool = True
    max_summary_length: int = 5000


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass(frozen=True)
class SessionSummary:
    """Summary of a completed session."""

    session_id: str
    ended_at: str
    duration_seconds: int
    files_created: tuple[str, ...]
    files_modified: tuple[str, ...]
    tools_used: tuple[str, ...]
    key_accomplishments: tuple[str, ...]
    errors_encountered: int
    tests_run: int
    tests_passed: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSummary:
        """Create from dictionary."""
        return cls(
            session_id=data.get("session_id", "unknown"),
            ended_at=datetime.now().isoformat(),
            duration_seconds=data.get("duration_seconds", 0),
            files_created=tuple(data.get("files_created", [])),
            files_modified=tuple(data.get("files_modified", [])),
            tools_used=tuple(data.get("tools_used", [])),
            key_accomplishments=tuple(data.get("key_accomplishments", [])),
            errors_encountered=data.get("errors_encountered", 0),
            tests_run=data.get("tests_run", 0),
            tests_passed=data.get("tests_passed", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "files_created": list(self.files_created),
            "files_modified": list(self.files_modified),
            "tools_used": list(self.tools_used),
            "key_accomplishments": list(self.key_accomplishments),
            "errors_encountered": self.errors_encountered,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
        }


@dataclass(frozen=True)
class HookInput:
    """Parsed input from Claude Code Stop event."""

    session_id: str
    session_data: dict[str, Any]

    @classmethod
    def from_stdin(cls) -> HookInput:
        """Parse JSON input from stdin."""
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e

        return cls(
            session_id=data.get("session_id", f"unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            session_data=data,
        )


@dataclass(frozen=True)
class FinalizationResult:
    """Result of session finalization."""

    exit_code: int
    summary_path: str | None
    knowledge_exported: bool
    message: str

    def to_json(self) -> str:
        """Convert to JSON string for output."""
        return json.dumps(
            {
                "summary_path": self.summary_path,
                "knowledge_exported": self.knowledge_exported,
            }
        )

    def emit(self) -> None:
        """Emit result and exit."""
        print(self.message, file=sys.stderr)
        print(self.to_json())
        sys.exit(self.exit_code)


# ============================================================================
# FINALIZATION LOGIC
# ============================================================================


def create_summary_dir(config: FinalizerConfig) -> Path:
    """Create summaries directory if it doesn't exist."""
    summaries_dir = Path(config.summaries_dir)
    summaries_dir.mkdir(parents=True, exist_ok=True)
    return summaries_dir


def write_session_summary(
    summary: SessionSummary,
    config: FinalizerConfig,
) -> str | None:
    """Write session summary to file."""
    if not config.create_summary:
        return None

    try:
        summaries_dir = create_summary_dir(config)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = "".join(c for c in summary.session_id if c.isalnum() or c in "_-")[:20]
        filename = f"session_{safe_id}_{timestamp}.json"
        filepath = summaries_dir / filename

        with open(filepath, "w") as f:
            json.dump(summary.to_dict(), f, indent=2)

        return str(filepath)
    except OSError:
        return None


def export_to_cipher(summary: SessionSummary, config: FinalizerConfig) -> bool:
    """
    Export session knowledge to Cipher MCP.

    Note: This is a placeholder that generates the command/data
    that would be used by the actual Cipher MCP integration.
    """
    if not config.export_knowledge:
        return False

    # In production, this would call cipher_extract_and_operate_memory
    # For now, we just prepare the data
    cipher_data = {
        "interaction_type": "session_summary",
        "session_id": summary.session_id,
        "key_learnings": list(summary.key_accomplishments),
        "files_involved": list(summary.files_modified) + list(summary.files_created),
        "metadata": {
            "domain": "development",
            "projectId": "analise",
            "timestamp": summary.ended_at,
        },
    }

    # Write to local file for later processing
    try:
        cipher_queue = Path(".claude/cipher_queue")
        cipher_queue.mkdir(parents=True, exist_ok=True)
        queue_file = cipher_queue / f"session_{summary.session_id}.json"
        with open(queue_file, "w") as f:
            json.dump(cipher_data, f, indent=2)
        return True
    except OSError:
        return False


def _read_compliance_tools(project_root: Path) -> list[str]:
    """Read tools_used from compliance.jsonl (last 50 entries)."""
    compliance_path = project_root / ".claude" / "metrics" / "compliance.jsonl"
    if not compliance_path.exists():
        return []
    tools: list[str] = []
    try:
        lines = compliance_path.read_text(encoding="utf-8").splitlines()
        for line in lines[-50:]:
            entry = json.loads(line)
            tool = entry.get("tool_name") or entry.get("tool") or ""
            if tool and tool not in tools:
                tools.append(tool)
    except (OSError, json.JSONDecodeError):
        pass
    return tools


def _enrich_session_data(session_data: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Enrich session_data with real tools_used from compliance.jsonl."""
    enriched = dict(session_data)
    if not enriched.get("tools_used"):
        enriched["tools_used"] = _read_compliance_tools(project_root)
    enriched["data_integrity_verified"] = True
    return enriched


def finalize_session(hook_input: HookInput, config: FinalizerConfig) -> FinalizationResult:
    """
    Finalize a session by creating summary and exporting knowledge.

    Returns FinalizationResult with status.
    """
    # Create session summary (enriched with compliance.jsonl data)
    project_root = Path(__file__).resolve().parents[3]
    enriched_data = _enrich_session_data(hook_input.session_data, project_root)
    summary = SessionSummary.from_dict(enriched_data)

    # Write summary file
    summary_path = write_session_summary(summary, config)

    # Export to Cipher
    knowledge_exported = export_to_cipher(summary, config)

    message_parts = []
    if summary_path:
        message_parts.append(f"Summary saved: {summary_path}")
    if knowledge_exported:
        message_parts.append("Knowledge queued for Cipher export")

    return FinalizationResult(
        exit_code=ALLOW,
        summary_path=summary_path,
        knowledge_exported=knowledge_exported,
        message=" | ".join(message_parts) if message_parts else "Session finalized",
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Entry point for the Stop hook."""
    try:
        # Load configuration
        config = FinalizerConfig()

        # Parse input
        hook_input = HookInput.from_stdin()

        # Finalize session
        result = finalize_session(hook_input, config)

        # Emit result
        result.emit()

    except ValueError as e:
        # Invalid input - warn but don't block
        print(f"WARNING: Invalid input: {e}", file=sys.stderr)
        print(json.dumps({"summary_path": None, "knowledge_exported": False}))
        sys.exit(ALLOW)

    except Exception as e:
        # Unexpected error
        print(f"WARNING: Finalizer hook error: {e}", file=sys.stderr)
        print(json.dumps({"summary_path": None, "knowledge_exported": False}))
        sys.exit(ALLOW)


if __name__ == "__main__":
    main()
