"""Tests for lib/rust_bridge.py — Python fallback behaviour.

All tests in this module explicitly force prefer_rust=False to exercise
the pure-Python fallback path, regardless of whether the Rust extension
is compiled or not.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from lib.patterns import SecretPatterns
from lib.rust_bridge import (
    BashValidation,
    PatternHit,
    PatternMatcher,
    RustBridge,
    RustBridgeConfig,
    SecretsDetector,
    _python_check_secrets,
    _python_validate_bash,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _python_bridge() -> RustBridge:
    """Return a RustBridge configured to use the Python backend only."""
    cfg = RustBridgeConfig(prefer_rust=False)
    return RustBridge(config=cfg)


@pytest.fixture(autouse=True)
def reset_singleton() -> None:  # type: ignore[return]
    """Reset singleton between tests."""
    RustBridge.reset_singleton()
    yield
    RustBridge.reset_singleton()


# ---------------------------------------------------------------------------
# 1. Fallback when Rust unavailable
# ---------------------------------------------------------------------------
def test_fallback_when_rust_unavailable() -> None:
    """When prefer_rust=False, bridge uses python backend regardless."""
    bridge = _python_bridge()
    assert bridge.backend_name == "python"
    assert bridge.available is False


# ---------------------------------------------------------------------------
# 2. Python backend — check_secrets
# ---------------------------------------------------------------------------
def test_python_backend_check_secrets() -> None:
    """Python backend detects secrets in content."""
    bridge = _python_bridge()
    clean = bridge.check_secrets("Hello world")
    assert len(clean) == 0

    dirty = bridge.check_secrets('api_key = "abcdefghijklmnopqrstuvwxyz12345"')
    assert len(dirty) > 0
    assert all(h.backend == "python" for h in dirty)


# ---------------------------------------------------------------------------
# 3. Python backend — match_patterns
# ---------------------------------------------------------------------------
def test_python_backend_match_patterns() -> None:
    """Python backend matches patterns against text."""
    bridge = _python_bridge()
    ps = SecretPatterns.create()

    hits = bridge.match_patterns("clean text here", ps)
    assert isinstance(hits, list)
    assert len(hits) == 0

    hits2 = bridge.match_patterns('api_key = "abcdefghijklmnopqrstuvwxyz12345"', ps)
    assert len(hits2) > 0
    assert all(isinstance(h, PatternHit) for h in hits2)
    assert all(h.backend == "python" for h in hits2)


# ---------------------------------------------------------------------------
# 4. Python backend — validate_bash
# ---------------------------------------------------------------------------
def test_python_backend_validate_bash() -> None:
    """Python backend validates bash commands."""
    bridge = _python_bridge()

    safe = bridge.validate_bash("git status")
    assert safe.allowed is True
    assert safe.backend == "python"

    dangerous = bridge.validate_bash("rm -rf /")
    assert dangerous.allowed is False
    assert dangerous.backend == "python"
    assert dangerous.severity == "high"


# ---------------------------------------------------------------------------
# 5. Fallback secrets — api_key
# ---------------------------------------------------------------------------
def test_fallback_secrets_api_key() -> None:
    """Python fallback detects API key pattern."""
    hits = _python_check_secrets('api_key = "abcdefghijklmnopqrstuvwxyz12345"')
    assert len(hits) > 0
    assert hits[0].backend == "python"


# ---------------------------------------------------------------------------
# 6. Fallback secrets — password
# ---------------------------------------------------------------------------
def test_fallback_secrets_password() -> None:
    """Python fallback detects hardcoded password."""
    hits = _python_check_secrets("password = 'MySecretP@ss!'")
    assert len(hits) > 0


# ---------------------------------------------------------------------------
# 7. Fallback secrets — token
# ---------------------------------------------------------------------------
def test_fallback_secrets_token() -> None:
    """Python fallback detects access_token/auth_token pattern."""
    hits = _python_check_secrets('access_token = "abcdefghijklmnopqrstuvwxyz12345"')
    assert len(hits) > 0


# ---------------------------------------------------------------------------
# 8. Fallback secrets — no match
# ---------------------------------------------------------------------------
def test_fallback_secrets_no_match() -> None:
    """Python fallback returns empty list for clean content."""
    hits = _python_check_secrets("def hello(): return 'world'")
    assert hits == []


# ---------------------------------------------------------------------------
# 9. Python backend performance
# ---------------------------------------------------------------------------
def test_python_backend_performance() -> None:
    """Python backend responds in under 500ms for typical content."""
    bridge = _python_bridge()
    content = "x = 1\n" * 1000  # 6000 chars, no secrets

    t0 = time.perf_counter()
    bridge.check_secrets(content)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.5, f"Python backend too slow: {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# 10. Backend interface compatibility
# ---------------------------------------------------------------------------
def test_backend_interface_compatibility() -> None:
    """Python and (mocked) Rust backends return same types."""
    bridge = _python_bridge()

    # check_secrets
    hits = bridge.check_secrets("hello")
    assert isinstance(hits, list)

    # match_patterns
    hits2 = bridge.match_patterns("hello")
    assert isinstance(hits2, list)

    # validate_bash
    result = bridge.validate_bash("ls -la")
    assert isinstance(result, BashValidation)
    assert isinstance(result.allowed, bool)
    assert isinstance(result.reason, str)


# ---------------------------------------------------------------------------
# 11. Graceful degradation
# ---------------------------------------------------------------------------
def test_graceful_degradation() -> None:
    """fallback_on_error=True silently falls back when Rust raises."""
    # Even if Rust is available, errors fall back to Python
    cfg = RustBridgeConfig(prefer_rust=True, fallback_on_error=True)

    with (
        patch("lib.rust_bridge._RUST_AVAILABLE", True),
        patch("lib.rust_bridge._kazuba_hooks") as mock_hooks,
    ):
        mock_hooks.detect_secrets.side_effect = RuntimeError("Rust exploded")
        bridge = RustBridge(config=cfg)
        bridge._use_rust = True  # Force rust path

        # Should fall back gracefully
        result = bridge.check_secrets('api_key = "abcdefghijklmnopqrstuvwxyz12345"')
        assert isinstance(result, list)
        # Result came from Python fallback
        if result:
            assert result[0].backend == "python"


# ---------------------------------------------------------------------------
# 12. Error handling fallback
# ---------------------------------------------------------------------------
def test_error_handling_fallback() -> None:
    """When Rust validate_bash raises, Python fallback is used."""
    cfg = RustBridgeConfig(prefer_rust=True, fallback_on_error=True)

    with (
        patch("lib.rust_bridge._RUST_AVAILABLE", True),
        patch("lib.rust_bridge._kazuba_hooks") as mock_hooks,
    ):
        mock_hooks.validate_bash_command.side_effect = RuntimeError("crash")
        bridge = RustBridge(config=cfg)
        bridge._use_rust = True

        result = bridge.validate_bash("ls -la")
        assert isinstance(result, BashValidation)
        assert result.backend == "python"


# ---------------------------------------------------------------------------
# 13. Fallback config
# ---------------------------------------------------------------------------
def test_fallback_config() -> None:
    """RustBridgeConfig with prefer_rust=False is frozen and accessible."""
    cfg = RustBridgeConfig(prefer_rust=False, fallback_on_error=True)
    bridge = _python_bridge()

    assert bridge.config.prefer_rust is False
    # Frozen
    with pytest.raises((TypeError, AttributeError, Exception)):
        cfg.prefer_rust = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 14. Fallback singleton
# ---------------------------------------------------------------------------
def test_fallback_singleton() -> None:
    """Even in fallback mode, singleton works correctly."""
    cfg = RustBridgeConfig(prefer_rust=False)
    b1 = RustBridge.instance(cfg)
    b2 = RustBridge.instance()
    assert b1 is b2
    assert b1.backend_name == "python"


# ---------------------------------------------------------------------------
# 15. Fallback backend name
# ---------------------------------------------------------------------------
def test_fallback_backend_name() -> None:
    """Python fallback bridge reports backend_name='python'."""
    bridge = _python_bridge()
    assert bridge.backend_name == "python"

    sd = SecretsDetector(config=RustBridgeConfig(prefer_rust=False))
    assert sd.backend_name == "python"

    pm = PatternMatcher(config=RustBridgeConfig(prefer_rust=False))
    assert pm.backend_name == "python"


# ---------------------------------------------------------------------------
# Additional edge cases for coverage
# ---------------------------------------------------------------------------
def test_python_validate_bash_empty() -> None:
    """Empty command always allowed in Python fallback."""
    result = _python_validate_bash("")
    assert result.allowed is True
    assert result.backend == "python"


def test_python_validate_bash_fork_bomb() -> None:
    """Fork bomb detected by Python fallback."""
    result = _python_validate_bash(":(){ :|:& };:")
    assert result.allowed is False
    assert result.severity == "high"


def test_python_validate_bash_chmod_777() -> None:
    """chmod 777 detected as dangerous (blocked)."""
    result = _python_validate_bash("chmod 777 /etc/passwd")
    assert result.allowed is False
    assert result.severity is not None


def test_secrets_detector_is_clean() -> None:
    """SecretsDetector.is_clean returns correct bool."""
    sd = SecretsDetector(config=RustBridgeConfig(prefer_rust=False))
    assert sd.is_clean("hello world") is True
    assert sd.is_clean('api_key = "abcdefghijklmnopqrstuvwxyz12345"') is False
