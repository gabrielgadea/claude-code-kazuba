"""Install a single module to target directory."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from scripts.merge_settings import merge_settings

# Directories within a module that get copied to .claude/
_CONTENT_DIRS = ("hooks", "skills", "agents", "commands", "contexts", "config", "templates", "src")

# Template file extensions
_TEMPLATE_EXT = ".template"


def _copy_directory(src: Path, dest: Path, copied: list[str]) -> None:
    """Recursively copy a directory, tracking copied files."""
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.rglob("*")):
        if item.is_file() and "__pycache__" not in str(item) and item.suffix != ".pyc":
            rel = item.relative_to(src)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            copied.append(str(target))


def _render_template(template_path: Path, output_path: Path, variables: dict[str, Any]) -> None:
    """Render a Jinja2 template file to output path."""
    # Import here to avoid hard dependency at module level
    from lib.template_engine import render_string

    template_text = template_path.read_text(encoding="utf-8")
    rendered = render_string(template_text, variables)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def _merge_hooks_settings(
    settings_path: Path,
    hooks_json_path: Path,
    merged: list[str],
) -> None:
    """Merge a module's settings.hooks.json into target settings.json."""
    overlay = json.loads(hooks_json_path.read_text(encoding="utf-8"))

    if settings_path.exists():
        base = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        base = {
            "$schema": "https://json.schemastore.org/claude-code-settings.json",
            "permissions": {"allow": [], "deny": []},
            "hooks": {},
            "env": {},
        }

    result = merge_settings(base, overlay)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    merged.append(str(hooks_json_path))


def install_module(
    module_name: str,
    source_dir: Path,
    target_dir: Path,
    variables: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Install a single module to target directory.

    Copies hooks, skills, agents, commands, contexts, config, templates
    to appropriate locations in .claude/.
    Merges settings.hooks.json into target settings.json.
    Renders template files with detected stack variables.

    Args:
        module_name: Name of the module to install.
        source_dir: Path to the project root (contains core/ and modules/).
        target_dir: Path to the target project root (will create .claude/).
        variables: Template variables for rendering (stack, language, etc.).

    Returns:
        Dict with keys "copied", "merged", "rendered" — lists of file paths.

    Raises:
        FileNotFoundError: If module directory doesn't exist.
    """
    if variables is None:
        variables = {}

    result: dict[str, list[str]] = {
        "copied": [],
        "merged": [],
        "rendered": [],
    }

    # Determine module source path
    if module_name == "core":
        module_path = source_dir / "core"
    else:
        module_path = source_dir / "modules" / module_name

    if not module_path.exists():
        msg = f"Module directory not found: {module_path}"
        raise FileNotFoundError(msg)

    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Copy content directories
    for content_dir_name in _CONTENT_DIRS:
        content_src = module_path / content_dir_name
        if content_src.is_dir():
            content_dest = claude_dir / content_dir_name
            _copy_directory(content_src, content_dest, result["copied"])

    # Copy rules (core module special case)
    rules_src = module_path / "rules"
    if rules_src.is_dir():
        rules_dest = claude_dir / "rules"
        _copy_directory(rules_src, rules_dest, result["copied"])

    # Process template files
    for template_file in sorted(module_path.glob(f"*{_TEMPLATE_EXT}")):
        output_name = template_file.name.removesuffix(_TEMPLATE_EXT)
        output_path = claude_dir / output_name
        _render_template(template_file, output_path, variables)
        result["rendered"].append(str(output_path))

    # Merge settings.hooks.json if present
    hooks_json = module_path / "settings.hooks.json"
    if hooks_json.exists():
        settings_path = claude_dir / "settings.json"
        _merge_hooks_settings(settings_path, hooks_json, result["merged"])

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: install_module.py MODULE_NAME SOURCE_DIR TARGET_DIR [KEY=VALUE ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    mod_name = sys.argv[1]
    src = Path(sys.argv[2])
    tgt = Path(sys.argv[3])

    # Parse key=value variables
    vars_dict: dict[str, Any] = {}
    for arg in sys.argv[4:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            vars_dict[k] = v

    try:
        output = install_module(mod_name, src, tgt, vars_dict)
        print(json.dumps(output, indent=2))
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
