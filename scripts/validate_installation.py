"""Post-install health check for a kazuba installation."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _check_settings_json(claude_dir: Path) -> tuple[bool, str]:
    """Verify settings.json is valid JSON with $schema."""
    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        return False, "settings.json not found"

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"settings.json is not valid JSON: {e}"

    if not isinstance(data, dict):
        return False, "settings.json root is not a JSON object"

    if "$schema" not in data:
        return False, "settings.json missing $schema field"

    return True, "settings.json valid"


def _check_hook_scripts(claude_dir: Path) -> tuple[bool, str]:
    """Verify all hook scripts exist.

    For Python hooks, check the file exists.
    For shell hooks, check the file exists (executable check not needed on install).
    """
    hooks_dir = claude_dir / "hooks"
    if not hooks_dir.exists():
        return True, "no hooks directory (OK if no hook modules installed)"

    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        return True, "no settings.json to cross-check hooks"

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, "settings.json unreadable, skipping hook cross-check"

    hooks_config = data.get("hooks", {})
    missing: list[str] = []

    for _event, hook_list in hooks_config.items():
        if not isinstance(hook_list, list):
            continue
        for hook_entry in hook_list:
            if not isinstance(hook_entry, dict):
                continue
            command = hook_entry.get("command", "")
            # Extract script path from command like "python hooks/foo.py" or "bash hooks/bar.sh"
            parts = command.split()
            if len(parts) >= 2:
                script = parts[-1]
                script_path = claude_dir / script
                if not script_path.exists():
                    missing.append(script)

    if missing:
        return False, f"missing hook scripts: {', '.join(missing)}"

    return True, "all hook scripts present"


def _check_skill_files(claude_dir: Path) -> tuple[bool, str]:
    """Verify all SKILL.md files have valid YAML frontmatter."""
    skills_dir = claude_dir / "skills"
    if not skills_dir.exists():
        return True, "no skills directory"

    skill_files = list(skills_dir.rglob("SKILL.md"))
    if not skill_files:
        return True, "no SKILL.md files found"

    invalid: list[str] = []
    for skill_md in skill_files:
        text = skill_md.read_text(encoding="utf-8")
        # Check for YAML frontmatter (---\n...\n---)
        if not re.match(r"^---\s*\n.*?\n---", text, re.DOTALL):
            invalid.append(str(skill_md.relative_to(claude_dir)))

    if invalid:
        return False, f"SKILL.md files missing YAML frontmatter: {', '.join(invalid)}"

    return True, f"all {len(skill_files)} SKILL.md files valid"


def _check_claude_md(claude_dir: Path) -> tuple[bool, str]:
    """Verify CLAUDE.md was generated."""
    claude_md = claude_dir / "CLAUDE.md"
    if not claude_md.exists():
        return False, "CLAUDE.md not found"

    content = claude_md.read_text(encoding="utf-8")
    if len(content.strip()) < 50:
        return False, "CLAUDE.md appears empty or too short"

    return True, "CLAUDE.md present"


def _check_directory_structure(claude_dir: Path) -> tuple[bool, str]:
    """Verify .claude/ directory has expected structure."""
    if not claude_dir.exists():
        return False, ".claude/ directory not found"
    if not claude_dir.is_dir():
        return False, ".claude is not a directory"
    return True, ".claude/ directory exists"


def validate_installation(target_dir: Path) -> dict[str, bool]:
    """Run post-install health checks on a kazuba installation.

    Args:
        target_dir: Path to the target project root (containing .claude/).

    Returns:
        Dict mapping check name to pass/fail boolean.
        Also includes a "_messages" key with diagnostic messages (as list).
    """
    claude_dir = target_dir / ".claude"

    checks: list[tuple[str, tuple[bool, str]]] = [
        ("directory_structure", _check_directory_structure(claude_dir)),
        ("settings_json", _check_settings_json(claude_dir)),
        ("hook_scripts", _check_hook_scripts(claude_dir)),
        ("skill_files", _check_skill_files(claude_dir)),
        ("claude_md", _check_claude_md(claude_dir)),
    ]

    results: dict[str, bool] = {}
    messages: list[str] = []

    for name, (passed, message) in checks:
        results[name] = passed
        status = "PASS" if passed else "FAIL"
        messages.append(f"[{status}] {name}: {message}")

    results["all_passed"] = all(v for k, v in results.items() if k != "all_passed")
    results["_messages"] = messages  # type: ignore[assignment]

    return results


if __name__ == "__main__":
    import sys

    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    validation = validate_installation(directory)

    messages = validation.pop("_messages", [])
    for msg in messages:  # type: ignore[union-attr]
        print(msg)

    all_ok = validation.pop("all_passed", False)
    print()
    print(f"Overall: {'PASS' if all_ok else 'FAIL'}")
    sys.exit(0 if all_ok else 1)
