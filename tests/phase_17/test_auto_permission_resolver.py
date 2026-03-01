"""Tests for auto_permission_resolver — Phase 17."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------


def _import_from_path(name: str, file_path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


_APR_PATH = (
    PROJECT_ROOT
    / "claude_code_kazuba/data/modules"
    / "hooks-routing"
    / "hooks"
    / "auto_permission_resolver.py"
)
_apr = _import_from_path("auto_permission_resolver_ph17", _APR_PATH)

# Aliases
PermissionConfig = _apr.PermissionConfig
HookInput = _apr.HookInput
PermissionResult = _apr.PermissionResult
resolve_permission = _apr.resolve_permission
is_safe_read = _apr.is_safe_read
is_safe_write = _apr.is_safe_write
is_safe_bash = _apr.is_safe_bash
ALLOW = _apr.ALLOW
BLOCK = _apr.BLOCK
DENY = _apr.DENY


# ---------------------------------------------------------------------------
# PermissionConfig tests
# ---------------------------------------------------------------------------


class TestPermissionConfig:
    """Tests for the immutable config dataclass."""

    def test_default_enabled(self) -> None:
        """Config is enabled by default."""
        cfg = PermissionConfig()
        assert cfg.enabled is True

    def test_frozen(self) -> None:
        """PermissionConfig is frozen (immutable)."""
        cfg = PermissionConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.enabled = False  # type: ignore[misc]

    def test_safe_write_paths_non_empty(self) -> None:
        """Default config has non-empty safe_write_paths."""
        cfg = PermissionConfig()
        assert len(cfg.safe_write_paths) > 0

    def test_dangerous_bash_patterns_non_empty(self) -> None:
        """Default config has non-empty dangerous_bash_patterns."""
        cfg = PermissionConfig()
        assert len(cfg.dangerous_bash_patterns) > 0


# ---------------------------------------------------------------------------
# is_safe_read tests
# ---------------------------------------------------------------------------


class TestIsSafeRead:
    """Tests for is_safe_read predicate."""

    def test_python_file_is_safe(self) -> None:
        """Python files are safe to read."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": "/project/src/app.py"}, cfg) is True

    def test_json_file_is_safe(self) -> None:
        """JSON files are safe to read."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": "/project/config.json"}, cfg) is True

    def test_env_file_is_dangerous(self) -> None:
        """Files containing '.env' are not safe to read."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": "/project/.env"}, cfg) is False

    def test_ssh_key_is_dangerous(self) -> None:
        """SSH private key paths are not safe to read."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": "/home/user/.ssh/id_rsa"}, cfg) is False

    def test_empty_path_not_safe(self) -> None:
        """Empty file_path returns False (not safe)."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": ""}, cfg) is False

    def test_missing_key_not_safe(self) -> None:
        """Missing 'file_path' key returns False."""
        cfg = PermissionConfig()
        assert is_safe_read({}, cfg) is False


# ---------------------------------------------------------------------------
# is_safe_write tests
# ---------------------------------------------------------------------------


class TestIsSafeWrite:
    """Tests for is_safe_write predicate."""

    def test_tests_dir_is_safe(self) -> None:
        """Writing to tests/ is safe."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/project/tests/test_foo.py"}, cfg) is True

    def test_claude_dir_is_safe(self) -> None:
        """Writing to .claude/ is safe."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/project/.claude/hooks/x.py"}, cfg) is True

    def test_env_file_unsafe(self) -> None:
        """Writing to .env is never safe."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/project/.env"}, cfg) is False

    def test_etc_dir_unsafe(self) -> None:
        """Writing to /etc/ is not safe."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/etc/passwd"}, cfg) is False

    def test_arbitrary_path_not_auto_approved(self) -> None:
        """Path not in safe_write_paths is not auto-approved."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/random/path/file.py"}, cfg) is False

    def test_empty_path(self) -> None:
        """Empty path returns False."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": ""}, cfg) is False


# ---------------------------------------------------------------------------
# is_safe_bash tests
# ---------------------------------------------------------------------------


class TestIsSafeBash:
    """Tests for is_safe_bash predicate."""

    def test_pytest_command_is_safe(self) -> None:
        """pytest is a safe command."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "pytest tests/ -q"}, cfg) is True

    def test_ruff_command_is_safe(self) -> None:
        """ruff is a safe command."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "ruff check ."}, cfg) is True

    def test_rm_rf_root_is_dangerous(self) -> None:
        """rm -rf / is detected as dangerous."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "rm -rf /"}, cfg) is False

    def test_sudo_rm_is_dangerous(self) -> None:
        """sudo rm is detected as dangerous."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "sudo rm -rf /tmp/x"}, cfg) is False

    def test_empty_command_not_safe(self) -> None:
        """Empty command returns False."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": ""}, cfg) is False

    def test_unknown_command_not_auto_approved(self) -> None:
        """Unknown command is not considered safe."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "unknowntool --do-stuff"}, cfg) is False


