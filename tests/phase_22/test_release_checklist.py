"""Release readiness checklist tests — Phase 22: Release v0.2.0.

These tests verify that all preconditions for a v0.2.0 release are met:
  - Phase checkpoints exist (15-21)
  - Core library files are present
  - Documentation is in place
  - Migration guide exists
  - No obvious structural gaps
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINTS_DIR = PROJECT_ROOT / "checkpoints"
DOCS_DIR = PROJECT_ROOT / "docs"
LIB_DIR = PROJECT_ROOT / "lib"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


# ---------------------------------------------------------------------------
# Checkpoint existence (phases 15–21 must have been completed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phase_id", [15, 16, 17, 18, 19, 20, 21])
def test_phase_checkpoint_exists(phase_id: int) -> None:
    """Checkpoint file for phase {phase_id} must exist."""
    checkpoint = CHECKPOINTS_DIR / f"phase_{phase_id}.toon"
    assert checkpoint.exists(), (
        f"Missing checkpoint for phase {phase_id}: {checkpoint}"
    )


# ---------------------------------------------------------------------------
# Core library files
# ---------------------------------------------------------------------------


def test_rlm_facade_exists() -> None:
    """lib/rlm.py (RLM facade) must exist."""
    assert (LIB_DIR / "rlm.py").exists(), "lib/rlm.py not found"


def test_lib_init_exists() -> None:
    """lib/__init__.py must exist."""
    assert (LIB_DIR / "__init__.py").exists(), "lib/__init__.py not found"


# ---------------------------------------------------------------------------
# Documentation completeness
# ---------------------------------------------------------------------------


def test_migration_guide_exists() -> None:
    """docs/MIGRATION.md must exist (required in release)."""
    migration = DOCS_DIR / "MIGRATION.md"
    assert migration.exists(), "docs/MIGRATION.md not found"


def test_migration_guide_has_content() -> None:
    """docs/MIGRATION.md must have at least 80 lines."""
    migration = DOCS_DIR / "MIGRATION.md"
    lines = migration.read_text().splitlines()
    assert len(lines) >= 80, f"MIGRATION.md has only {len(lines)} lines"


def test_readme_exists() -> None:
    """README.md must exist at project root."""
    readme = PROJECT_ROOT / "README.md"
    assert readme.exists(), "README.md not found at project root"


# ---------------------------------------------------------------------------
# Release artifacts
# ---------------------------------------------------------------------------


def test_benchmark_script_exists() -> None:
    """scripts/benchmark_hooks.py must exist for the release."""
    assert (SCRIPTS_DIR / "benchmark_hooks.py").exists(), (
        "scripts/benchmark_hooks.py not found"
    )


def test_migration_script_exists() -> None:
    """scripts/migrate_v01_v02.py must exist."""
    assert (SCRIPTS_DIR / "migrate_v01_v02.py").exists(), (
        "scripts/migrate_v01_v02.py not found"
    )


def test_self_host_config_exists() -> None:
    """Self-hosting hook config must exist."""
    self_host = PROJECT_ROOT / ".claude" / "hooks" / "self_host_config.py"
    assert self_host.exists(), ".claude/hooks/self_host_config.py not found"


def test_checkpoints_dir_exists() -> None:
    """checkpoints/ directory must exist."""
    assert CHECKPOINTS_DIR.exists() and CHECKPOINTS_DIR.is_dir()
