"""Detect project stack by checking for manifest files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Map of manifest files to language/framework detection
_MANIFEST_MAP: list[tuple[str, str, str | None]] = [
    ("pyproject.toml", "python", None),
    ("setup.py", "python", None),
    ("requirements.txt", "python", None),
    ("Cargo.toml", "rust", None),
    ("package.json", "javascript", None),
    ("go.mod", "go", None),
    ("pom.xml", "java", "maven"),
    ("build.gradle", "java", "gradle"),
    ("build.gradle.kts", "java", "gradle"),
]


def _detect_python_version(target_dir: Path) -> str | None:
    """Try to extract Python version from pyproject.toml."""
    pyproject = target_dir / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        text = pyproject.read_text(encoding="utf-8")
        # Match requires-python = ">=3.12"
        match = re.search(r'requires-python\s*=\s*"([^"]+)"', text)
        if match:
            return match.group(1)
    except OSError:
        pass
    return None


def _detect_python_framework(target_dir: Path) -> str | None:
    """Detect Python framework from pyproject.toml dependencies."""
    pyproject = target_dir / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        text = pyproject.read_text(encoding="utf-8").lower()
        if "django" in text:
            return "django"
        if "flask" in text:
            return "flask"
        if "fastapi" in text:
            return "fastapi"
    except OSError:
        pass
    return None


def _detect_js_typescript(target_dir: Path) -> bool:
    """Check if a JS project uses TypeScript."""
    return (target_dir / "tsconfig.json").exists()


def _detect_js_framework(target_dir: Path) -> str | None:
    """Detect JS/TS framework from package.json."""
    pkg = target_dir / "package.json"
    if not pkg.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(pkg.read_text(encoding="utf-8"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "next" in deps:
            return "next"
        if "react" in deps:
            return "react"
        if "vue" in deps:
            return "vue"
        if "svelte" in deps:
            return "svelte"
        if "@angular/core" in deps:
            return "angular"
        if "express" in deps:
            return "express"
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _detect_node_version(target_dir: Path) -> str | None:
    """Try to extract Node version from package.json engines field."""
    pkg = target_dir / "package.json"
    if not pkg.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(pkg.read_text(encoding="utf-8"))
        engines = data.get("engines", {})
        return engines.get("node")
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _detect_go_version(target_dir: Path) -> str | None:
    """Try to extract Go version from go.mod."""
    gomod = target_dir / "go.mod"
    if not gomod.exists():
        return None
    try:
        text = gomod.read_text(encoding="utf-8")
        match = re.search(r"^go\s+(\d+\.\d+(?:\.\d+)?)", text, re.MULTILINE)
        if match:
            return match.group(1)
    except OSError:
        pass
    return None


def _detect_rust_version(target_dir: Path) -> str | None:
    """Try to extract Rust edition from Cargo.toml."""
    cargo = target_dir / "Cargo.toml"
    if not cargo.exists():
        return None
    try:
        text = cargo.read_text(encoding="utf-8")
        match = re.search(r'edition\s*=\s*"(\d{4})"', text)
        if match:
            return f"edition-{match.group(1)}"
    except OSError:
        pass
    return None


def detect_stack(target_dir: Path) -> dict[str, str]:
    """Detect project type by checking for manifest files.

    Args:
        target_dir: Path to the project root directory.

    Returns:
        Dict with keys: language, and optionally version, framework.
        Returns {"language": "unknown"} if no manifest is found.
    """
    target = Path(target_dir)
    result: dict[str, str] = {"language": "unknown"}

    for manifest_file, language, framework in _MANIFEST_MAP:
        if (target / manifest_file).exists():
            result["language"] = language
            if framework:
                result["framework"] = framework
            break

    lang = result["language"]

    if lang == "python":
        version = _detect_python_version(target)
        if version:
            result["version"] = version
        fw = _detect_python_framework(target)
        if fw:
            result["framework"] = fw

    elif lang == "javascript":
        if _detect_js_typescript(target):
            result["language"] = "typescript"
        version = _detect_node_version(target)
        if version:
            result["version"] = version
        fw = _detect_js_framework(target)
        if fw:
            result["framework"] = fw

    elif lang == "go":
        version = _detect_go_version(target)
        if version:
            result["version"] = version

    elif lang == "rust":
        version = _detect_rust_version(target)
        if version:
            result["version"] = version

    return result


if __name__ == "__main__":
    import sys

    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    info = detect_stack(directory)
    for key, value in sorted(info.items()):
        print(f"{key}={value}")
