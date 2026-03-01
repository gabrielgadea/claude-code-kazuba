"""Rust Acceleration Layer — Python facade with automatic fallback.

Attempts to import the compiled Rust extension (kazuba_hooks).
If unavailable, falls back transparently to pure-Python implementations
from lib/patterns.py. All public interfaces remain identical.

Usage:
    from lib.rust_bridge import RustBridge, SecretsDetector, PatternMatcher

    bridge = RustBridge.instance()
    result = bridge.check_secrets("api_key = 'sk-abc123...'")
    is_safe = bridge.validate_bash("rm -rf /")
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from lib.patterns import BashSafetyPatterns, PatternSet, SecretPatterns

# ---------------------------------------------------------------------------
# Try importing the compiled Rust extension (optional, fails gracefully)
# ---------------------------------------------------------------------------
_RUST_AVAILABLE = False
_kazuba_hooks: Any = None

try:
    import kazuba_hooks as _kazuba_hooks  # type: ignore[import-untyped]

    _RUST_AVAILABLE = True  # pyright: ignore[reportConstantRedefinition]
except ImportError:
    _kazuba_hooks = None


# ---------------------------------------------------------------------------
# Configuration model (Pydantic v2, frozen)
# ---------------------------------------------------------------------------
class RustBridgeConfig(BaseModel, frozen=True):
    """Immutable configuration for the RustBridge facade."""

    prefer_rust: bool = Field(default=True, description="Use Rust backend when available")
    fallback_on_error: bool = Field(default=True, description="Fall back to Python on Rust errors")
    benchmark_mode: bool = Field(default=False, description="Collect timing metrics")
    max_content_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum content size to scan (bytes)",
    )


# ---------------------------------------------------------------------------
# Result types (frozen dataclasses)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SecretHit:
    """A single secret detection hit."""

    description: str
    pattern_index: int
    backend: str  # "rust" | "python"


@dataclass(frozen=True)
class PatternHit:
    """A single pattern match result."""

    pattern_name: str
    matched_text: str
    start: int
    end: int
    backend: str


@dataclass(frozen=True)
class BashValidation:
    """Result of bash command safety validation."""

    allowed: bool
    reason: str
    severity: str | None  # "high" | "medium" | "low" | None
    matched_pattern: str | None
    backend: str


@dataclass(frozen=True)
class BenchmarkResult:
    """Timing result for benchmark mode."""

    operation: str
    backend: str
    elapsed_ns: int
    result_count: int


# ---------------------------------------------------------------------------
# Python backend helpers
# ---------------------------------------------------------------------------
_PYTHON_SECRETS: PatternSet = SecretPatterns.create()
_PYTHON_BASH: PatternSet = BashSafetyPatterns.create()


def _python_check_secrets(content: str) -> list[SecretHit]:
    """Detect secrets using the pure-Python pattern engine."""
    matches = _PYTHON_SECRETS.detect(content)
    return [
        SecretHit(
            description=m.pattern_name,
            pattern_index=i,
            backend="python",
        )
        for i, m in enumerate(matches)
    ]


def _python_match_patterns(text: str, pattern_set: PatternSet) -> list[PatternHit]:
    """Match patterns using pure-Python engine."""
    raw = pattern_set.detect(text)
    return [
        PatternHit(
            pattern_name=m.pattern_name,
            matched_text=m.matched_text,
            start=m.start,
            end=m.end,
            backend="python",
        )
        for m in raw
    ]


def _python_validate_bash(command: str) -> BashValidation:
    """Validate bash command safety using pure-Python patterns."""
    if not command.strip():
        return BashValidation(
            allowed=True,
            reason="Empty command",
            severity=None,
            matched_pattern=None,
            backend="python",
        )

    # Check safe patterns first (patterns module has bash safety)
    hits = _PYTHON_BASH.detect(command)
    if hits:
        match = hits[0]
        return BashValidation(
            allowed=False,
            reason=f"Dangerous pattern detected: {match.pattern_name[:80]}",
            severity="high",
            matched_pattern=match.matched_text,
            backend="python",
        )

    # Additional Python-level checks for common dangerous patterns
    dangerous_literals = [
        ("rm -rf /", "high", "Recursive delete of root filesystem"),
        ("rm -rf /*", "high", "Recursive delete of root filesystem wildcard"),
        ("sudo rm -rf", "high", "Privileged recursive delete"),
        ("| sh", "high", "Pipe to shell — potential code injection"),
        ("| bash", "high", "Pipe to bash — potential code injection"),
        ("dd of=/dev/", "high", "Direct write to device"),
        ("mkfs.", "high", "Filesystem format — data destruction"),
        (":(){ :|:& };:", "high", "Fork bomb"),
        ("chmod 777", "medium", "World-writable permissions"),
        ("> /etc/", "medium", "Writing to system config directory"),
        ("> /usr/", "medium", "Writing to system binaries directory"),
    ]

    for pattern_str, severity, reason in dangerous_literals:
        if pattern_str in command:
            return BashValidation(
                allowed=False,
                reason=reason,
                severity=severity,
                matched_pattern=pattern_str,
                backend="python",
            )

    return BashValidation(
        allowed=True,
        reason="Command is safe",
        severity=None,
        matched_pattern=None,
        backend="python",
    )


# ---------------------------------------------------------------------------
# Rust backend helpers
# ---------------------------------------------------------------------------
def _rust_check_secrets(content: str, file_path: str = "") -> list[SecretHit]:
    """Detect secrets using the compiled Rust engine."""
    assert _kazuba_hooks is not None
    raw: list[dict[str, str]] = _kazuba_hooks.detect_secrets(content, file_path)
    return [
        SecretHit(
            description=item.get("type", "unknown"),
            pattern_index=int(item.get("pattern_index", 0)),
            backend="rust",
        )
        for item in raw
    ]


def _rust_validate_bash(command: str) -> BashValidation:
    """Validate bash command using compiled Rust engine."""
    assert _kazuba_hooks is not None
    result: dict[str, Any] = _kazuba_hooks.validate_bash_command(command)
    return BashValidation(
        allowed=bool(result.get("allowed", True)),
        reason=str(result.get("reason", "")),
        severity=result.get("severity"),
        matched_pattern=result.get("matched_pattern"),
        backend="rust",
    )


# ---------------------------------------------------------------------------
# Main Facade — RustBridge
# ---------------------------------------------------------------------------
class RustBridge:
    """Facade providing unified access to Rust or Python backend.

    Use RustBridge.instance() to obtain the singleton.
    """

    _singleton: RustBridge | None = None

    def __init__(self, config: RustBridgeConfig | None = None) -> None:
        self._config = config or RustBridgeConfig()
        self._use_rust = _RUST_AVAILABLE and self._config.prefer_rust
        self._benchmarks: list[BenchmarkResult] = []

    # ---- Singleton -------------------------------------------------------

    @classmethod
    def instance(cls, config: RustBridgeConfig | None = None) -> RustBridge:
        """Return (or create) the process-level singleton."""
        if cls._singleton is None:
            cls._singleton = cls(config)
        return cls._singleton

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton (used in tests)."""
        cls._singleton = None

    # ---- Properties ------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when Rust extension is loaded and preferred."""
        return self._use_rust

    @property
    def backend_name(self) -> str:
        """Name of the active backend: 'rust' or 'python'."""
        return "rust" if self._use_rust else "python"

    @property
    def config(self) -> RustBridgeConfig:
        """Active configuration."""
        return self._config

    # ---- Public API ------------------------------------------------------

    def check_secrets(self, content: str, file_path: str = "") -> list[SecretHit]:
        """Scan content for secrets/credentials.

        Args:
            content: Text content to scan.
            file_path: Optional path for safe-file exclusions.

        Returns:
            List of SecretHit instances (empty = clean).
        """
        if len(content.encode()) > self._config.max_content_bytes:
            content = content[: self._config.max_content_bytes]

        t0 = time.perf_counter_ns()
        try:
            if self._use_rust:
                result = _rust_check_secrets(content, file_path)
            else:
                result = _python_check_secrets(content)
        except Exception:
            if self._config.fallback_on_error:
                result = _python_check_secrets(content)
            else:
                raise

        if self._config.benchmark_mode:
            self._benchmarks.append(
                BenchmarkResult(
                    "check_secrets", self.backend_name, time.perf_counter_ns() - t0, len(result)
                )
            )
        return result

    def match_patterns(self, text: str, pattern_set: PatternSet | None = None) -> list[PatternHit]:
        """Match patterns against text.

        Args:
            text: Text to search.
            pattern_set: Optional PatternSet; defaults to secrets patterns.

        Returns:
            List of PatternHit instances.
        """
        ps = pattern_set or _PYTHON_SECRETS
        t0 = time.perf_counter_ns()
        result = _python_match_patterns(text, ps)
        if self._config.benchmark_mode:
            self._benchmarks.append(
                BenchmarkResult(
                    "match_patterns", "python", time.perf_counter_ns() - t0, len(result)
                )
            )
        return result

    def validate_bash(self, command: str) -> BashValidation:
        """Validate a bash command for dangerous patterns.

        Args:
            command: Shell command string to validate.

        Returns:
            BashValidation with allowed=True/False and reason.
        """
        t0 = time.perf_counter_ns()
        try:
            if self._use_rust:
                result = _rust_validate_bash(command)
            else:
                result = _python_validate_bash(command)
        except Exception:
            if self._config.fallback_on_error:
                result = _python_validate_bash(command)
            else:
                raise

        if self._config.benchmark_mode:
            self._benchmarks.append(
                BenchmarkResult("validate_bash", self.backend_name, time.perf_counter_ns() - t0, 1)
            )
        return result

    def get_benchmarks(self) -> list[BenchmarkResult]:
        """Return collected benchmark results (only when benchmark_mode=True)."""
        return list(self._benchmarks)


