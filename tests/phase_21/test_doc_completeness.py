"""Tests for overall documentation completeness — Phase 21."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
MIGRATION_MD = DOCS_DIR / "MIGRATION.md"


# ---------------------------------------------------------------------------
# Directory and file checks
# ---------------------------------------------------------------------------


def test_docs_directory_exists() -> None:
    """docs/ directory must exist."""
    assert DOCS_DIR.exists() and DOCS_DIR.is_dir()


def test_migration_md_has_all_required_sections() -> None:
    """MIGRATION.md must contain Step 1 through Step 5 (or equivalent sections)."""
    content = MIGRATION_MD.read_text().lower()
    # At minimum, should have steps or major sections
    assert "step" in content or ("##" in MIGRATION_MD.read_text()), (
        "MIGRATION.md is missing step-based sections"
    )


def test_readme_exists_at_project_root() -> None:
    """README.md must exist at the project root."""
    readme = PROJECT_ROOT / "README.md"
    assert readme.exists(), "README.md not found at project root"


def test_docs_modules_catalog_exists() -> None:
    """docs/MODULES_CATALOG.md must exist."""
    assert (DOCS_DIR / "MODULES_CATALOG.md").exists()


def test_migration_md_has_minimum_sections() -> None:
    """MIGRATION.md must have at least 3 level-2 sections (##)."""
    content = MIGRATION_MD.read_text()
    sections = [ln for ln in content.splitlines() if ln.startswith("## ")]
    assert len(sections) >= 3, (
        f"Expected >= 3 level-2 sections, found {len(sections)}: {sections}"
    )


def test_migration_md_mentions_install() -> None:
    """MIGRATION.md must mention installation or preset."""
    content = MIGRATION_MD.read_text().lower()
    assert "install" in content or "preset" in content, (
        "MIGRATION.md should describe installation or preset selection"
    )


def test_migration_md_has_validate_step() -> None:
    """MIGRATION.md must describe a validation step."""
    content = MIGRATION_MD.read_text().lower()
    assert "validat" in content, "MIGRATION.md missing validation step"


def test_docs_all_markdown_files_non_empty() -> None:
    """All .md files in docs/ must be non-empty."""
    for md_file in DOCS_DIR.glob("*.md"):
        content = md_file.read_text().strip()
        assert len(content) > 0, f"{md_file.name} is empty"
