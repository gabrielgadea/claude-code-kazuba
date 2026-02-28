"""Tests for scripts.resolve_deps — module dependency resolution."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.resolve_deps import (
    _parse_yaml_frontmatter,
    resolve_dependencies,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestParseYamlFrontmatter:
    """YAML frontmatter parser for MODULE.md files."""

    def test_basic_frontmatter(self) -> None:
        text = "---\nname: core\nversion: \"1.0.0\"\ndependencies: []\n---\n# Core\n"
        result = _parse_yaml_frontmatter(text)
        assert result["name"] == "core"
        assert result["version"] == "1.0.0"
        assert result["dependencies"] == []

    def test_multiline_dependencies(self) -> None:
        text = "---\nname: hooks\ndependencies:\n  - core\n  - utils\n---\n"
        result = _parse_yaml_frontmatter(text)
        assert result["dependencies"] == ["core", "utils"]

    def test_no_frontmatter(self) -> None:
        text = "# No frontmatter here\n"
        result = _parse_yaml_frontmatter(text)
        assert result == {}

    def test_empty_dependencies(self) -> None:
        text = "---\nname: test\ndependencies: []\n---\n"
        result = _parse_yaml_frontmatter(text)
        assert result["dependencies"] == []

    def test_inline_dependencies(self) -> None:
        text = '---\nname: test\ndependencies: [core, "utils"]\n---\n'
        result = _parse_yaml_frontmatter(text)
        assert "core" in result["dependencies"]
        assert "utils" in result["dependencies"]


class TestResolveDependencies:
    """Dependency resolution with topological sort."""

    def _make_module(self, tmp_path: Path, name: str, deps: list[str]) -> None:
        """Create a minimal MODULE.md in the right location."""
        module_dir = tmp_path / "core" if name == "core" else tmp_path / "modules" / name

        module_dir.mkdir(parents=True, exist_ok=True)
        dep_str = ", ".join(deps) if deps else ""
        if deps:
            dep_lines = "\n".join(f"  - {d}" for d in deps)
            frontmatter = f"---\nname: {name}\ndependencies:\n{dep_lines}\n---\n"
        else:
            frontmatter = f"---\nname: {name}\ndependencies: [{dep_str}]\n---\n"
        (module_dir / "MODULE.md").write_text(frontmatter)

    def test_single_module_no_deps(self, tmp_path: Path) -> None:
        self._make_module(tmp_path, "core", [])
        result = resolve_dependencies(["core"], tmp_path / "modules", core_dir=tmp_path / "core")
        assert result == ["core"]

    def test_simple_chain(self, tmp_path: Path) -> None:
        self._make_module(tmp_path, "core", [])
        self._make_module(tmp_path, "hooks", ["core"])
        result = resolve_dependencies(
            ["hooks"], tmp_path / "modules", core_dir=tmp_path / "core"
        )
        assert result.index("core") < result.index("hooks")

    def test_multiple_modules(self, tmp_path: Path) -> None:
        self._make_module(tmp_path, "core", [])
        self._make_module(tmp_path, "hooks-essential", ["core"])
        self._make_module(tmp_path, "hooks-quality", ["core"])
        result = resolve_dependencies(
            ["hooks-essential", "hooks-quality"],
            tmp_path / "modules",
            core_dir=tmp_path / "core",
        )
        assert result[0] == "core"
        assert "hooks-essential" in result
        assert "hooks-quality" in result

    def test_transitive_dependencies(self, tmp_path: Path) -> None:
        self._make_module(tmp_path, "core", [])
        self._make_module(tmp_path, "base", ["core"])
        self._make_module(tmp_path, "advanced", ["base"])
        result = resolve_dependencies(
            ["advanced"], tmp_path / "modules", core_dir=tmp_path / "core"
        )
        assert result == ["core", "base", "advanced"]

    def test_circular_dependency_raises(self, tmp_path: Path) -> None:
        self._make_module(tmp_path, "a", ["b"])
        self._make_module(tmp_path, "b", ["a"])
        with pytest.raises(ValueError, match="Circular"):
            resolve_dependencies(["a"], tmp_path / "modules", core_dir=tmp_path / "core")

    def test_missing_module_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            resolve_dependencies(
                ["nonexistent"], tmp_path / "modules", core_dir=tmp_path / "core"
            )

    def test_deduplication(self, tmp_path: Path) -> None:
        self._make_module(tmp_path, "core", [])
        self._make_module(tmp_path, "a", ["core"])
        self._make_module(tmp_path, "b", ["core"])
        result = resolve_dependencies(
            ["a", "b"], tmp_path / "modules", core_dir=tmp_path / "core"
        )
        # core should appear only once
        assert result.count("core") == 1

    def test_default_core_dir(self, tmp_path: Path) -> None:
        """When core_dir is not specified, it defaults to modules_dir parent / core."""
        self._make_module(tmp_path, "core", [])
        result = resolve_dependencies(["core"], tmp_path / "modules")
        assert result == ["core"]

    def test_real_modules(self, base_dir: Path) -> None:
        """Test with actual project modules."""
        modules_dir = base_dir / "modules"
        core_dir = base_dir / "core"
        result = resolve_dependencies(
            ["hooks-essential"], modules_dir, core_dir=core_dir
        )
        assert "core" in result
        assert "hooks-essential" in result
        assert result.index("core") < result.index("hooks-essential")
