"""Tests for scripts/benchmark_hooks.py — BenchmarkRunner."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to sys.path for direct import
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark_hooks import (  # noqa: E402
    BenchmarkConfig,
    BenchmarkResult,
    _build_parser,
    compute_percentiles,
    discover_hooks,
    format_report,
    run_all_benchmarks,
    run_hook_benchmark,
    run_single_hook,
)

# ---------------------------------------------------------------------------
# compute_percentiles
# ---------------------------------------------------------------------------


def test_compute_percentiles_empty_returns_zeros() -> None:
    """Empty input yields 0.0 for all percentiles."""
    result = compute_percentiles([], (50, 95, 99))
    assert result == {50: 0.0, 95: 0.0, 99: 0.0}


def test_compute_percentiles_single_value() -> None:
    """Single value → all percentiles equal that value."""
    result = compute_percentiles([42.0], (50, 95, 99))
    assert result[50] == pytest.approx(42.0)
    assert result[95] == pytest.approx(42.0)
    assert result[99] == pytest.approx(42.0)


def test_compute_percentiles_sorted_output() -> None:
    """P50 <= P95 <= P99 for any input."""
    times = [10.0, 200.0, 30.0, 400.0, 5.0]
    result = compute_percentiles(times, (50, 95, 99))
    assert result[50] <= result[95] <= result[99]


def test_compute_percentiles_p50_is_median() -> None:
    """P50 approximates the median for a uniform distribution."""
    times = [float(i) for i in range(1, 101)]
    result = compute_percentiles(times, (50,))
    # Nearest-rank P50: ~50th value out of 100
    assert 45.0 <= result[50] <= 55.0


def test_compute_percentiles_returns_dict_with_all_keys() -> None:
    """All requested percentiles are present in the output."""
    times = [1.0, 2.0, 3.0]
    result = compute_percentiles(times, (25, 50, 75, 99))
    assert set(result.keys()) == {25, 50, 75, 99}


# ---------------------------------------------------------------------------
# BenchmarkResult
# ---------------------------------------------------------------------------


def _make_result(**kwargs: object) -> BenchmarkResult:
    defaults: dict[str, object] = {
        "hook_name": "test_hook",
        "hook_path": Path("/tmp/test_hook.py"),
        "iterations": 40,
        "p50_ms": 10.0,
        "p95_ms": 20.0,
        "p99_ms": 25.0,
        "min_ms": 5.0,
        "max_ms": 30.0,
        "mean_ms": 12.0,
        "errors": 0,
    }
    defaults.update(kwargs)
    return BenchmarkResult(**defaults)  # type: ignore[arg-type]


def test_benchmark_result_success_rate_no_errors() -> None:
    """100% success rate when errors == 0."""
    result = _make_result(iterations=50, errors=0)
    assert result.success_rate == pytest.approx(1.0)


def test_benchmark_result_success_rate_with_errors() -> None:
    """Correct fraction computed with errors."""
    result = _make_result(iterations=40, errors=10)
    assert result.success_rate == pytest.approx(0.8)


def test_benchmark_result_success_rate_all_errors() -> None:
    """Zero success rate when all iterations fail."""
    result = _make_result(iterations=0, errors=50)
    assert result.success_rate == pytest.approx(0.0)


def test_benchmark_result_is_healthy_true() -> None:
    """Healthy when success_rate >= 0.9 and p99 < 3000 ms."""
    result = _make_result(iterations=90, errors=10, p99_ms=100.0)
    assert result.is_healthy is True


def test_benchmark_result_is_healthy_false_high_p99() -> None:
    """Unhealthy when p99 >= 3000 ms."""
    result = _make_result(iterations=50, errors=0, p99_ms=5000.0)
    assert result.is_healthy is False


def test_benchmark_result_to_dict_has_required_keys() -> None:
    """to_dict() returns all expected keys."""
    result = _make_result()
    d = result.to_dict()
    for key in (
        "hook_name", "p50_ms", "p95_ms", "p99_ms",
        "success_rate", "is_healthy", "errors",
    ):
        assert key in d


# ---------------------------------------------------------------------------
# BenchmarkConfig
# ---------------------------------------------------------------------------


def test_benchmark_config_defaults() -> None:
    """BenchmarkConfig has sensible defaults."""
    cfg = BenchmarkConfig()
    assert cfg.iterations == 50
    assert cfg.warmup_iterations == 5
    assert cfg.timeout_seconds == 5.0
    assert 50 in cfg.percentiles


def test_benchmark_config_from_args() -> None:
    """from_args() correctly maps parsed arguments."""
    parser = _build_parser()
    args = parser.parse_args(["--iterations", "20", "--warmup", "3"])
    cfg = BenchmarkConfig.from_args(args)
    assert cfg.iterations == 20
    assert cfg.warmup_iterations == 3


# ---------------------------------------------------------------------------
# discover_hooks
# ---------------------------------------------------------------------------


def test_discover_hooks_missing_dir_returns_empty() -> None:
    """Non-existent directory returns empty list."""
    result = discover_hooks(Path("/tmp/nonexistent_hooks_xyz"))
    assert result == []


def test_discover_hooks_finds_py_files(tmp_path: Path) -> None:
    """Discovers .py files, skipping __init__.py."""
    (tmp_path / "my_hook.py").touch()
    (tmp_path / "__init__.py").touch()
    (tmp_path / "not_python.txt").touch()
    hooks = discover_hooks(tmp_path)
    assert len(hooks) == 1
    assert hooks[0].name == "my_hook.py"


def test_discover_hooks_sorted_output(tmp_path: Path) -> None:
    """Hooks are returned in sorted order."""
    (tmp_path / "z_hook.py").touch()
    (tmp_path / "a_hook.py").touch()
    hooks = discover_hooks(tmp_path)
    names = [h.name for h in hooks]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# run_single_hook (with mocking)
# ---------------------------------------------------------------------------


def test_run_single_hook_success() -> None:
    """Valid exit code returns (elapsed, True)."""
    with patch("scripts.benchmark_hooks.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        elapsed, success = run_single_hook(
            Path("/fake/hook.py"), '{"tool_name":"Read"}', 5.0, sys.executable
        )
        assert success is True
        assert elapsed >= 0.0


def test_run_single_hook_timeout() -> None:
    """Timeout returns (elapsed, False)."""
    import subprocess

    with patch("scripts.benchmark_hooks.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=5.0)
        elapsed, success = run_single_hook(
            Path("/fake/hook.py"), '{"tool_name":"Read"}', 5.0, sys.executable
        )
        assert success is False


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------


def test_format_report_empty_returns_message() -> None:
    """Empty results list returns a no-results message."""
    report = format_report([])
    assert "No benchmark results" in report


def test_format_report_contains_hook_name() -> None:
    """Report includes the hook name."""
    result = _make_result(hook_name="my_awesome_hook")
    report = format_report([result])
    assert "my_awesome_hook" in report


def test_format_report_contains_summary_line() -> None:
    """Report includes a summary line with hook count."""
    result = _make_result()
    report = format_report([result])
    assert "1 hooks benchmarked" in report


# ---------------------------------------------------------------------------
# run_all_benchmarks
# ---------------------------------------------------------------------------


def test_run_all_benchmarks_empty_dir_returns_empty(tmp_path: Path) -> None:
    """Empty hooks directory returns empty results list."""
    cfg = BenchmarkConfig(hooks_dir=tmp_path, iterations=1, warmup_iterations=0)
    results = run_all_benchmarks(cfg)
    assert results == []


def test_run_all_benchmarks_default_config_returns_list() -> None:
    """Default config (no hooks dir) returns a list."""
    results = run_all_benchmarks(
        BenchmarkConfig(
            hooks_dir=Path("/tmp/nonexistent_xyz"),
            iterations=1,
            warmup_iterations=0,
        )
    )
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# run_single_hook — OSError branch
# ---------------------------------------------------------------------------


def test_run_single_hook_os_error() -> None:
    """OSError (e.g., missing interpreter) returns (elapsed, False)."""
    with patch("scripts.benchmark_hooks.subprocess.run") as mock_run:
        mock_run.side_effect = OSError("exec error")
        elapsed, success = run_single_hook(
            Path("/fake/hook.py"), '{"tool_name":"Read"}', 5.0, sys.executable
        )
        assert success is False
        assert elapsed >= 0.0


def test_run_single_hook_non_zero_exit_valid() -> None:
    """Exit code 2 (deny) is still considered a valid hook response."""
    with patch("scripts.benchmark_hooks.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=2)
        _, success = run_single_hook(
            Path("/fake/hook.py"), "{}", 5.0, sys.executable
        )
        assert success is True


def test_run_single_hook_invalid_exit_code() -> None:
    """Exit code 99 is not a valid hook response."""
    with patch("scripts.benchmark_hooks.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=99)
        _, success = run_single_hook(
            Path("/fake/hook.py"), "{}", 5.0, sys.executable
        )
        assert success is False


# ---------------------------------------------------------------------------
# run_hook_benchmark (mocked)
# ---------------------------------------------------------------------------


def test_run_hook_benchmark_with_mocked_hook(tmp_path: Path) -> None:
    """run_hook_benchmark returns a BenchmarkResult with mocked subprocess."""
    hook_path = tmp_path / "fake_hook.py"
    hook_path.write_text("import sys; sys.exit(0)\n")

    cfg = BenchmarkConfig(
        hooks_dir=tmp_path,
        iterations=3,
        warmup_iterations=1,
        timeout_seconds=5.0,
    )

    with patch("scripts.benchmark_hooks.run_single_hook") as mock_run:
        mock_run.return_value = (10.0, True)
        result = run_hook_benchmark(hook_path, cfg)

    assert isinstance(result, BenchmarkResult)
    assert result.hook_name == "fake_hook"
    assert result.iterations == 3
    assert result.errors == 0


def test_run_hook_benchmark_counts_errors(tmp_path: Path) -> None:
    """Errors are counted correctly when run_single_hook returns failures."""
    hook_path = tmp_path / "bad_hook.py"
    hook_path.write_text("# bad hook\n")

    cfg = BenchmarkConfig(
        hooks_dir=tmp_path,
        iterations=4,
        warmup_iterations=0,
    )

    with patch("scripts.benchmark_hooks.run_single_hook") as mock_run:
        # 2 success, 2 failures
        mock_run.side_effect = [
            (5.0, True), (6.0, True), (0.0, False), (0.0, False)
        ]
        result = run_hook_benchmark(hook_path, cfg)

    assert result.iterations == 2
    assert result.errors == 2


# ---------------------------------------------------------------------------
# main() function
# ---------------------------------------------------------------------------


def test_main_exits_1_when_no_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() exits 1 when no hooks are found."""
    monkeypatch.setattr(
        "sys.argv",
        ["benchmark_hooks.py", "--hooks-dir", "/tmp/nonexistent_hooks_xyz"],
    )
    with pytest.raises(SystemExit) as exc:
        from scripts.benchmark_hooks import main
        main()
    assert exc.value.code == 1


