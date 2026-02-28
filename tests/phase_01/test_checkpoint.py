"""Tests for lib.checkpoint — TOON checkpoint format."""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.checkpoint import (
    TOON_MAGIC,
    TOON_VERSION,
    create_phase_checkpoint,
    load_toon,
    save_toon,
)


class TestToonConstants:
    """TOON format constants."""

    def test_magic_bytes(self) -> None:
        assert TOON_MAGIC == b"TOON"
        assert len(TOON_MAGIC) == 4

    def test_version(self) -> None:
        assert TOON_VERSION == 1


class TestSaveLoad:
    """save_toon and load_toon roundtrip."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "test.toon"
        result = save_toon(path, {"key": "value"})
        assert result.exists()
        assert result.stat().st_size > 0

    def test_roundtrip(self, tmp_path: Path) -> None:
        data = {"phase": 1, "status": "complete", "items": [1, 2, 3]}
        path = tmp_path / "roundtrip.toon"
        save_toon(path, data)
        loaded = load_toon(path)
        assert loaded == data

    def test_load_invalid_magic_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.toon"
        path.write_bytes(b"NOPE" + b"\x01" + b"garbage")
        with pytest.raises(ValueError, match="magic"):
            load_toon(path)

    def test_load_invalid_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "badver.toon"
        path.write_bytes(b"TOON" + b"\x99" + b"garbage")
        with pytest.raises(ValueError, match="version"):
            load_toon(path)

    def test_complex_data_roundtrip(self, tmp_path: Path) -> None:
        data = {
            "nested": {"a": [1, 2, {"b": True}]},
            "text": "hello world",
            "number": 3.14,
        }
        path = tmp_path / "complex.toon"
        save_toon(path, data)
        assert load_toon(path) == data


class TestPhaseCheckpoint:
    """create_phase_checkpoint high-level API."""

    def test_creates_checkpoint_with_metadata(self, checkpoint_dir: Path) -> None:
        path = create_phase_checkpoint(
            phase_id=1,
            title="lib foundation",
            results={"tests_passed": 42, "coverage": 95.0},
            checkpoint_dir=checkpoint_dir,
        )
        assert path.exists()
        data = load_toon(path)
        assert data["phase_id"] == 1
        assert data["title"] == "lib foundation"
        assert data["results"]["tests_passed"] == 42
        assert "timestamp" in data

    def test_filename_contains_phase_id(self, checkpoint_dir: Path) -> None:
        path = create_phase_checkpoint(
            phase_id=3,
            title="test",
            results={},
            checkpoint_dir=checkpoint_dir,
        )
        assert "phase_03" in path.name
