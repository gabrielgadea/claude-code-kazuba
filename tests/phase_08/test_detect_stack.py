"""Tests for scripts.detect_stack — project stack auto-detection."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from scripts.detect_stack import detect_stack

if TYPE_CHECKING:
    from pathlib import Path


class TestDetectLanguage:
    """Language detection from manifest files."""

    def test_python_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.12"\n')
        result = detect_stack(tmp_path)
        assert result["language"] == "python"
        assert result["version"] == ">=3.12"

    def test_python_setup_py(self, tmp_path: Path) -> None:
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()\n")
        result = detect_stack(tmp_path)
        assert result["language"] == "python"

    def test_python_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask>=2.0\n")
        result = detect_stack(tmp_path)
        assert result["language"] == "python"

    def test_rust_cargo(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text('[package]\nedition = "2021"\n')
        result = detect_stack(tmp_path)
        assert result["language"] == "rust"
        assert result["version"] == "edition-2021"

    def test_javascript_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"name": "test"}))
        result = detect_stack(tmp_path)
        assert result["language"] == "javascript"

    def test_typescript_detection(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"name": "test"}))
        (tmp_path / "tsconfig.json").write_text("{}")
        result = detect_stack(tmp_path)
        assert result["language"] == "typescript"

    def test_go_mod(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/m\n\ngo 1.21\n")
        result = detect_stack(tmp_path)
        assert result["language"] == "go"
        assert result["version"] == "1.21"

    def test_java_maven(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project></project>")
        result = detect_stack(tmp_path)
        assert result["language"] == "java"
        assert result["framework"] == "maven"

    def test_java_gradle(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'\n")
        result = detect_stack(tmp_path)
        assert result["language"] == "java"
        assert result["framework"] == "gradle"

    def test_unknown_project(self, tmp_path: Path) -> None:
        result = detect_stack(tmp_path)
        assert result["language"] == "unknown"

    def test_priority_pyproject_over_requirements(self, tmp_path: Path) -> None:
        """pyproject.toml should be detected before requirements.txt."""
        (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.11"\n')
        (tmp_path / "requirements.txt").write_text("flask\n")
        result = detect_stack(tmp_path)
        assert result["language"] == "python"
        assert result["version"] == ">=3.11"


class TestDetectFramework:
    """Framework detection within a language."""

    def test_python_django(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["django>=4.0"]\n'
        )
        result = detect_stack(tmp_path)
        assert result.get("framework") == "django"

    def test_python_flask(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["flask>=2.0"]\n'
        )
        result = detect_stack(tmp_path)
        assert result.get("framework") == "flask"

    def test_python_fastapi(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi>=0.100"]\n'
        )
        result = detect_stack(tmp_path)
        assert result.get("framework") == "fastapi"

    def test_js_react(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"react": "^18.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = detect_stack(tmp_path)
        assert result.get("framework") == "react"

    def test_js_next(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"next": "^14.0", "react": "^18.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = detect_stack(tmp_path)
        assert result.get("framework") == "next"

    def test_js_vue(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"vue": "^3.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = detect_stack(tmp_path)
        assert result.get("framework") == "vue"

    def test_js_node_version(self, tmp_path: Path) -> None:
        pkg = {"engines": {"node": ">=18"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = detect_stack(tmp_path)
        assert result.get("version") == ">=18"

    def test_no_framework(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
        result = detect_stack(tmp_path)
        assert "framework" not in result