# ---------------------------------------------------------------------------
# resolve_permission tests
# ---------------------------------------------------------------------------


class TestResolvePermission:
    """Tests for the main resolve_permission decision logic."""

    def _make_input(self, tool_name: str, tool_input: dict) -> HookInput:
        return HookInput.from_dict(
            {"tool_name": tool_name, "tool_input": tool_input, "session_id": "test"}
        )

    def test_read_safe_file_allowed(self) -> None:
        """Safe read is auto-approved (ALLOW)."""
        cfg = PermissionConfig()
        hi = self._make_input("Read", {"file_path": "/project/app.py"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW

    def test_write_dangerous_path_denied(self) -> None:
        """Write to .env returns DENY."""
        cfg = PermissionConfig()
        hi = self._make_input("Write", {"file_path": "/project/.env"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == DENY

    def test_write_safe_path_allowed(self) -> None:
        """Write to tests/ is auto-approved."""
        cfg = PermissionConfig()
        hi = self._make_input("Write", {"file_path": "/project/tests/test.py"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW

    def test_bash_dangerous_pattern_blocked(self) -> None:
        """Dangerous bash command returns BLOCK."""
        cfg = PermissionConfig()
        hi = self._make_input("Bash", {"command": "rm -rf /"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == BLOCK

    def test_bash_safe_command_allowed(self) -> None:
        """Safe bash command (pytest) is auto-approved."""
        cfg = PermissionConfig()
        hi = self._make_input("Bash", {"command": "pytest tests/ -q"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW

    def test_task_always_allowed(self) -> None:
        """Task tool is always allowed."""
        cfg = PermissionConfig()
        hi = self._make_input("Task", {"prompt": "do something"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW
        assert r.auto_approved is True

    def test_unknown_tool_default_allow(self) -> None:
        """Unknown tool returns ALLOW by default."""
        cfg = PermissionConfig()
        hi = self._make_input("UnknownTool", {})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW

    def test_permission_result_frozen(self) -> None:
        """PermissionResult is immutable (frozen=True)."""
        r = PermissionResult(ALLOW, reason="test")
        with pytest.raises((AttributeError, TypeError)):
            r.exit_code = BLOCK  # type: ignore[misc]

    def test_hook_input_from_dict(self) -> None:
        """HookInput.from_dict parses fields correctly."""
        data = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/x.py"},
            "session_id": "abc123",
        }
        hi = HookInput.from_dict(data)
        assert hi.tool_name == "Write"
        assert hi.session_id == "abc123"

    def test_edit_dangerous_path_denied(self) -> None:
        """Edit to .ssh/ path returns DENY."""
        cfg = PermissionConfig()
        hi = self._make_input("Edit", {"file_path": "/home/user/.ssh/config"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == DENY

    def test_multiedit_safe_path_allowed(self) -> None:
        """MultiEdit to tests/ is allowed."""
        cfg = PermissionConfig()
        hi = self._make_input("MultiEdit", {"file_path": "/project/tests/helper.py"})
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


class TestIsReadExtensionEdgeCases:
    """Additional edge cases for is_safe_read."""

    def test_file_no_extension_is_safe(self) -> None:
        """Files without an extension (Makefile, Dockerfile) are safe to read."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": "/project/Makefile"}, cfg) is True

    def test_pem_extension_not_safe(self) -> None:
        """PEM key files are NOT safe to read."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": "/project/server.pem"}, cfg) is False

    def test_yaml_extension_is_safe(self) -> None:
        """YAML files are safe to read."""
        cfg = PermissionConfig()
        assert is_safe_read({"file_path": "/project/config.yaml"}, cfg) is True


class TestIsWriteEdgeCases:
    """Additional edge cases for is_safe_write."""

    def test_lib_dir_is_safe(self) -> None:
        """Writing to lib/ is safe."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/project/lib/helper.py"}, cfg) is True

    def test_modules_dir_is_safe(self) -> None:
        """Writing to modules/ is safe."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/project/modules/foo/bar.py"}, cfg) is True

    def test_credentials_path_unsafe(self) -> None:
        """Writing to path containing 'credentials' is not safe."""
        cfg = PermissionConfig()
        assert is_safe_write({"file_path": "/project/credentials.json"}, cfg) is False


class TestIsBashEdgeCases:
    """Additional edge cases for is_safe_bash."""

    def test_python3_is_safe(self) -> None:
        """python3 is a safe command."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "python3 script.py"}, cfg) is True

    def test_uv_is_safe(self) -> None:
        """uv (Python package manager) is safe."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "uv pip install pytest"}, cfg) is True

    def test_chmod_777_is_dangerous(self) -> None:
        """chmod 777 is dangerous."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "chmod 777 /tmp/file"}, cfg) is False

    def test_whitespace_only_command(self) -> None:
        """Command with only whitespace is not safe."""
        cfg = PermissionConfig()
        assert is_safe_bash({"command": "   "}, cfg) is False


class TestLoadConfig:
    """Tests for load_config."""

    def test_load_config_default_returns_permission_config(self) -> None:
        """load_config returns PermissionConfig even if file missing."""
        cfg = _apr.load_config(None)
        assert isinstance(cfg, PermissionConfig)
        assert cfg.enabled is True

    def test_load_config_with_nonexistent_path(self, tmp_path: Path) -> None:
        """load_config with a nonexistent path returns default config."""
        cfg = _apr.load_config(tmp_path / "nonexistent.json")
        assert isinstance(cfg, PermissionConfig)

    def test_load_config_with_existing_file(self, tmp_path: Path) -> None:
        """load_config with an existing file returns PermissionConfig."""
        config_file = tmp_path / "hooks.json"
        config_file.write_text("{}")
        cfg = _apr.load_config(config_file)
        assert isinstance(cfg, PermissionConfig)


class TestResolvePermissionReadNotAutoApproved:
    """Test Read when auto_approve_safe_reads is disabled."""

    def test_read_disabled_auto_approve(self) -> None:
        """When auto_approve_safe_reads=False, read returns ALLOW with review reason."""
        cfg = PermissionConfig(auto_approve_safe_reads=False)
        hi = HookInput.from_dict(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/project/app.py"},
                "session_id": "x",
            }
        )
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW
        assert r.auto_approved is False

    def test_write_disabled_auto_approve(self) -> None:
        """When auto_approve_safe_writes=False, safe write path still returns ALLOW."""
        cfg = PermissionConfig(auto_approve_safe_writes=False)
        hi = HookInput.from_dict(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/project/tests/test.py"},
                "session_id": "x",
            }
        )
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW

    def test_bash_disabled_auto_approve(self) -> None:
        """When auto_approve_safe_bash=False, safe command returns ALLOW with review."""
        cfg = PermissionConfig(auto_approve_safe_bash=False)
        hi = HookInput.from_dict(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "pytest tests/"},
                "session_id": "x",
            }
        )
        r = resolve_permission(hi, cfg)
        assert r.exit_code == ALLOW
        assert r.auto_approved is False


class TestPermissionResultEmit:
    """Tests for PermissionResult.emit() and message output."""

    def test_emit_with_message_prints_to_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """emit() with message prints to stderr."""
        r = PermissionResult(ALLOW, message="test warning", reason="r")
        with pytest.raises(SystemExit) as exc_info:
            r.emit()
        assert exc_info.value.code == ALLOW
        captured = capsys.readouterr()
        assert "test warning" in captured.err

    def test_emit_writes_json_to_stdout(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """emit() always writes JSON to stdout."""
        import json as _json

        # Capture sys.stdout writes via monkeypatching json.dump
        written: list[dict] = []
        original_dump = _json.dump

        def _cap(obj: object, fp: object, **kw: object) -> None:
            written.append(obj)  # type: ignore[arg-type]
            original_dump(obj, fp, **kw)

        monkeypatch.setattr("json.dump", _cap)
        r = PermissionResult(BLOCK, reason="dangerous", auto_approved=False)
        with pytest.raises(SystemExit):
            r.emit()
        assert any(d.get("reason") == "dangerous" for d in written)


class TestHookInputFromStdin:
    """Tests for HookInput.from_stdin()."""

    def test_from_stdin_parses_correctly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_stdin() parses valid JSON from stdin."""
        import io

        data = '{"tool_name": "Write", "tool_input": {"file_path": "/x.py"}, "session_id": "s1"}'
        monkeypatch.setattr("sys.stdin", io.StringIO(data))
        hi = HookInput.from_stdin()
        assert hi.tool_name == "Write"
        assert hi.session_id == "s1"


class TestMainFunctionErrors:
    """Tests for main() exception handling (fail-open)."""

    def test_main_invalid_json_fail_open(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() exits 0 on JSON decode error (fail-open)."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("not valid json {"))
        with pytest.raises(SystemExit) as exc_info:
            _apr.main()
        assert exc_info.value.code == ALLOW

    def test_main_unexpected_exception_fail_open(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() exits 0 on unexpected exception (fail-open)."""
        import io

        def _bad_load_config(_path=None):  # type: ignore[override]
            raise RuntimeError("unexpected")

        monkeypatch.setattr(_apr, "load_config", _bad_load_config)
        monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
        with pytest.raises(SystemExit) as exc_info:
            _apr.main()
        assert exc_info.value.code == ALLOW
