#!/usr/bin/env python3
"""Hook benchmark suite — measures P50/P95/P99 execution times for all hooks.

Discovers hook scripts in a target directory and runs each one repeatedly
with a synthetic payload, collecting timing data to compute percentile metrics.

Usage::

    python scripts/benchmark_hooks.py [--hooks-dir .claude/hooks] [--iterations 50]

Exit codes:
    0  — benchmark completed successfully
    1  — no hooks found or critical error
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkConfig:
    """Immutable configuration for the benchmark runner."""

    hooks_dir: Path = field(default_factory=lambda: Path(".claude/hooks"))
    iterations: int = 50
    warmup_iterations: int = 5
    timeout_seconds: float = 5.0
    percentiles: tuple[int, ...] = (50, 95, 99)
    python_executable: str = sys.executable
    sample_payload: str = json.dumps(
        {
            "tool_name": "Read",
            "tool_input": {"file_path": "README.md"},
            "session_id": "benchmark-session-001",
        }
    )

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> BenchmarkConfig:
        """Construct from parsed CLI arguments."""
        return cls(
            hooks_dir=Path(args.hooks_dir),
            iterations=args.iterations,
            warmup_iterations=args.warmup,
            timeout_seconds=args.timeout,
        )


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkResult:
    """Timing statistics for a single hook."""

    hook_name: str
    hook_path: Path
    iterations: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    errors: int

    @property
    def success_rate(self) -> float:
        """Fraction of iterations that completed without error (0.0–1.0)."""
        total = self.iterations + self.errors
        return (self.iterations / total) if total > 0 else 0.0

    @property
    def is_healthy(self) -> bool:
        """True when success rate >= 90% and p99 < 3000 ms."""
        return self.success_rate >= 0.9 and self.p99_ms < 3000.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-friendly dict."""
        return {
            "hook_name": self.hook_name,
            "hook_path": str(self.hook_path),
            "iterations": self.iterations,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "mean_ms": self.mean_ms,
            "errors": self.errors,
            "success_rate": round(self.success_rate, 4),
            "is_healthy": self.is_healthy,
        }


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def compute_percentiles(
    times: list[float],
    percentiles: tuple[int, ...] = (50, 95, 99),
) -> dict[int, float]:
    """Compute requested percentiles from a list of timing values (ms).

    Args:
        times: List of timing measurements in milliseconds.
        percentiles: Tuple of integer percentile values (e.g., (50, 95, 99)).

    Returns:
        Dict mapping each percentile to its computed value. All zeros if empty.
    """
    if not times:
        return {p: 0.0 for p in percentiles}

    sorted_times = sorted(times)
    n = len(sorted_times)
    result: dict[int, float] = {}

    for p in percentiles:
        # Nearest-rank method
        idx = max(0, int((p / 100.0) * n) - 1)
        idx = min(idx, n - 1)
        result[p] = round(sorted_times[idx], 3)

    return result


