"""Tests for lib.template_engine — Jinja2 template rendering."""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from claude_code_kazuba.template_engine import TemplateEngine, render_string


class TestRenderString:
    """render_string renders Jinja2 from string."""

    def test_simple_substitution(self) -> None:
        result = render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_missing_variable_is_empty(self) -> None:
        result = render_string("Hello {{ name }}!", {})
        assert result == "Hello !"


class TestTemplateEngine:
    """TemplateEngine renders from template files."""

    @pytest.fixture
    def engine(self, tmp_path: Path) -> TemplateEngine:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "greeting.j2").write_text("Hello {{ name }}!")
        (tpl_dir / "module.j2").write_text("# {{ title | upper_first }}\nSlug: {{ title | slug }}")
        (tpl_dir / "block.j2").write_text("Code:\n{{ code | indent_block(4) }}")
        return TemplateEngine(tpl_dir)

    def test_render_file(self, engine: TemplateEngine) -> None:
        result = engine.render("greeting.j2", {"name": "Claude"})
        assert result == "Hello Claude!"

    def test_slug_filter(self, engine: TemplateEngine) -> None:
        result = engine.render("module.j2", {"title": "My Cool Module"})
        assert "my-cool-module" in result

    def test_upper_first_filter(self, engine: TemplateEngine) -> None:
        result = engine.render("module.j2", {"title": "hello world"})
        assert "Hello world" in result

    def test_indent_block_filter(self, engine: TemplateEngine) -> None:
        result = engine.render("block.j2", {"code": "line1\nline2"})
        assert "    line1" in result
        assert "    line2" in result

    def test_missing_template_raises(self, engine: TemplateEngine) -> None:
        with pytest.raises((FileNotFoundError, jinja2.TemplateNotFound)):
            engine.render("nonexistent.j2", {})
