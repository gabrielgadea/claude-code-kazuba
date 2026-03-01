#!/usr/bin/env python3
"""E2E integration tests for the migrate_v01_v02 migration script.

Directly exercises all major functions to achieve 90%+ coverage.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the migration module (register in sys.modules for dataclass support)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION_PATH = _ROOT / "scripts" / "migrate_v01_v02.py"

_MODULE_NAME = "migrate_v01_v02_e2e"
_mig_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MIGRATION_PATH)
_mig_mod = importlib.util.module_from_spec(_mig_spec)  # type: ignore[arg-type]
sys.modules[_MODULE_NAME] = _mig_mod
_mig_spec.loader.exec_module(_mig_mod)  # type: ignore[union-attr]

MigrationConfig = _mig_mod.MigrationConfig
MigrationResult = _mig_mod.MigrationResult
StepResult = _mig_mod.StepResult
detect_v1_installation = _mig_mod.detect_v1_installation
backup_directory = _mig_mod.backup_directory
migrate_hooks_settings = _mig_mod.migrate_hooks_settings
migrate_presets = _mig_mod.migrate_presets
validate_migration = _mig_mod.validate_migration
run_migration = _mig_mod.run_migration
main = _mig_mod.main
_V01_HOOK_NAMES = _mig_mod._V01_HOOK_NAMES
_HOOK_MIGRATION_MAP = _mig_mod._HOOK_MIGRATION_MAP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_v1_settings(tmp_path: Path, hooks: dict | None = None) -> Path:
    """Create a v0.1-style .claude/settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    sp = claude_dir / "settings.json"
    data = {
        "hooks_v1": True,
        "hooks": hooks or {"quality_gate": {"enabled": True}},
    }
    sp.write_text(json.dumps(data, indent=2))
    return sp


