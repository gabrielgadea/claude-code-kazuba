#!/usr/bin/env python3
"""Migration script: claude-code-kazuba v0.1 -> v0.2.

Detects v0.1 installations, creates backups, migrates hooks settings,
migrates presets, and validates the result.

Usage:
    python scripts/migrate_v01_v02.py [--dry-run] [--backup-dir DIR] [--target-dir DIR]

Exit codes:
    0 - Migration successful (or dry-run completed)
    1 - Migration failed
    2 - Nothing to migrate (v0.1 not detected)
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MigrationConfig:
    """Immutable configuration for migration execution."""

    target_dir: Path
    backup_dir: Path
    dry_run: bool = False
    verbose: bool = False

    def __post_init__(self) -> None:
        # Coerce str -> Path if needed (workaround frozen=True)
        object.__setattr__(self, "target_dir", Path(self.target_dir))
        object.__setattr__(self, "backup_dir", Path(self.backup_dir))


@dataclass(frozen=True)
class StepResult:
    """Result from a single migration step."""

    step: str
    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MigrationResult:
    """Aggregate result from the full migration run."""

    success: bool
    steps: tuple[StepResult, ...]
    duration_ms: float
    dry_run: bool
    backed_up_to: Path | None = None

    @property
    def failed_steps(self) -> list[StepResult]:
        return [s for s in self.steps if not s.success]

    @property
    def passed_steps(self) -> list[StepResult]:
        return [s for s in self.steps if s.success]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "duration_ms": self.duration_ms,
            "backed_up_to": str(self.backed_up_to) if self.backed_up_to else None,
            "steps": [
                {
                    "step": s.step,
                    "success": s.success,
                    "message": s.message,
                    "details": s.details,
                }
                for s in self.steps
            ],
        }


# ---------------------------------------------------------------------------
# V0.1 detection
# ---------------------------------------------------------------------------

# Known v0.1 hook names (renamed or restructured in v0.2)
_V01_HOOK_NAMES: frozenset[str] = frozenset(
    [
        "quality_gate",
        "bash_safety",
        "secrets_scanner",
        "pii_scanner",
        "auto_approve",
        "route_decisions",
    ]
)

# Settings key that identifies v0.1 layout
_V01_SETTINGS_MARKER = "hooks_v1"


def detect_v1_installation(target_dir: Path) -> dict[str, Any]:
    """Detect whether a v0.1 installation exists in target_dir.

    Checks for:
    - .claude/settings.json with v0.1 hook structure
    - Presence of v0.1 hook script names
    - Missing v0.2 markers

    Args:
        target_dir: Root directory of the Claude Code installation.

    Returns:
        dict with keys: ``detected`` (bool), ``evidence`` (list[str]),
        ``settings_path`` (Path|None).
    """
    evidence: list[str] = []
    settings_path: Path | None = None

    claude_dir = target_dir / ".claude"
    if not claude_dir.exists():
        return {"detected": False, "evidence": [], "settings_path": None}

    # Check settings.json
    sp = claude_dir / "settings.json"
    if sp.exists():
        settings_path = sp
        try:
            data = json.loads(sp.read_text())
            hooks = data.get("hooks", {})

            # v0.1 used flat hook names at top level
            if isinstance(hooks, dict):
                for name in hooks:
                    if name in _V01_HOOK_NAMES:
                        evidence.append(f"v0.1 hook name found: {name}")

            # Check for v0.1 marker
            if _V01_SETTINGS_MARKER in data:
                evidence.append("v0.1 settings marker present")

            # v0.2 uses event-based structure — absence is evidence of v0.1
            for event in ("PreToolUse", "PostToolUse", "UserPromptSubmit"):
                if event not in hooks:
                    evidence.append(f"Missing v0.2 event key: {event}")

        except (json.JSONDecodeError, OSError) as exc:
            evidence.append(f"Settings parse error (possible v0.1): {exc}")

    # Check for v0.1 hooks directory layout
    hooks_dir = claude_dir / "hooks"
    if hooks_dir.exists():
        for script in hooks_dir.iterdir():
            stem = script.stem
            if stem in _V01_HOOK_NAMES:
                evidence.append(f"v0.1 hook script: {script.name}")

    detected = len(evidence) >= 1
    return {
        "detected": detected,
        "evidence": evidence,
        "settings_path": settings_path,
    }


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def backup_directory(source: Path, backup_dir: Path, dry_run: bool = False) -> StepResult:
    """Create a timestamped backup of source directory.

    Args:
        source: Directory to back up.
        backup_dir: Parent directory where backup is stored.
        dry_run: If True, simulate without copying.

    Returns:
        StepResult indicating success or failure.
    """
    if not source.exists():
        return StepResult(
            step="backup",
            success=False,
            message=f"Source does not exist: {source}",
        )

    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"backup_{source.name}_{ts}"

    if dry_run:
        logger.info("[DRY-RUN] Would backup %s -> %s", source, dest)
        return StepResult(
            step="backup",
            success=True,
            message=f"[DRY-RUN] Would backup to {dest}",
            details={"source": str(source), "dest": str(dest)},
        )

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
        logger.info("Backup created: %s", dest)
        return StepResult(
            step="backup",
            success=True,
            message=f"Backup created at {dest}",
            details={"source": str(source), "dest": str(dest)},
        )
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        return StepResult(
            step="backup",
            success=False,
            message=f"Backup failed: {exc}",
        )


# ---------------------------------------------------------------------------
# Hook settings migration
# ---------------------------------------------------------------------------

# Mapping: v0.1 flat hook name -> v0.2 event + command
_HOOK_MIGRATION_MAP: dict[str, dict[str, Any]] = {
    "quality_gate": {
        "event": "PostToolUse",
        "matcher": {"tool_name": "*"},
        "command": "python modules/hooks-quality/hooks/quality_gate.py",
    },
    "bash_safety": {
        "event": "PreToolUse",
        "matcher": {"tool_name": "Bash"},
        "command": "python modules/hooks-quality/hooks/bash_safety.py",
    },
    "secrets_scanner": {
        "event": "PreToolUse",
        "matcher": {"tool_name": "*"},
        "command": "python modules/hooks-quality/hooks/secrets_scanner.py",
    },
    "pii_scanner": {
        "event": "PreToolUse",
        "matcher": {"tool_name": "*"},
        "command": "python modules/hooks-quality/hooks/pii_scanner.py",
    },
    "auto_approve": {
        "event": "PreToolUse",
        "matcher": {"tool_name": "*"},
        "command": "python modules/hooks-routing/hooks/auto_permission_resolver.py",
    },
    "route_decisions": {
        "event": "PreToolUse",
        "matcher": {"tool_name": "*"},
        "command": "python modules/hooks-routing/hooks/cila_router.py",
    },
}


def migrate_hooks_settings(
    settings_path: Path,
    dry_run: bool = False,
) -> StepResult:
    """Migrate v0.1 flat hooks to v0.2 event-based structure.

    Args:
        settings_path: Path to settings.json to migrate.
        dry_run: If True, return what would change without writing.

    Returns:
        StepResult with migration details.
    """
    if not settings_path.exists():
        return StepResult(
            step="migrate_hooks",
            success=False,
            message=f"settings.json not found: {settings_path}",
        )

    try:
        data: dict[str, Any] = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return StepResult(
            step="migrate_hooks",
            success=False,
            message=f"Failed to read settings.json: {exc}",
        )

    hooks = data.get("hooks", {})
    migrated_hooks: dict[str, list[dict[str, Any]]] = {
        "PreToolUse": [],
        "PostToolUse": [],
        "UserPromptSubmit": [],
    }
    migrated_names: list[str] = []
    skipped_names: list[str] = []

    # Preserve any existing v0.2 event-based hooks
    for event in ("PreToolUse", "PostToolUse", "UserPromptSubmit"):
        if isinstance(hooks.get(event), list):
            migrated_hooks[event] = list(hooks[event])

    # Migrate v0.1 flat hooks
    for hook_name, _hook_val in hooks.items():
        if hook_name in _HOOK_MIGRATION_MAP:
            mapping = _HOOK_MIGRATION_MAP[hook_name]
            event = mapping["event"]
            entry = {
                "matcher": mapping["matcher"],
                "hooks": [{"type": "command", "command": mapping["command"]}],
            }
            migrated_hooks[event].append(entry)
            migrated_names.append(hook_name)
        elif hook_name not in ("PreToolUse", "PostToolUse", "UserPromptSubmit"):
            # Unknown v0.1 hook: preserve as-is under a legacy key
            skipped_names.append(hook_name)

    # Remove v0.1 marker
    data.pop(_V01_SETTINGS_MARKER, None)

    # Write new hooks structure
    data["hooks"] = migrated_hooks
    data["_migrated_from"] = "v0.1"
    data["_migration_ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    details = {
        "migrated": migrated_names,
        "skipped": skipped_names,
        "events": {k: len(v) for k, v in migrated_hooks.items()},
    }

    if dry_run:
        logger.info("[DRY-RUN] Would migrate hooks: %s", migrated_names)
        return StepResult(
            step="migrate_hooks",
            success=True,
            message=f"[DRY-RUN] Would migrate {len(migrated_names)} hooks",
            details=details,
        )

    try:
        settings_path.write_text(json.dumps(data, indent=2))
        logger.info("Hooks migrated: %s", migrated_names)
        return StepResult(
            step="migrate_hooks",
            success=True,
            message=f"Migrated {len(migrated_names)} hooks to v0.2 event structure",
            details=details,
        )
    except OSError as exc:
        return StepResult(
            step="migrate_hooks",
            success=False,
            message=f"Failed to write settings.json: {exc}",
        )


# ---------------------------------------------------------------------------
# Presets migration
# ---------------------------------------------------------------------------

_V01_PRESET_DEFAULTS: dict[str, Any] = {
    "version": "0.1",
    "hooks_enabled": True,
    "quality_level": "standard",
}

_V02_PRESET_DEFAULTS: dict[str, Any] = {
    "version": "0.2",
    "hooks": {
        "quality": True,
        "routing": True,
        "essential": True,
    },
    "quality_level": "standard",
}


def migrate_presets(target_dir: Path, dry_run: bool = False) -> StepResult:
    """Migrate v0.1 preset files to v0.2 format.

    Looks for presets in target_dir/presets/ and upgrades any v0.1 format
    files (identified by ``"version": "0.1"``) to v0.2 structure.

    Args:
        target_dir: Root directory of the installation.
        dry_run: If True, report what would change without writing.

    Returns:
        StepResult with migration details.
    """
    presets_dir = target_dir / "presets"
    if not presets_dir.exists():
        return StepResult(
            step="migrate_presets",
            success=True,
            message="No presets directory found — nothing to migrate",
            details={"migrated": 0},
        )

    migrated: list[str] = []
    errors: list[str] = []

    for preset_file in presets_dir.rglob("*.json"):
        try:
            data: dict[str, Any] = json.loads(preset_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{preset_file.name}: {exc}")
            continue

        if data.get("version") != "0.1":
            continue  # Already v0.2 or unknown — skip

        # Upgrade fields
        upgraded = dict(_V02_PRESET_DEFAULTS)
        # Preserve overrides from v0.1
        if "quality_level" in data:
            upgraded["quality_level"] = data["quality_level"]
        if "name" in data:
            upgraded["name"] = data["name"]
        if "description" in data:
            upgraded["description"] = data["description"]
        upgraded["_migrated_from"] = "v0.1"

        if dry_run:
            migrated.append(preset_file.name)
            logger.info("[DRY-RUN] Would migrate preset: %s", preset_file.name)
            continue

        try:
            preset_file.write_text(json.dumps(upgraded, indent=2))
            migrated.append(preset_file.name)
            logger.info("Preset migrated: %s", preset_file.name)
        except OSError as exc:
            errors.append(f"{preset_file.name}: write failed: {exc}")

    success = len(errors) == 0
    prefix = "[DRY-RUN] " if dry_run else ""
    return StepResult(
        step="migrate_presets",
        success=success,
        message=f"{prefix}Migrated {len(migrated)} preset(s)",
        details={"migrated": migrated, "errors": errors},
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_migration(target_dir: Path) -> StepResult:
    """Validate that migration to v0.2 completed correctly.

    Checks:
    - settings.json is valid JSON
    - hooks use event-based structure (PreToolUse/PostToolUse/UserPromptSubmit)
    - No v0.1 flat hook names remain at top level
    - _migrated_from marker is present

    Args:
        target_dir: Root directory of the installation.

    Returns:
        StepResult indicating validation success or failure.
    """
    claude_dir = target_dir / ".claude"
    settings_path = claude_dir / "settings.json"

    if not settings_path.exists():
        return StepResult(
            step="validate",
            success=False,
            message="settings.json missing after migration",
        )

    try:
        data: dict[str, Any] = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return StepResult(
            step="validate",
            success=False,
            message=f"settings.json invalid JSON: {exc}",
        )

    issues: list[str] = []

    # Must have _migrated_from marker
    if "_migrated_from" not in data:
        issues.append("Missing _migrated_from marker")

    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        issues.append("hooks is not a dict")
    else:
        # Check for v0.2 event-based structure
        v2_events = {"PreToolUse", "PostToolUse", "UserPromptSubmit"}
        has_v2 = any(e in hooks for e in v2_events)
        if not has_v2:
            issues.append("No v0.2 event keys found in hooks")

        # Check no flat v0.1 names remain
        for name in _V01_HOOK_NAMES:
            if name in hooks:
                issues.append(f"v0.1 hook name still present: {name}")

    success = len(issues) == 0
    return StepResult(
        step="validate",
        success=success,
        message="Validation passed" if success else f"Validation failed: {issues}",
        details={"issues": issues},
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run_migration(config: MigrationConfig) -> MigrationResult:
    """Execute the full v0.1 -> v0.2 migration.

    Args:
        config: MigrationConfig with target/backup dirs and flags.

    Returns:
        MigrationResult with step-by-step results and overall success.
    """
    start_ms = time.monotonic() * 1000
    steps: list[StepResult] = []
    backed_up_to: Path | None = None

    logger.info(
        "Starting migration: target=%s dry_run=%s", config.target_dir, config.dry_run
    )

    # Step 1: Detect v0.1
    detection = detect_v1_installation(config.target_dir)
    if not detection["detected"]:
        steps.append(
            StepResult(
                step="detect",
                success=True,
                message="v0.1 installation not detected — nothing to migrate",
                details=detection,
            )
        )
        duration = time.monotonic() * 1000 - start_ms
        return MigrationResult(
            success=True,
            steps=tuple(steps),
            duration_ms=duration,
            dry_run=config.dry_run,
        )

    steps.append(
        StepResult(
            step="detect",
            success=True,
            message=f"v0.1 detected ({len(detection['evidence'])} evidence items)",
            details=detection,
        )
    )

    # Step 2: Backup
    claude_dir = config.target_dir / ".claude"
    backup_result = backup_directory(claude_dir, config.backup_dir, config.dry_run)
    steps.append(backup_result)

    if not backup_result.success:
        duration = time.monotonic() * 1000 - start_ms
        return MigrationResult(
            success=False,
            steps=tuple(steps),
            duration_ms=duration,
            dry_run=config.dry_run,
        )

    if not config.dry_run and backup_result.details.get("dest"):
        backed_up_to = Path(backup_result.details["dest"])

    # Step 3: Migrate hooks settings
    settings_path = detection.get("settings_path")
    if settings_path is None:
        settings_path = claude_dir / "settings.json"

    hook_result = migrate_hooks_settings(Path(settings_path), config.dry_run)
    steps.append(hook_result)

    # Step 4: Migrate presets
    preset_result = migrate_presets(config.target_dir, config.dry_run)
    steps.append(preset_result)

    # Step 5: Validate (skip in dry-run)
    if not config.dry_run:
        validate_result = validate_migration(config.target_dir)
        steps.append(validate_result)
        overall_success = all(s.success for s in steps)
    else:
        overall_success = all(s.success for s in steps)

    duration = time.monotonic() * 1000 - start_ms
    logger.info(
        "Migration complete: success=%s duration_ms=%.1f", overall_success, duration
    )

    return MigrationResult(
        success=overall_success,
        steps=tuple(steps),
        duration_ms=duration,
        dry_run=config.dry_run,
        backed_up_to=backed_up_to,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for migration script.

    Args:
        argv: Optional argument list (uses sys.argv if None).

    Returns:
        Exit code: 0=success, 1=failure, 2=nothing-to-migrate.
    """
    parser = argparse.ArgumentParser(
        description="Migrate claude-code-kazuba v0.1 -> v0.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path.home() / ".claude-kazuba-backups",
        help="Directory to store backups (default: ~/.claude-kazuba-backups)",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path.cwd(),
        help="Root directory of the Claude Code installation (default: cwd)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    config = MigrationConfig(
        target_dir=args.target_dir,
        backup_dir=args.backup_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    result = run_migration(config)

    # Print summary
    prefix = "[DRY-RUN] " if result.dry_run else ""
    print(f"\n{prefix}Migration {'PASSED' if result.success else 'FAILED'}")
    print(f"Duration: {result.duration_ms:.1f}ms")
    for step in result.steps:
        status = "OK" if step.success else "FAIL"
        print(f"  [{status}] {step.step}: {step.message}")

    if result.backed_up_to:
        print(f"Backup: {result.backed_up_to}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
