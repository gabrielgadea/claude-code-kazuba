"""Phase 0 Tests: Verify project structure and bootstrap files."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


class TestDirectoryStructure:
    """Verify all required directories exist."""

    REQUIRED_DIRS = [
        "claude_code_kazuba",
        "tests",
        "scripts",
        "plans",
        "plans/validation",
        "modules",
        "presets",
        "docs",
        "core",
        "core/rules",
        "checkpoints",
        ".claude",
        ".github/workflows",
    ]

    @pytest.mark.parametrize("dir_path", REQUIRED_DIRS)
    def test_directory_exists(self, project_root: Path, dir_path: str) -> None:
        assert (project_root / dir_path).is_dir(), f"Directory {dir_path} missing"


class TestBootstrapFiles:
    """Verify all bootstrap files exist and have minimum content."""

    FILES_AND_MIN_LINES = [
        ("pyproject.toml", 40),
        (".gitignore", 15),
        ("LICENSE", 15),
        ("claude_code_kazuba/__init__.py", 3),
        ("tests/__init__.py", 0),
        ("tests/conftest.py", 15),
        (".claude/CLAUDE.md", 20),
        (".claude/settings.json", 10),
    ]

    @pytest.mark.parametrize("file_path,min_lines", FILES_AND_MIN_LINES)
    def test_file_exists_and_has_content(
        self, project_root: Path, file_path: str, min_lines: int
    ) -> None:
        full_path = project_root / file_path
        assert full_path.is_file(), f"File {file_path} missing"
        lines = len(full_path.read_text().splitlines())
        assert lines >= min_lines, f"{file_path}: {lines} lines < {min_lines} required"


class TestPyprojectToml:
    """Verify pyproject.toml has correct configuration."""

    def test_has_project_section(self, project_root: Path) -> None:
        content = (project_root / "pyproject.toml").read_text()
        assert "[project]" in content

    def test_requires_python_312(self, project_root: Path) -> None:
        content = (project_root / "pyproject.toml").read_text()
        assert ">=3.12" in content

    def test_has_dependencies(self, project_root: Path) -> None:
        content = (project_root / "pyproject.toml").read_text()
        for dep in ["pydantic", "msgpack", "pyyaml", "jinja2"]:
            assert dep in content.lower(), f"Dependency {dep} missing"

    def test_has_dev_dependencies(self, project_root: Path) -> None:
        content = (project_root / "pyproject.toml").read_text()
        for dep in ["pytest", "ruff", "pyright"]:
            assert dep in content.lower(), f"Dev dependency {dep} missing"

    def test_has_ruff_config(self, project_root: Path) -> None:
        content = (project_root / "pyproject.toml").read_text()
        assert "[tool.ruff]" in content

    def test_has_pyright_config(self, project_root: Path) -> None:
        content = (project_root / "pyproject.toml").read_text()
        assert "[tool.pyright]" in content

    def test_has_pytest_config(self, project_root: Path) -> None:
        content = (project_root / "pyproject.toml").read_text()
        assert "[tool.pytest.ini_options]" in content


class TestGitignore:
    """Verify .gitignore has essential patterns."""

    REQUIRED_PATTERNS = [
        "__pycache__",
        ".venv",
        "settings.local.json",
        "*.toon",
        ".coverage",
    ]

    @pytest.mark.parametrize("pattern", REQUIRED_PATTERNS)
    def test_pattern_present(self, project_root: Path, pattern: str) -> None:
        content = (project_root / ".gitignore").read_text()
        assert pattern in content, f"Pattern '{pattern}' missing from .gitignore"


class TestLibInit:
    """Verify lib package is importable."""

    def test_has_version(self, project_root: Path) -> None:
        content = (project_root / "claude_code_kazuba" / "__init__.py").read_text()
        assert "__version__" in content

    def test_has_future_annotations(self, project_root: Path) -> None:
        content = (project_root / "claude_code_kazuba" / "__init__.py").read_text()
        assert "from __future__ import annotations" in content


class TestClaudeConfig:
    """Verify .claude/ self-hosting configuration."""

    def test_claude_md_has_stack(self, project_root: Path) -> None:
        content = (project_root / ".claude" / "CLAUDE.md").read_text()
        assert "Python 3.12" in content

    def test_settings_has_schema(self, project_root: Path) -> None:
        import json

        settings = json.loads((project_root / ".claude" / "settings.json").read_text())
        assert "$schema" in settings

    def test_settings_has_permissions(self, project_root: Path) -> None:
        import json

        settings = json.loads((project_root / ".claude" / "settings.json").read_text())
        assert "permissions" in settings


class TestPlanFiles:
    """Verify plan files were generated."""

    def test_index_exists(self, project_root: Path) -> None:
        assert (project_root / "plans" / "00-index.md").is_file()

    def test_all_phase_files_exist(self, project_root: Path) -> None:
        plans_dir = project_root / "plans"
        phase_files = list(plans_dir.glob("*-phase-*.md"))
        assert len(phase_files) == 11, f"Expected 11 phase files, got {len(phase_files)}"

    def test_all_validation_scripts_exist(self, project_root: Path) -> None:
        val_dir = project_root / "plans" / "validation"
        scripts = list(val_dir.glob("validate_phase_*.py"))
        assert len(scripts) == 11, f"Expected 11 validation scripts, got {len(scripts)}"

    def test_validate_all_exists(self, project_root: Path) -> None:
        assert (project_root / "plans" / "validation" / "validate_all.py").is_file()