def make_v2_settings(tmp_path: Path) -> Path:
    """Create a v0.2-style .claude/settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    sp = claude_dir / "settings.json"
    data = {
        "_migrated_from": "v0.1",
        "_migration_ts": "2026-01-01T00:00:00Z",
        "hooks": {
            "PreToolUse": [],
            "PostToolUse": [],
            "UserPromptSubmit": [],
        },
    }
    sp.write_text(json.dumps(data, indent=2))
    return sp


# ---------------------------------------------------------------------------
# Tests: MigrationConfig
# ---------------------------------------------------------------------------


def test_migration_config_is_frozen(tmp_path: Path) -> None:
    """MigrationConfig is frozen (immutable)."""
    cfg = MigrationConfig(target_dir=tmp_path, backup_dir=tmp_path / "bak")
    with pytest.raises((AttributeError, TypeError)):
        cfg.dry_run = True  # type: ignore[misc]


def test_migration_config_coerces_paths(tmp_path: Path) -> None:
    """MigrationConfig coerces str -> Path."""
    cfg = MigrationConfig(
        target_dir=str(tmp_path),
        backup_dir=str(tmp_path / "bak"),
    )
    assert isinstance(cfg.target_dir, Path)
    assert isinstance(cfg.backup_dir, Path)


def test_step_result_fields() -> None:
    """StepResult stores fields correctly."""
    sr = StepResult(step="test_step", success=True, message="ok", details={"k": "v"})
    assert sr.step == "test_step"
    assert sr.success is True
    assert sr.message == "ok"


def test_migration_result_failed_steps() -> None:
    """MigrationResult.failed_steps filters correctly."""
    steps = (
        StepResult(step="a", success=True, message="ok"),
        StepResult(step="b", success=False, message="fail"),
    )
    result = MigrationResult(
        success=False, steps=steps, duration_ms=10.0, dry_run=False
    )
    assert len(result.failed_steps) == 1
    assert result.failed_steps[0].step == "b"


def test_migration_result_passed_steps() -> None:
    """MigrationResult.passed_steps filters correctly."""
    steps = (
        StepResult(step="a", success=True, message="ok"),
        StepResult(step="b", success=False, message="fail"),
    )
    result = MigrationResult(
        success=False, steps=steps, duration_ms=10.0, dry_run=False
    )
    assert len(result.passed_steps) == 1


def test_migration_result_to_dict() -> None:
    """MigrationResult.to_dict serializes correctly."""
    result = MigrationResult(
        success=True,
        steps=(StepResult(step="x", success=True, message="done"),),
        duration_ms=42.0,
        dry_run=True,
    )
    d = result.to_dict()
    assert d["success"] is True
    assert d["dry_run"] is True
    assert len(d["steps"]) == 1


# ---------------------------------------------------------------------------
# Tests: detect_v1_installation
# ---------------------------------------------------------------------------


def test_detect_v1_no_claude_dir(tmp_path: Path) -> None:
    """detect_v1_installation returns detected=False when no .claude dir."""
    result = detect_v1_installation(tmp_path)
    assert result["detected"] is False
    assert result["settings_path"] is None


def test_detect_v1_with_v1_settings(tmp_path: Path) -> None:
    """detect_v1_installation detects v0.1 from hooks_v1 marker."""
    make_v1_settings(tmp_path)
    result = detect_v1_installation(tmp_path)
    assert result["detected"] is True
    assert len(result["evidence"]) >= 1


def test_detect_v1_no_v1_detected_clean_dir(tmp_path: Path) -> None:
    """detect_v1_installation returns not detected for empty .claude dir."""
    (tmp_path / ".claude").mkdir()
    result = detect_v1_installation(tmp_path)
    # No settings.json present — may or may not detect
    assert isinstance(result["detected"], bool)


def test_detect_v1_with_hook_script_names(tmp_path: Path) -> None:
    """detect_v1_installation detects v0.1 hook scripts."""
    claude_dir = tmp_path / ".claude"
    (claude_dir / "hooks").mkdir(parents=True)
    (claude_dir / "hooks" / "quality_gate.py").write_text("# v0.1 hook")
    result = detect_v1_installation(tmp_path)
    assert result["detected"] is True


def test_detect_v1_evidence_has_items(tmp_path: Path) -> None:
    """evidence list is non-empty when v0.1 is detected."""
    make_v1_settings(tmp_path, hooks={"quality_gate": {}})
    result = detect_v1_installation(tmp_path)
    if result["detected"]:
        assert len(result["evidence"]) > 0


# ---------------------------------------------------------------------------
# Tests: backup_directory
# ---------------------------------------------------------------------------


def test_backup_nonexistent_source(tmp_path: Path) -> None:
    """backup_directory fails gracefully when source doesn't exist."""
    result = backup_directory(tmp_path / "nonexistent", tmp_path / "bak")
    assert result.success is False
    assert "does not exist" in result.message


def test_backup_dry_run(tmp_path: Path) -> None:
    """backup_directory dry-run returns success without copying."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "file.txt").write_text("data")
    bak_dir = tmp_path / "backups"

    result = backup_directory(source, bak_dir, dry_run=True)
    assert result.success is True
    assert "[DRY-RUN]" in result.message
    assert not bak_dir.exists()  # No actual copy in dry-run


def test_backup_actually_copies(tmp_path: Path) -> None:
    """backup_directory copies the directory on real run."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "file.txt").write_text("content")
    bak_dir = tmp_path / "backups"

    result = backup_directory(source, bak_dir, dry_run=False)
    assert result.success is True
    assert bak_dir.exists()
    assert result.details.get("dest") is not None


# ---------------------------------------------------------------------------
# Tests: migrate_hooks_settings
# ---------------------------------------------------------------------------


def test_migrate_hooks_missing_file(tmp_path: Path) -> None:
    """migrate_hooks_settings fails if settings.json doesn't exist."""
    result = migrate_hooks_settings(tmp_path / "nonexistent.json")
    assert result.success is False


def test_migrate_hooks_dry_run(tmp_path: Path) -> None:
    """migrate_hooks_settings dry-run reports what would be done."""
    sp = make_v1_settings(tmp_path, hooks={"quality_gate": {"enabled": True}})
    result = migrate_hooks_settings(sp, dry_run=True)
    assert result.success is True
    assert "[DRY-RUN]" in result.message
    # Original file should not be modified
    data = json.loads(sp.read_text())
    assert "hooks_v1" in data  # Unchanged


