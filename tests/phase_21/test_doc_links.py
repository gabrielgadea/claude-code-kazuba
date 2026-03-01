"""Tests for docs/MIGRATION.md — cross-references and link integrity."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_MD = PROJECT_ROOT / "docs" / "MIGRATION.md"
DOCS_DIR = PROJECT_ROOT / "docs"


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_migration_md_exists() -> None:
    """docs/MIGRATION.md must exist."""
    assert MIGRATION_MD.exists(), "docs/MIGRATION.md not found"


def test_migration_md_minimum_lines() -> None:
    """docs/MIGRATION.md must have at least 80 lines."""
    content = MIGRATION_MD.read_text()
    lines = content.splitlines()
    assert len(lines) >= 80, f"Expected >= 80 lines, got {len(lines)}"


def test_migration_md_is_not_empty() -> None:
    """docs/MIGRATION.md must not be empty."""
    content = MIGRATION_MD.read_text().strip()
    assert len(content) > 0, "docs/MIGRATION.md is empty"


# ---------------------------------------------------------------------------
# Content structure
# ---------------------------------------------------------------------------


def test_migration_md_has_title_header() -> None:
    """MIGRATION.md must start with a markdown title."""
    content = MIGRATION_MD.read_text()
    lines = [ln for ln in content.splitlines() if ln.strip()]
    assert lines[0].startswith("#"), f"First non-empty line is not a header: {lines[0]!r}"


def test_migration_md_mentions_backup() -> None:
    """MIGRATION.md must mention backup (critical safety step)."""
    content = MIGRATION_MD.read_text().lower()
    assert "backup" in content, "MIGRATION.md does not mention 'backup'"


def test_migration_md_mentions_hooks() -> None:
    """MIGRATION.md must reference hooks (key migration component)."""
    content = MIGRATION_MD.read_text().lower()
    assert "hook" in content, "MIGRATION.md does not mention 'hooks'"


def test_migration_md_mentions_settings() -> None:
    """MIGRATION.md must mention settings.json."""
    content = MIGRATION_MD.read_text()
    assert "settings.json" in content, "MIGRATION.md does not mention settings.json"


def test_migration_md_has_rollback_section() -> None:
    """MIGRATION.md must include a rollback procedure."""
    content = MIGRATION_MD.read_text().lower()
    assert "rollback" in content, "MIGRATION.md is missing a rollback section"


def test_migration_md_has_code_blocks() -> None:
    """MIGRATION.md must include code examples (``` blocks)."""
    content = MIGRATION_MD.read_text()
    assert "```" in content, "MIGRATION.md has no code blocks"


def test_migration_md_mentions_steps_or_procedure() -> None:
    """MIGRATION.md must outline procedural steps."""
    content = MIGRATION_MD.read_text().lower()
    has_steps = "step" in content or "## " in content
    assert has_steps, "MIGRATION.md lacks step-by-step structure"


# ---------------------------------------------------------------------------
# Cross-references to other docs
# ---------------------------------------------------------------------------


def test_migration_md_references_creating_modules_doc() -> None:
    """MIGRATION.md must reference CREATING_MODULES.md for custom hooks."""
    content = MIGRATION_MD.read_text()
    assert "CREATING_MODULES" in content, (
        "MIGRATION.md should reference docs/CREATING_MODULES.md"
    )


def test_docs_creating_modules_exists() -> None:
    """The referenced docs/CREATING_MODULES.md must exist."""
    assert (DOCS_DIR / "CREATING_MODULES.md").exists()


def test_docs_architecture_exists() -> None:
    """docs/ARCHITECTURE.md must exist."""
    assert (DOCS_DIR / "ARCHITECTURE.md").exists()


def test_docs_hooks_reference_exists() -> None:
    """docs/HOOKS_REFERENCE.md must exist."""
    assert (DOCS_DIR / "HOOKS_REFERENCE.md").exists()
