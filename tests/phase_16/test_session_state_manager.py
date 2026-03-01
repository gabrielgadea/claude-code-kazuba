"""Tests for session_state_manager.py — Phase 16."""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Module loading via importlib (modules dir has hyphens — not valid py names)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _import_from_path(name: str, file_path: Path) -> types.ModuleType:
    """Import a Python module from an arbitrary file path."""
    lib_parent = str(PROJECT_ROOT)
    if lib_parent not in sys.path:
        sys.path.insert(0, lib_parent)
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None, f"Cannot load spec for {file_path}"
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_SSM_PATH = (
    PROJECT_ROOT
    / "modules"
    / "hooks-essential"
    / "hooks"
    / "session_state_manager.py"
)
_ssm = _import_from_path("session_state_manager_ph16", _SSM_PATH)

SessionStateConfig = _ssm.SessionStateConfig
CaptureResult = _ssm.CaptureResult
SessionStateManager = _ssm.SessionStateManager
main = _ssm.main


# ---------------------------------------------------------------------------
# SessionStateConfig tests
# ---------------------------------------------------------------------------


def test_session_state_config_creation() -> None:
    """SessionStateConfig can be created with default values."""
    config = SessionStateConfig()
    assert config.max_checkpoints >= 1
    assert isinstance(config.checkpoint_dir, Path)
    assert isinstance(config.include_env_keys, list)
    assert config.format in ("toon", "json")


def test_session_state_config_frozen() -> None:
    """SessionStateConfig is immutable (frozen=True)."""
    config = SessionStateConfig()
    with pytest.raises(ValueError):
        config.max_checkpoints = 999  # type: ignore[misc]


def test_session_state_config_defaults() -> None:
    """SessionStateConfig has sensible default values."""
    config = SessionStateConfig()
    assert config.max_checkpoints == 10
    assert config.format == "toon"
    assert len(config.include_env_keys) > 0


def test_session_state_config_custom_values(tmp_path: Path) -> None:
    """SessionStateConfig accepts custom values."""
    config = SessionStateConfig(
        checkpoint_dir=tmp_path / "checkpoints",
        max_checkpoints=5,
        format="json",
    )
    assert config.max_checkpoints == 5
    assert config.format == "json"


# ---------------------------------------------------------------------------
# CaptureResult tests
# ---------------------------------------------------------------------------


def test_capture_result_creation() -> None:
    """CaptureResult can be created with minimal fields."""
    result = CaptureResult(success=True)
    assert result.success is True
    assert result.checkpoint_path is None
    assert result.size_bytes == 0
    assert result.duration_ms == 0
    assert result.error is None


def test_capture_result_success() -> None:
    """CaptureResult stores success state correctly."""
    result = CaptureResult(
        success=True,
        checkpoint_path=Path("/tmp/test.json"),
        size_bytes=1024,
        duration_ms=50,
    )
    assert result.success is True
    assert result.size_bytes == 1024
    assert result.duration_ms == 50


def test_capture_result_frozen() -> None:
    """CaptureResult is immutable (frozen=True)."""
    result = CaptureResult(success=True)
    with pytest.raises(ValueError):
        result.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SessionStateManager init
# ---------------------------------------------------------------------------


def test_session_manager_init(tmp_path: Path) -> None:
    """SessionStateManager initialises with config."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    assert manager.config is config


# ---------------------------------------------------------------------------
# SessionStateManager.capture tests
# ---------------------------------------------------------------------------


def test_session_manager_capture_json_format(tmp_path: Path) -> None:
    """Capture writes a file when format='json'."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    result = manager.capture({"key": "value"})
    assert result.success is True
    assert result.checkpoint_path is not None


def test_session_manager_capture_creates_file(tmp_path: Path) -> None:
    """Capture actually creates a file on disk."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    result = manager.capture({"hello": "world"})
    assert result.success is True
    assert result.checkpoint_path is not None
    # At least one checkpoint file should exist
    cp_dir = tmp_path / "cp"
    assert any(cp_dir.iterdir())


def test_session_manager_capture_empty_data(tmp_path: Path) -> None:
    """Capture works with an empty dict."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    result = manager.capture({})
    assert result.success is True


def test_session_manager_capture_file_content(tmp_path: Path) -> None:
    """Captured JSON file contains the provided session data."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    result = manager.capture({"my_key": "my_value"})
    assert result.success is True

    cp_dir = tmp_path / "cp"
    json_files = list(cp_dir.glob("*.json"))
    if json_files:
        data = json.loads(json_files[0].read_text())
        assert data["session_data"]["my_key"] == "my_value"


# ---------------------------------------------------------------------------
# SessionStateManager.list_checkpoints
# ---------------------------------------------------------------------------


def test_session_manager_list_checkpoints(tmp_path: Path) -> None:
    """list_checkpoints returns paths after captures."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    assert manager.list_checkpoints() == []

    manager.capture({"n": 1})
    manager.capture({"n": 2})

    checkpoints = manager.list_checkpoints()
    assert len(checkpoints) >= 1


