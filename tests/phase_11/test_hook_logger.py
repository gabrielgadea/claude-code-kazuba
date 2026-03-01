"""Tests for lib.hook_logger — Phase 11 shared infrastructure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.hook_logger import HookLogger, LogEntry, LogLevel


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_levels_exist(self) -> None:
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_entry_is_frozen(self) -> None:
        entry = LogEntry(
            timestamp="2026-01-01T00:00:00",
            level=LogLevel.INFO,
            hook_name="test",
            message="hello",
            metadata={},
        )
        with pytest.raises(AttributeError):
            entry.message = "other"  # type: ignore[misc]


class TestHookLogger:
    """Tests for HookLogger class."""

    def test_create_logger(self) -> None:
        logger = HookLogger("test-hook")
        assert logger.hook_name == "test-hook"

    def test_log_info(self) -> None:
        logger = HookLogger("test")
        logger.info("test message")
        assert len(logger.entries) == 1
        assert logger.entries[0].level == LogLevel.INFO
        assert logger.entries[0].message == "test message"

    def test_log_warning(self) -> None:
        logger = HookLogger("test")
        logger.warning("warn msg")
        assert logger.entries[0].level == LogLevel.WARNING

    def test_log_error(self) -> None:
        logger = HookLogger("test")
        logger.error("err msg")
        assert logger.entries[0].level == LogLevel.ERROR

    def test_log_debug(self) -> None:
        logger = HookLogger("test")
        logger.debug("debug msg")
        assert logger.entries[0].level == LogLevel.DEBUG

    def test_entries_list(self) -> None:
        logger = HookLogger("test")
        logger.info("a")
        logger.info("b")
        logger.info("c")
        assert len(logger.entries) == 3

    def test_to_jsonl_format(self) -> None:
        logger = HookLogger("test")
        logger.info("msg1")
        logger.warning("msg2")
        jsonl = logger.to_jsonl()
        lines = jsonl.strip().split("\n")
        assert len(lines) == 2
        parsed1 = json.loads(lines[0])
        assert parsed1["message"] == "msg1"
        assert parsed1["level"] == "INFO"
        parsed2 = json.loads(lines[1])
        assert parsed2["message"] == "msg2"
        assert parsed2["level"] == "WARNING"

    def test_flush_to_file(self, tmp_path: Path) -> None:
        logger = HookLogger("test")
        logger.info("flush test")
        out = tmp_path / "test.jsonl"
        logger.flush(out)
        assert out.exists()
        content = out.read_text()
        parsed = json.loads(content.strip())
        assert parsed["message"] == "flush test"

    def test_clear_entries(self) -> None:
        logger = HookLogger("test")
        logger.info("a")
        logger.info("b")
        assert len(logger.entries) == 2
        logger.clear()
        assert len(logger.entries) == 0

    def test_max_entries_limit(self) -> None:
        logger = HookLogger("test", max_entries=5)
        for i in range(10):
            logger.info(f"msg {i}")
        assert len(logger.entries) == 5

    def test_metadata_in_entry(self) -> None:
        logger = HookLogger("test")
        logger.info("with meta", key="value", count=42)
        entry = logger.entries[0]
        assert entry.metadata["key"] == "value"
        assert entry.metadata["count"] == 42

    def test_timestamp_present(self) -> None:
        logger = HookLogger("test")
        logger.info("ts test")
        entry = logger.entries[0]
        assert entry.timestamp != ""
        assert "T" in entry.timestamp  # ISO format

    def test_hook_name_in_entry(self) -> None:
        logger = HookLogger("my-hook")
        logger.info("test")
        assert logger.entries[0].hook_name == "my-hook"

    def test_log_dir_parameter(self, tmp_path: Path) -> None:
        logger = HookLogger("test", log_dir=tmp_path)
        logger.info("dir test")
        logger.flush(tmp_path / "out.jsonl")
        assert (tmp_path / "out.jsonl").exists()
