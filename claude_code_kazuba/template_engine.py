"""Template rendering engine using Jinja2."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Undefined


def _slug_filter(value: str) -> str:
    """Convert a title to kebab-case slug.

    Example: "My Cool Module" -> "my-cool-module"
    """
    text = value.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def _upper_first_filter(value: str) -> str:
    """Capitalize the first character of the string.

    Example: "hello world" -> "Hello world"
    """
    if not value:
        return value
    return value[0].upper() + value[1:]


def _indent_block_filter(value: str, width: int = 4) -> str:
    """Indent every line of a block of text.

    Args:
        value: Multi-line text to indent.
        width: Number of spaces for indentation.

    Example: "line1\\nline2" with width=4 -> "    line1\\n    line2"
    """
    indent = " " * width
    return "\n".join(indent + line for line in value.splitlines())


def _create_env(loader: Any = None) -> Environment:
    """Create a Jinja2 Environment with custom filters."""
    env = Environment(
        loader=loader,
        undefined=Undefined,
        keep_trailing_newline=True,
        autoescape=False,
    )
    env.filters["slug"] = _slug_filter
    env.filters["upper_first"] = _upper_first_filter
    env.filters["indent_block"] = _indent_block_filter
    return env


class TemplateEngine:
    """Template engine that renders Jinja2 templates from a directory.

    Args:
        templates_dir: Path to the directory containing template files.
    """

    def __init__(self, templates_dir: Path) -> None:
        self._templates_dir = templates_dir
        self._env = _create_env(loader=FileSystemLoader(str(templates_dir)))

    def render(self, template_name: str, variables: dict[str, Any]) -> str:
        """Render a template file with the given variables.

        Args:
            template_name: Name of the template file (relative to templates_dir).
            variables: Dictionary of template variables.

        Returns:
            Rendered template string.
        """
        template = self._env.get_template(template_name)
        return template.render(**variables)


def render_string(template_str: str, variables: dict[str, Any]) -> str:
    """Render a Jinja2 template from a string.

    Args:
        template_str: Jinja2 template as a string.
        variables: Dictionary of template variables.

    Returns:
        Rendered string.
    """
    env = _create_env()
    template = env.from_string(template_str)
    return template.render(**variables)