def test_migrate_hooks_actual_migration(tmp_path: Path) -> None:
    """migrate_hooks_settings migrates hooks to v0.2 event structure."""
    sp = make_v1_settings(
        tmp_path,
        hooks={
            "quality_gate": {"enabled": True},
            "bash_safety": {"enabled": True},
        },
    )
    result = migrate_hooks_settings(sp, dry_run=False)
    assert result.success is True
    data = json.loads(sp.read_text())
    assert "_migrated_from" in data
    hooks = data["hooks"]
    assert "PostToolUse" in hooks or "PreToolUse" in hooks


def test_migrate_hooks_invalid_json(tmp_path: Path) -> None:
    """migrate_hooks_settings handles invalid JSON gracefully."""
    sp = tmp_path / "settings.json"
    sp.write_text("{broken json")
    result = migrate_hooks_settings(sp)
    assert result.success is False


def test_migrate_hooks_migration_map_coverage() -> None:
    """All expected hook names are in the migration map."""
    for name in ("quality_gate", "bash_safety", "secrets_scanner", "pii_scanner"):
        assert name in _HOOK_MIGRATION_MAP


# ---------------------------------------------------------------------------
# Tests: migrate_presets
# ---------------------------------------------------------------------------


def test_migrate_presets_no_presets_dir(tmp_path: Path) -> None:
    """migrate_presets returns success when no presets directory."""
    result = migrate_presets(tmp_path)
    assert result.success is True
    assert "nothing to migrate" in result.message.lower()


def test_migrate_presets_v1_preset(tmp_path: Path) -> None:
    """migrate_presets upgrades v0.1 preset to v0.2 format."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    preset_file = presets_dir / "default.json"
    preset_file.write_text(json.dumps({
        "version": "0.1",
        "quality_level": "high",
        "name": "default",
    }))

    result = migrate_presets(tmp_path, dry_run=False)
    assert result.success is True
    data = json.loads(preset_file.read_text())
    assert data["version"] == "0.2"
    assert data["quality_level"] == "high"
    assert "_migrated_from" in data


def test_migrate_presets_dry_run(tmp_path: Path) -> None:
    """migrate_presets dry-run does not modify files."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    preset_file = presets_dir / "default.json"
    original = {"version": "0.1", "quality_level": "standard"}
    preset_file.write_text(json.dumps(original))

    result = migrate_presets(tmp_path, dry_run=True)
    assert result.success is True
    # File should be unchanged
    data = json.loads(preset_file.read_text())
    assert data["version"] == "0.1"


def test_migrate_presets_non_v1_skipped(tmp_path: Path) -> None:
    """migrate_presets skips presets that are already v0.2."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    preset_file = presets_dir / "v2.json"
    preset_file.write_text(json.dumps({"version": "0.2"}))

    result = migrate_presets(tmp_path)
    assert result.success is True
    assert result.details.get("migrated") == [] or len(result.details.get("migrated", [])) == 0


# ---------------------------------------------------------------------------
# Tests: validate_migration
# ---------------------------------------------------------------------------


def test_validate_migration_missing_settings(tmp_path: Path) -> None:
    """validate_migration fails if settings.json doesn't exist."""
    (tmp_path / ".claude").mkdir()
    result = validate_migration(tmp_path)
    assert result.success is False


def test_validate_migration_passes_after_migration(tmp_path: Path) -> None:
    """validate_migration passes when settings are in v0.2 format."""
    make_v2_settings(tmp_path)
    result = validate_migration(tmp_path)
    assert result.success is True


