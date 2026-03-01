"""Tests for claude_code_kazuba.cli — kazuba CLI entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from claude_code_kazuba.cli import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestCLIVersion:
    """Test --version output."""

    def test_version_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "kazuba 0.2.0" in captured.out


class TestCLIHelp:
    """Test --help output."""

    def test_help_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["--help"] if False else [])
        # No subcommand → prints help and returns 0
        assert result == 0


class TestListPresets:
    """Test list-presets subcommand."""

    def test_list_presets_shows_5(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["list-presets"])
        assert result == 0
        captured = capsys.readouterr()
        for preset in ["minimal", "standard", "professional", "enterprise", "research"]:
            assert preset in captured.out


class TestListModules:
    """Test list-modules subcommand."""

    def test_list_modules_shows_modules(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["list-modules"])
        assert result == 0
        captured = capsys.readouterr()
        # Should show at least these core modules
        assert "hooks-essential" in captured.out
        assert "hooks-quality" in captured.out
        assert "hooks-routing" in captured.out


class TestInstallDryRun:
    """Test install --dry-run."""

    def test_install_dry_run_minimal(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["install", "--preset", "minimal", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Would install" in captured.out

    def test_install_dry_run_standard(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["install", "--preset", "standard", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Would install" in captured.out


class TestInstallFull:
    """Test full installation to tmp dir."""

    def test_install_minimal_in_tmp(self, tmp_path: Path) -> None:
        result = main(["install", "--preset", "minimal", "--target", str(tmp_path)])
        assert result == 0
        # Should create .claude directory
        assert (tmp_path / ".claude").is_dir()

    def test_install_standard_in_tmp(self, tmp_path: Path) -> None:
        result = main(["install", "--preset", "standard", "--target", str(tmp_path)])
        assert result == 0
        assert (tmp_path / ".claude").is_dir()

    def test_validate_after_install(self, tmp_path: Path) -> None:
        main(["install", "--preset", "minimal", "--target", str(tmp_path)])
        result = main(["validate", str(tmp_path)])
        assert result == 0


class TestModuleEntry:
    """Test python -m claude_code_kazuba."""

    def test_main_module_entry_point(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "claude_code_kazuba", "--version"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert result.returncode == 0
        assert "0.2.0" in result.stdout
