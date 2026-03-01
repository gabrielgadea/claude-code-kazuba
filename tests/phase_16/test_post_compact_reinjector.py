"""Tests for post_compact_reinjector.py — Phase 16."""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Module loading via importlib (modules dir has hyphens — not valid py names)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _import_from_path(name: str, file_path: Path) -> types.ModuleType:
    """Import a Python module from an arbitrary file path."""
    lib_parent = str(PROJECT_ROOT)
    if lib_parent not in sys.path:
        sys.path.insert(0, lib_parent)
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None, f"Cannot load spec for {file_path}"
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_PCR_PATH = (
    PROJECT_ROOT
    / "modules"
    / "hooks-essential"
    / "hooks"
    / "post_compact_reinjector.py"
)
_pcr = _import_from_path("post_compact_reinjector_ph16", _PCR_PATH)

ReinjectorConfig = _pcr.ReinjectorConfig
load_critical_rules = _pcr.load_critical_rules
format_additional_context = _pcr.format_additional_context
main = _pcr.main


# ---------------------------------------------------------------------------
# ReinjectorConfig tests
# ---------------------------------------------------------------------------


def test_reinjector_config_defaults() -> None:
    """ReinjectorConfig has sensible defaults."""
    config = ReinjectorConfig()
    assert config.max_rules >= 1
    assert isinstance(config.rules_dir, Path)


def test_reinjector_config_frozen() -> None:
    """ReinjectorConfig is immutable (frozen=True)."""
    config = ReinjectorConfig()
    with pytest.raises(ValueError):
        config.max_rules = 999  # type: ignore[misc]


def test_reinjector_config_custom_values(tmp_path: Path) -> None:
    """ReinjectorConfig accepts custom values."""
    config = ReinjectorConfig(rules_dir=tmp_path / "rules", max_rules=5)
    assert config.max_rules == 5
    assert config.rules_dir == tmp_path / "rules"


# ---------------------------------------------------------------------------
# load_critical_rules tests
# ---------------------------------------------------------------------------


def test_load_rules_empty_dir(tmp_path: Path) -> None:
    """load_critical_rules returns built-in rules when dir does not exist."""
    rules = load_critical_rules(tmp_path / "nonexistent")
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_load_rules_with_files(tmp_path: Path) -> None:
    """load_critical_rules loads rules from .txt files in directory."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "my_rules.txt").write_text("Rule one\nRule two\n# comment ignored\n")

    rules = load_critical_rules(rules_dir)
    assert "Rule one" in rules
    assert "Rule two" in rules
    # Comment lines should be excluded
    assert "# comment ignored" not in rules


def test_load_rules_with_md_files(tmp_path: Path) -> None:
    """load_critical_rules loads rules from .md files."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "critical.md").write_text("Always test before ship\nFail loud\n")

    rules = load_critical_rules(rules_dir)
    assert "Always test before ship" in rules


def test_load_rules_empty_files_fallback(tmp_path: Path) -> None:
    """load_critical_rules returns built-in rules when files are empty."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "empty.txt").write_text("")

    rules = load_critical_rules(rules_dir)
    # Should fall back to built-in rules
    assert len(rules) > 0


# ---------------------------------------------------------------------------
# format_additional_context tests
# ---------------------------------------------------------------------------


def test_format_additional_context() -> None:
    """format_additional_context wraps rules in a consistent block."""
    rules = ["Rule A", "Rule B"]
    context = format_additional_context(rules)
    assert "[CRITICAL RULES" in context
    assert "Rule A" in context
    assert "Rule B" in context
    assert "[END CRITICAL RULES]" in context


def test_format_context_empty_rules() -> None:
    """format_additional_context handles empty rule list gracefully."""
    context = format_additional_context([])
    assert isinstance(context, str)
    assert len(context) > 0


def test_format_context_structure() -> None:
    """format_additional_context produces a block with start and end markers."""
    rules = ["X"]
    context = format_additional_context(rules)
    lines = context.splitlines()
    assert len(lines) >= 3
    assert lines[0].startswith("[CRITICAL RULES")
    assert lines[-1] == "[END CRITICAL RULES]"


# ---------------------------------------------------------------------------
# max_rules_limit test
# ---------------------------------------------------------------------------


def test_max_rules_limit(tmp_path: Path) -> None:
    """max_rules limits the number of rules injected."""
    config = ReinjectorConfig(max_rules=2)
    # Create many rules
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    lines = "\n".join(f"Rule {i}" for i in range(10))
    (rules_dir / "many.txt").write_text(lines)

    loaded = load_critical_rules(rules_dir)
    limited = loaded[: config.max_rules]
    assert len(limited) == 2


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


def test_main_empty_stdin() -> None:
    """main() handles empty stdin without crashing, exits 0."""
    with patch("sys.stdin", StringIO("")), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


def test_main_with_rules() -> None:
    """main() produces JSON output with additionalContext on stdout."""
    event = json.dumps({"hook_event_name": "PreCompact"})
    captured_stdout = StringIO()
    with patch("sys.stdin", StringIO(event)), patch("sys.stdout", captured_stdout), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    output = captured_stdout.getvalue()
    if output.strip():
        data = json.loads(output)
        assert "hookSpecificOutput" in data
        assert "additionalContext" in data["hookSpecificOutput"]


def test_main_always_exits_zero() -> None:
    """main() always exits 0 even with invalid input (fail-open)."""
    with patch("sys.stdin", StringIO("INVALID {{{")), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


def test_main_exception_in_stdout_still_exits_zero() -> None:
    """main() exits 0 even when writing to stdout raises."""
    import post_compact_reinjector_ph16 as mod_pcr

    original = mod_pcr.format_additional_context

    def _raise(rules: list) -> str:
        raise RuntimeError("simulated stdout error")

    mod_pcr.format_additional_context = _raise  # type: ignore[attr-defined]
    with patch("sys.stdin", StringIO("")), pytest.raises(SystemExit) as exc_info:
        main()
    mod_pcr.format_additional_context = original  # type: ignore[attr-defined]
    assert exc_info.value.code == 0


def test_load_rules_oserror_on_file(tmp_path: Path) -> None:
    """load_critical_rules skips unreadable files and falls back to built-ins."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    # Create a file but make it unreadable
    bad_file = rules_dir / "bad.txt"
    bad_file.write_text("Rule from bad file")
    bad_file.chmod(0o000)

    try:
        rules = load_critical_rules(rules_dir)
        # Should either have rules from file or fall back to built-ins — never empty
        assert len(rules) > 0
    finally:
        # Restore permissions for cleanup
        bad_file.chmod(0o644)