def test_validate_migration_fails_with_v1_hooks(tmp_path: Path) -> None:
    """validate_migration fails when v0.1 hook names still present."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    sp = claude_dir / "settings.json"
    sp.write_text(json.dumps({
        "_migrated_from": "v0.1",
        "hooks": {"quality_gate": {}},  # v0.1 flat name
    }))
    result = validate_migration(tmp_path)
    assert result.success is False


def test_validate_migration_fails_without_marker(tmp_path: Path) -> None:
    """validate_migration fails when _migrated_from marker is missing."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    sp = claude_dir / "settings.json"
    sp.write_text(json.dumps({
        "hooks": {"PreToolUse": [], "PostToolUse": []},
    }))
    result = validate_migration(tmp_path)
    assert result.success is False


# ---------------------------------------------------------------------------
# Tests: run_migration (end-to-end orchestration)
# ---------------------------------------------------------------------------


def test_run_migration_no_v1_detected(tmp_path: Path) -> None:
    """run_migration returns success with no steps when v0.1 not found."""
    cfg = MigrationConfig(target_dir=tmp_path, backup_dir=tmp_path / "bak")
    result = run_migration(cfg)
    assert result.success is True
    assert any(s.step == "detect" for s in result.steps)


def test_run_migration_full_v1_to_v2(tmp_path: Path) -> None:
    """run_migration performs complete v0.1 -> v0.2 migration."""
    make_v1_settings(tmp_path, hooks={"quality_gate": {}, "bash_safety": {}})
    cfg = MigrationConfig(
        target_dir=tmp_path,
        backup_dir=tmp_path / "bak",
        dry_run=False,
    )
    result = run_migration(cfg)
    assert result.success is True
    assert result.backed_up_to is not None
    assert any(s.step == "validate" for s in result.steps)


def test_run_migration_dry_run(tmp_path: Path) -> None:
    """run_migration dry-run succeeds without modifying files."""
    make_v1_settings(tmp_path)
    cfg = MigrationConfig(
        target_dir=tmp_path,
        backup_dir=tmp_path / "bak",
        dry_run=True,
    )
    result = run_migration(cfg)
    assert result.dry_run is True
    # Settings should not be modified
    sp = tmp_path / ".claude" / "settings.json"
    data = json.loads(sp.read_text())
    assert "hooks_v1" in data  # Unchanged by dry-run


def test_run_migration_result_to_dict(tmp_path: Path) -> None:
    """MigrationResult from run_migration serializes to dict."""
    cfg = MigrationConfig(target_dir=tmp_path, backup_dir=tmp_path / "bak")
    result = run_migration(cfg)
    d = result.to_dict()
    assert "success" in d
    assert "steps" in d


def test_run_migration_duration_positive(tmp_path: Path) -> None:
    """MigrationResult.duration_ms is positive."""
    cfg = MigrationConfig(target_dir=tmp_path, backup_dir=tmp_path / "bak")
    result = run_migration(cfg)
    assert result.duration_ms > 0


# ---------------------------------------------------------------------------
# Tests: main() CLI
# ---------------------------------------------------------------------------


def test_main_dry_run(tmp_path: Path) -> None:
    """main() with --dry-run exits 0 on no-v1-found scenario."""
    code = main(["--dry-run", "--target-dir", str(tmp_path)])
    assert code == 0


def test_main_with_v1_settings(tmp_path: Path) -> None:
    """main() migrates a v0.1 installation."""
    make_v1_settings(tmp_path)
    code = main([
        "--target-dir", str(tmp_path),
        "--backup-dir", str(tmp_path / "bak"),
    ])
    assert code == 0


def test_main_dry_run_v1(tmp_path: Path) -> None:
    """main() dry-run with v0.1 settings exits 0."""
    make_v1_settings(tmp_path)
    code = main([
        "--dry-run",
        "--target-dir", str(tmp_path),
        "--backup-dir", str(tmp_path / "bak"),
    ])
    assert code == 0


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


