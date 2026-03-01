"""Structured JSON logger for hooks.

Provides in-memory buffered logging with JSONL flush-to-disk support.
Designed for hook execution where structured output is needed for
debugging and monitoring without blocking hook execution.

Usage:
    logger = HookLogger("my-hook")
    logger.info("Hook started", phase="init")
    logger.warning("Slow operation", duration_ms=1200)
    logger.flush(Path("/tmp/hook.jsonl"))

All entries are buffered in memory and can be flushed to disk on demand.
Max entries limit prevents unbounded memory growth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class LogLevel(Enum):
    """Log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class LogEntry:
    """An immutable log entry.

    Args:
        timestamp: ISO-format timestamp string.
        level: Log severity level.
        hook_name: Name of the hook that produced this entry.
        message: Human-readable log message.
        metadata: Additional structured data.
    """

    timestamp: str
    level: LogLevel
    hook_name: str
    message: str
    metadata: dict[str, Any]


class HookLogger:
    """Structured JSON logger for hooks.

    Buffers log entries in memory with configurable max capacity.
    Provides JSONL serialization and flush-to-disk functionality.

    Args:
        hook_name: Name of the hook using this logger.
        log_dir: Optional directory for log files (informational only).
        max_entries: Maximum number of entries to buffer. When exceeded,
            oldest entries are dropped (FIFO).
    """

    def __init__(
        self,
        hook_name: str,
        log_dir: Path | None = None,
        max_entries: int = 1000,
    ) -> None:
        self._hook_name = hook_name
        self._log_dir = log_dir
        self._max_entries = max_entries
        self._entries: list[LogEntry] = []

    @property
    def hook_name(self) -> str:
        """Return the hook name."""
        return self._hook_name

    @property
    def entries(self) -> list[LogEntry]:
        """Return the current list of log entries."""
        return list(self._entries)

    def _add_entry(self, level: LogLevel, message: str, metadata: dict[str, Any]) -> None:
        """Create and buffer a log entry.

        If max_entries is exceeded, the oldest entry is dropped.

        Args:
            level: Log severity.
            message: Log message.
            metadata: Additional structured data.
        """
        entry = LogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            level=level,
            hook_name=self._hook_name,
            message=message,
            metadata=metadata,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

    def debug(self, message: str, **metadata: Any) -> None:
        """Log a debug-level message.

        Args:
            message: Log message.
            **metadata: Additional key-value data.
        """
        self._add_entry(LogLevel.DEBUG, message, metadata)

    def info(self, message: str, **metadata: Any) -> None:
        """Log an info-level message.

        Args:
            message: Log message.
            **metadata: Additional key-value data.
        """
        self._add_entry(LogLevel.INFO, message, metadata)

    def warning(self, message: str, **metadata: Any) -> None:
        """Log a warning-level message.

        Args:
            message: Log message.
            **metadata: Additional key-value data.
        """
        self._add_entry(LogLevel.WARNING, message, metadata)

    def error(self, message: str, **metadata: Any) -> None:
        """Log an error-level message.

        Args:
            message: Log message.
            **metadata: Additional key-value data.
        """
        self._add_entry(LogLevel.ERROR, message, metadata)

    def _entry_to_dict(self, entry: LogEntry) -> dict[str, Any]:
        """Convert a LogEntry to a serializable dict."""
        result: dict[str, Any] = {
            "timestamp": entry.timestamp,
            "level": entry.level.value,
            "hook_name": entry.hook_name,
            "message": entry.message,
        }
        if entry.metadata:
            result["metadata"] = entry.metadata
        return result

    def to_jsonl(self) -> str:
        """Serialize all entries as JSON Lines (one JSON object per line).

        Returns:
            String with one JSON object per line.
        """
        lines = [json.dumps(self._entry_to_dict(e)) for e in self._entries]
        return "\n".join(lines)

    def flush(self, path: Path) -> None:
        """Write all buffered entries to a JSONL file.

        Args:
            path: File path to write to. Parent directories must exist.
        """
        path.write_text(self.to_jsonl(), encoding="utf-8")

    def clear(self) -> None:
        """Remove all buffered entries."""
        self._entries.clear()