def run_single_hook(
    hook_path: Path,
    payload: str,
    timeout: float,
    python_exe: str,
) -> tuple[float, bool]:
    """Run a hook script once and return (elapsed_ms, success).

    Args:
        hook_path: Path to the hook Python script.
        payload: JSON string to pipe to the hook's stdin.
        timeout: Maximum allowed execution time in seconds.
        python_exe: Python interpreter path.

    Returns:
        Tuple of (elapsed time in ms, True if hook exited with a valid code).
    """
    start = time.perf_counter()
    try:
        result = subprocess.run(  # noqa: S603
            [python_exe, str(hook_path)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - start) * 1000.0
        # Hooks exit with 0 (allow), 1 (block), or 2 (deny) — all valid
        return elapsed, result.returncode in (0, 1, 2)
    except subprocess.TimeoutExpired:
        return (time.perf_counter() - start) * 1000.0, False
    except OSError:
        return (time.perf_counter() - start) * 1000.0, False


def run_hook_benchmark(
    hook_path: Path,
    config: BenchmarkConfig,
) -> BenchmarkResult:
    """Run the full benchmark for a single hook script.

    Performs warmup iterations (uncounted), then measured iterations.

    Args:
        hook_path: Path to the hook Python script.
        config: Benchmark configuration.

    Returns:
        BenchmarkResult with timing statistics.
    """
    payload = config.sample_payload

    # Warmup phase (results discarded)
    for _ in range(config.warmup_iterations):
        run_single_hook(
            hook_path, payload, config.timeout_seconds, config.python_executable
        )

    # Measured phase
    times: list[float] = []
    errors = 0

    for _ in range(config.iterations):
        elapsed, success = run_single_hook(
            hook_path, payload, config.timeout_seconds, config.python_executable
        )
        if success:
            times.append(elapsed)
        else:
            errors += 1

    pcts = compute_percentiles(times, config.percentiles)

    return BenchmarkResult(
        hook_name=hook_path.stem,
        hook_path=hook_path,
        iterations=len(times),
        p50_ms=pcts.get(50, 0.0),
        p95_ms=pcts.get(95, 0.0),
        p99_ms=pcts.get(99, 0.0),
        min_ms=round(min(times), 3) if times else 0.0,
        max_ms=round(max(times), 3) if times else 0.0,
        mean_ms=round(statistics.mean(times), 3) if times else 0.0,
        errors=errors,
    )


def discover_hooks(hooks_dir: Path) -> list[Path]:
    """Discover all Python hook scripts in a directory.

    Args:
        hooks_dir: Directory to scan for hook scripts.

    Returns:
        Sorted list of .py file paths (excludes __init__.py and __pycache__).
    """
    if not hooks_dir.exists() or not hooks_dir.is_dir():
        return []

    return sorted(
        p
        for p in hooks_dir.glob("*.py")
        if p.name not in ("__init__.py",) and not p.name.startswith("_")
    )


def format_report(results: list[BenchmarkResult]) -> str:
    """Format benchmark results as a human-readable table.

    Args:
        results: List of BenchmarkResult objects.

    Returns:
        Multi-line formatted string report.
    """
    if not results:
        return "No benchmark results to display.\n"

    header = (
        f"\n{'Hook':<35} {'P50':>8} {'P95':>8} {'P99':>8} "
        f"{'Min':>8} {'Max':>8} {'Mean':>8} {'OK%':>6}\n"
    )
    separator = "-" * 90 + "\n"
    rows = []

    for r in results:
        health_mark = "✓" if r.is_healthy else "✗"
        rows.append(
            f"{health_mark} {r.hook_name:<33} "
            f"{r.p50_ms:>7.1f}ms {r.p95_ms:>7.1f}ms {r.p99_ms:>7.1f}ms "
            f"{r.min_ms:>7.1f}ms {r.max_ms:>7.1f}ms {r.mean_ms:>7.1f}ms "
            f"{r.success_rate * 100:>5.1f}%\n"
        )

    unhealthy = [r for r in results if not r.is_healthy]
    summary = (
        f"\nSummary: {len(results)} hooks benchmarked, "
        f"{len(unhealthy)} with health issues.\n"
    )

    return header + separator + "".join(rows) + separator + summary


def run_all_benchmarks(
    config: BenchmarkConfig | None = None,
) -> list[BenchmarkResult]:
    """Discover and benchmark all hooks in the configured directory.

    Args:
        config: Optional BenchmarkConfig; uses defaults if omitted.

    Returns:
        List of BenchmarkResult objects, one per discovered hook.
    """
    cfg = config or BenchmarkConfig()
    hooks = discover_hooks(cfg.hooks_dir)

    results: list[BenchmarkResult] = []
    for hook_path in hooks:
        result = run_hook_benchmark(hook_path, cfg)
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Hook benchmark suite — P50/P95/P99 timing metrics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--hooks-dir",
        default=".claude/hooks",
        help="Directory containing hook scripts to benchmark",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of measured iterations per hook",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Number of warmup iterations (discarded)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Maximum execution time per hook invocation (seconds)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of table",
    )
    return parser


def main() -> None:
    """CLI entry point for the hook benchmark suite."""
    parser = _build_parser()
    args = parser.parse_args()
    config = BenchmarkConfig.from_args(args)

    hooks = discover_hooks(config.hooks_dir)
    if not hooks:
        print(
            f"No hook scripts found in '{config.hooks_dir}'. "
            "Use --hooks-dir to specify the hooks directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Benchmarking {len(hooks)} hook(s) "
        f"({config.warmup_iterations} warmup + {config.iterations} measured iterations)…"
    )

    results = run_all_benchmarks(config)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(format_report(results))

    # Non-zero exit if any hook is unhealthy
    unhealthy = [r for r in results if not r.is_healthy]
    if unhealthy:
        sys.exit(1)


if __name__ == "__main__":
    main()