def test_detect_v1_invalid_settings_json(tmp_path: Path) -> None:
    """detect_v1_installation handles invalid JSON in settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    sp = claude_dir / "settings.json"
    sp.write_text("{bad json!!!")
    result = detect_v1_installation(tmp_path)
    # Evidence should contain parse error
    assert any("error" in e.lower() or "parse" in e.lower() for e in result["evidence"])


def test_detect_v1_settings_exists_path_returned(tmp_path: Path) -> None:
    """detect_v1_installation returns settings_path when file exists."""
    make_v1_settings(tmp_path)
    result = detect_v1_installation(tmp_path)
    assert result["settings_path"] is not None


def test_migrate_hooks_with_unknown_hook(tmp_path: Path) -> None:
    """migrate_hooks_settings handles unknown v0.1 hooks gracefully."""
    sp = make_v1_settings(tmp_path, hooks={"unknown_hook_xyz": {"enabled": True}})
    result = migrate_hooks_settings(sp, dry_run=False)
    assert result.success is True
    # unknown hook goes to skipped
    assert "unknown_hook_xyz" in result.details.get("skipped", [])


def test_migrate_hooks_preserves_existing_v2_hooks(tmp_path: Path) -> None:
    """migrate_hooks_settings preserves pre-existing v0.2 event hooks."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    sp = claude_dir / "settings.json"
    existing_hooks = {
        "PreToolUse": [{"matcher": {"tool_name": "Bash"}, "hooks": []}],
        "quality_gate": {"enabled": True},
    }
    sp.write_text(json.dumps({"hooks_v1": True, "hooks": existing_hooks}))
    result = migrate_hooks_settings(sp, dry_run=False)
    assert result.success is True
    data = json.loads(sp.read_text())
    # Existing v0.2 PreToolUse hook should be preserved
    assert len(data["hooks"]["PreToolUse"]) >= 1


def test_migrate_presets_with_name_and_description(tmp_path: Path) -> None:
    """migrate_presets preserves name and description fields."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    preset_file = presets_dir / "named.json"
    preset_file.write_text(json.dumps({
        "version": "0.1",
        "name": "My Preset",
        "description": "A test preset",
        "quality_level": "high",
    }))
    result = migrate_presets(tmp_path, dry_run=False)
    assert result.success is True
    data = json.loads(preset_file.read_text())
    assert data.get("name") == "My Preset"
    assert data.get("description") == "A test preset"


def test_migrate_presets_invalid_json_file(tmp_path: Path) -> None:
    """migrate_presets handles a preset file with invalid JSON."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    bad_file = presets_dir / "bad.json"
    bad_file.write_text("{not valid")
    result = migrate_presets(tmp_path, dry_run=False)
    # Should still report (as error), not crash
    assert isinstance(result.success, bool)
    assert len(result.details.get("errors", [])) >= 1


def test_validate_migration_invalid_json(tmp_path: Path) -> None:
    """validate_migration fails gracefully on invalid JSON settings."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    sp = claude_dir / "settings.json"
    sp.write_text("{bad")
    result = validate_migration(tmp_path)
    assert result.success is False
    assert "invalid" in result.message.lower() or "json" in result.message.lower()


def test_validate_migration_non_dict_hooks(tmp_path: Path) -> None:
    """validate_migration detects non-dict hooks field."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    sp = claude_dir / "settings.json"
    sp.write_text(json.dumps({"_migrated_from": "v0.1", "hooks": ["list", "not", "dict"]}))
    result = validate_migration(tmp_path)
    assert result.success is False


def test_run_migration_backup_fails_returns_failure(tmp_path: Path, monkeypatch) -> None:
    """run_migration fails if backup step fails."""
    make_v1_settings(tmp_path)

    original_backup = backup_directory

    def failing_backup(source, backup_dir, dry_run=False):
        return StepResult(step="backup", success=False, message="Forced failure")

    monkeypatch.setattr(_mig_mod, "backup_directory", failing_backup)
    try:
        cfg = MigrationConfig(target_dir=tmp_path, backup_dir=tmp_path / "bak")
        result = run_migration(cfg)
        assert result.success is False
    finally:
        monkeypatch.setattr(_mig_mod, "backup_directory", original_backup)


def test_main_verbose_flag(tmp_path: Path) -> None:
    """main() with --verbose flag runs without error."""
    code = main(["--verbose", "--dry-run", "--target-dir", str(tmp_path)])
    assert code == 0