def test_main_with_hooks_runs_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() runs and prints report when hooks are found."""
    # Create a minimal valid hook that exits 0
    hook = tmp_path / "echo_hook.py"
    hook.write_text('import sys,json; sys.exit(0)\n')

    monkeypatch.setattr(
        "sys.argv",
        ["benchmark_hooks.py", "--hooks-dir", str(tmp_path),
         "--iterations", "2", "--warmup", "0"],
    )
    with patch("scripts.benchmark_hooks.run_single_hook") as mock_run:
        mock_run.return_value = (10.0, True)
        # Should not raise SystemExit (all hooks healthy)
        from scripts.benchmark_hooks import main
        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_main_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """main() with --json outputs content containing JSON array markers."""
    hook = tmp_path / "test_hook.py"
    hook.write_text('import sys; sys.exit(0)\n')

    monkeypatch.setattr(
        "sys.argv",
        ["benchmark_hooks.py", "--hooks-dir", str(tmp_path),
         "--iterations", "2", "--warmup", "0", "--json"],
    )
    with patch("scripts.benchmark_hooks.run_single_hook") as mock_run:
        mock_run.return_value = (10.0, True)
        try:
            from scripts.benchmark_hooks import main
            main()
        except SystemExit:
            pass
    captured = capsys.readouterr()
    # main() prints a progress line then multi-line JSON
    assert "[" in captured.out and "hook_name" in captured.out


def test_main_exits_1_when_unhealthy_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() exits 1 when a hook has p99 >= 3000 ms (unhealthy)."""
    hook = tmp_path / "slow_hook.py"
    hook.write_text('import sys; sys.exit(0)\n')

    monkeypatch.setattr(
        "sys.argv",
        ["benchmark_hooks.py", "--hooks-dir", str(tmp_path),
         "--iterations", "2", "--warmup", "0"],
    )
    # Return very slow times to trigger unhealthy status (p99 >= 3000 ms)
    with patch("scripts.benchmark_hooks.run_single_hook") as mock_run:
        mock_run.return_value = (5000.0, True)
        with pytest.raises(SystemExit) as exc:
            from scripts.benchmark_hooks import main
            main()
    assert exc.value.code == 1