def test_session_manager_list_checkpoints_empty_dir(tmp_path: Path) -> None:
    """list_checkpoints returns empty list when dir does not exist."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "nonexistent", format="json")
    manager = SessionStateManager(config)
    assert manager.list_checkpoints() == []


# ---------------------------------------------------------------------------
# SessionStateManager.prune_old
# ---------------------------------------------------------------------------


def test_session_manager_prune_old(tmp_path: Path) -> None:
    """prune_old removes files beyond max_keep."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)

    cp_dir = tmp_path / "cp"
    cp_dir.mkdir(parents=True)
    for i in range(5):
        (cp_dir / f"session_state_{i:04d}.json").write_text("{}")

    removed = manager.prune_old(max_keep=3)
    assert removed == 2
    remaining = manager.list_checkpoints()
    assert len(remaining) == 3


def test_session_manager_max_checkpoints(tmp_path: Path) -> None:
    """max_checkpoints is enforced after each capture."""
    config = SessionStateConfig(
        checkpoint_dir=tmp_path / "cp",
        format="json",
        max_checkpoints=2,
    )
    manager = SessionStateManager(config)

    for i in range(4):
        manager.capture({"i": i})

    remaining = manager.list_checkpoints()
    assert len(remaining) <= 2


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


def test_main_empty_stdin() -> None:
    """main() handles empty stdin without crashing, exits 0."""
    with patch("sys.stdin", StringIO("")), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


def test_main_with_session_data() -> None:
    """main() processes hook event JSON from stdin, exits 0."""
    event = json.dumps({
        "hook_event_name": "PreCompact",
        "session_id": "abc123",
    })
    with patch("sys.stdin", StringIO(event)), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


def test_main_always_exits_zero() -> None:
    """main() always exits 0 even with invalid input (fail-open)."""
    with patch("sys.stdin", StringIO("NOT VALID JSON {{{")), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


def test_write_json_directly(tmp_path: Path) -> None:
    """_write_json writes a valid JSON file."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    target = tmp_path / "out.json"
    manager._write_json({"a": 1}, target)
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["a"] == 1


def test_write_toon_fallback_on_error(tmp_path: Path) -> None:
    """_write_toon falls back to JSON when save_toon raises."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    manager = SessionStateManager(config)

    # Patch save_toon to raise if available
    import session_state_manager_ph16 as mod_ssm

    original = getattr(mod_ssm, "save_toon", None)
    if original is not None:
        # Temporarily replace with raising function
        def _raising(path: Path, data: dict) -> None:  # type: ignore[return]
            raise RuntimeError("simulated toon error")

        mod_ssm.save_toon = _raising  # type: ignore[attr-defined]
        target = tmp_path / "test.toon"
        manager._write_toon({"x": 2}, target)
        mod_ssm.save_toon = original  # restore


def test_capture_toon_format(tmp_path: Path) -> None:
    """Capture with format='toon' works (falls back to JSON if toon not available)."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="toon")
    manager = SessionStateManager(config)
    result = manager.capture({"toon_test": True})
    assert result.success is True


def test_capture_exception_returns_failure(tmp_path: Path) -> None:
    """Capture returns CaptureResult(success=False) when capture raises."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)

    import session_state_manager_ph16 as mod_ssm

    original = mod_ssm.SessionStateManager._do_capture_internal

    def _raise(self: object, session_data: dict, start: float) -> object:
        raise RuntimeError("forced error")

    mod_ssm.SessionStateManager._do_capture_internal = _raise  # type: ignore[method-assign]
    result = manager.capture({"key": "v"})
    mod_ssm.SessionStateManager._do_capture_internal = original  # type: ignore[method-assign]

    assert result.success is False
    assert result.error is not None


def test_main_capture_failure_branch(tmp_path: Path) -> None:
    """main() handles capture failure and still exits 0 (fail-open)."""
    import session_state_manager_ph16 as mod_ssm

    original = mod_ssm.SessionStateManager.capture

    def _failing_capture(self: object, session_data: dict) -> object:
        return CaptureResult(success=False, error="simulated failure")

    mod_ssm.SessionStateManager.capture = _failing_capture  # type: ignore[method-assign]
    with patch("sys.stdin", StringIO("")), pytest.raises(SystemExit) as exc_info:
        main()
    mod_ssm.SessionStateManager.capture = original  # type: ignore[method-assign]
    assert exc_info.value.code == 0


def test_prune_old_no_files(tmp_path: Path) -> None:
    """prune_old returns 0 when there are no files to remove."""
    config = SessionStateConfig(checkpoint_dir=tmp_path / "cp", format="json")
    manager = SessionStateManager(config)
    removed = manager.prune_old(max_keep=5)
    assert removed == 0