# ---------------------------------------------------------------------------
# High-level convenience classes
# ---------------------------------------------------------------------------
class SecretsDetector:
    """Convenience wrapper focused on secret detection."""

    def __init__(self, config: RustBridgeConfig | None = None) -> None:
        self._bridge = RustBridge(config)

    @property
    def backend_name(self) -> str:
        return self._bridge.backend_name

    def scan(self, content: str, file_path: str = "") -> list[SecretHit]:
        """Scan content for secrets.

        Returns list of SecretHit (empty = no secrets found).
        """
        return self._bridge.check_secrets(content, file_path)

    def is_clean(self, content: str, file_path: str = "") -> bool:
        """Return True if no secrets detected."""
        return len(self.scan(content, file_path)) == 0


class PatternMatcher:
    """Convenience wrapper focused on general pattern matching."""

    def __init__(
        self,
        pattern_set: PatternSet | None = None,
        config: RustBridgeConfig | None = None,
    ) -> None:
        self._bridge = RustBridge(config)
        self._pattern_set = pattern_set or _PYTHON_SECRETS

    @property
    def backend_name(self) -> str:
        return self._bridge.backend_name

    def match(self, text: str) -> list[PatternHit]:
        """Find all pattern matches in text."""
        return self._bridge.match_patterns(text, self._pattern_set)

    def has_match(self, text: str) -> bool:
        """Return True if any pattern matches."""
        return len(self.match(text)) > 0
