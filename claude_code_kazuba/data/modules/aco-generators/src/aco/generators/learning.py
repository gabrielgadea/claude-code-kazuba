"""learning.py — Generator Learning System.

Records generator execution outcomes, computes effectiveness metrics,
extracts patterns, and generates actionable recommendations. Persists
data as append-only JSONL at `.claude/metrics/generator_learning.jsonl`.

Standalone module — no imports from library.py or other generators.
Designed for hook integration (aco_evolution_hook, compliance_collector).

Usage:
    python scripts/aco/generators/learning.py                  # full report
    python scripts/aco/generators/learning.py --top 10         # top generators
    python scripts/aco/generators/learning.py --struggling     # needs attention
    python scripts/aco/generators/learning.py --record '{...}' # record outcome
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_METRICS_DIR = _PROJECT_ROOT / ".claude" / "metrics"
_DEFAULT_METRICS_FILE = _METRICS_DIR / "generator_learning.jsonl"

# ---------------------------------------------------------------------------
# Rust acceleration (dual-mode bridge)
# Availability probed at module load; actual classes imported lazily in
# wilson_rank_generators() and detect_generator_drift() below.
# ---------------------------------------------------------------------------


_RUST_AVAILABLE = importlib.util.find_spec("claude_learning_kernel") is not None


# ---------------------------------------------------------------------------
# Models (frozen Pydantic V2)
# ---------------------------------------------------------------------------


class GeneratorOutcome(BaseModel, frozen=True):
    """Single execution outcome for a generator.

    Recorded after each generator run (generate, validate, rollback,
    dry_run) and appended to the JSONL metrics file.
    """

    timestamp: str
    session_id: str
    generator_name: str
    generator_path: str
    action: str
    success: bool
    duration_seconds: float
    output_loc: int
    validation_passed: bool | None = None
    error_type: str | None = None
    error_message: str | None = None
    context: dict[str, str] = {}


class GeneratorEffectiveness(BaseModel, frozen=True):
    """Computed effectiveness metrics for a single generator.

    Aggregated from all recorded outcomes for that generator.
    """

    generator_name: str
    total_executions: int
    success_rate: float
    avg_duration: float
    avg_output_loc: int
    validation_pass_rate: float
    last_execution: str
    effectiveness_score: float
    trend: str


class LearningReport(BaseModel, frozen=True):
    """Comprehensive learning report across all generators.

    Built from all recorded outcomes with effectiveness metrics,
    extracted patterns, and actionable recommendations.
    """

    generated_at: str
    total_outcomes: int
    unique_generators: int
    overall_success_rate: float
    top_generators: tuple[GeneratorEffectiveness, ...]
    struggling_generators: tuple[GeneratorEffectiveness, ...]
    patterns: tuple[str, ...]
    recommendations: tuple[str, ...]


# ---------------------------------------------------------------------------
# Persistence (JSONL append-only)
# ---------------------------------------------------------------------------


def record_outcome(
    outcome: GeneratorOutcome,
    metrics_path: Path | None = None,
) -> None:
    """Append a generator outcome to the JSONL metrics file.

    Thread-safe via file append mode. Creates parent directories
    if they do not exist.

    Args:
        outcome: The generator execution outcome to record.
        metrics_path: Path to the JSONL file. Defaults to
            `.claude/metrics/generator_learning.jsonl`.
    """
    path = metrics_path or _DEFAULT_METRICS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    line = outcome.model_dump_json()
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    logger.debug("Recorded outcome for %s", outcome.generator_name)


def load_outcomes(
    metrics_path: Path | None = None,
) -> list[GeneratorOutcome]:
    """Load all generator outcomes from the JSONL metrics file.

    Skips malformed lines with a warning instead of failing.

    Args:
        metrics_path: Path to the JSONL file. Defaults to
            `.claude/metrics/generator_learning.jsonl`.

    Returns:
        List of parsed GeneratorOutcome objects.
    """
    path = metrics_path or _DEFAULT_METRICS_FILE

    if not path.exists():
        logger.info("No metrics file found at %s", path)
        return []

    outcomes: list[GeneratorOutcome] = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                outcomes.append(GeneratorOutcome.model_validate_json(stripped))
            except Exception:
                logger.warning(
                    "Skipping malformed line %d in %s",
                    line_num,
                    path,
                )

    logger.debug("Loaded %d outcomes from %s", len(outcomes), path)
    return outcomes


# ---------------------------------------------------------------------------
# Effectiveness computation
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


def _compute_trend(outcomes: list[GeneratorOutcome]) -> str:
    """Determine trend from recent vs previous executions.

    Compares the success rate of the last 5 executions against
    the previous 5 executions.

    Args:
        outcomes: Sorted outcomes (oldest first) for a single generator.

    Returns:
        One of "improving", "stable", or "declining".
    """
    if len(outcomes) < 6:
        return "stable"

    recent = outcomes[-5:]
    previous = outcomes[-10:-5] if len(outcomes) >= 10 else outcomes[:-5]

    if not previous:
        return "stable"

    recent_rate = sum(1 for o in recent if o.success) / len(recent)
    previous_rate = sum(1 for o in previous if o.success) / len(previous)

    delta = recent_rate - previous_rate
    if delta > 0.1:
        return "improving"
    if delta < -0.1:
        return "declining"
    return "stable"


def compute_effectiveness(
    outcomes: list[GeneratorOutcome],
    generator_name: str,
) -> GeneratorEffectiveness:
    """Compute effectiveness metrics for a specific generator.

    Effectiveness score formula:
        0.40 * success_rate
      + 0.25 * validation_pass_rate
      + 0.20 * (1.0 - clamp(avg_duration / 60, 0, 1))
      + 0.15 * min(total_executions / 10, 1.0)

    Args:
        outcomes: All recorded outcomes (will be filtered).
        generator_name: Name of the generator to evaluate.

    Returns:
        Computed effectiveness metrics for the generator.

    Raises:
        ValueError: If no outcomes exist for the given generator.
    """
    filtered = [o for o in outcomes if o.generator_name == generator_name]
    if not filtered:
        msg = f"No outcomes found for generator: {generator_name}"
        raise ValueError(msg)

    # Sort by timestamp for trend analysis
    filtered.sort(key=lambda o: o.timestamp)

    total = len(filtered)
    successes = sum(1 for o in filtered if o.success)
    success_rate = successes / total

    durations = [o.duration_seconds for o in filtered]
    avg_duration = sum(durations) / total

    locs = [o.output_loc for o in filtered]
    avg_loc = int(sum(locs) / total)

    validated = [o for o in filtered if o.validation_passed is not None]
    if validated:
        validation_pass_rate = sum(1 for o in validated if o.validation_passed) / len(validated)
    else:
        validation_pass_rate = 0.0

    last_execution = filtered[-1].timestamp
    trend = _compute_trend(filtered)

    # Weighted composite score
    speed_score = 1.0 - _clamp(avg_duration / 60.0, 0.0, 1.0)
    experience_score = min(total / 10.0, 1.0)

    effectiveness_score = (
        0.40 * success_rate + 0.25 * validation_pass_rate + 0.20 * speed_score + 0.15 * experience_score
    )

    return GeneratorEffectiveness(
        generator_name=generator_name,
        total_executions=total,
        success_rate=round(success_rate, 4),
        avg_duration=round(avg_duration, 2),
        avg_output_loc=avg_loc,
        validation_pass_rate=round(validation_pass_rate, 4),
        last_execution=last_execution,
        effectiveness_score=round(effectiveness_score, 4),
        trend=trend,
    )


def compute_all_effectiveness(
    outcomes: list[GeneratorOutcome],
) -> list[GeneratorEffectiveness]:
    """Compute effectiveness for all generators found in outcomes.

    Groups outcomes by generator_name and computes metrics for each.

    Args:
        outcomes: All recorded outcomes.

    Returns:
        List of effectiveness metrics sorted by score descending.
    """
    names: set[str] = {o.generator_name for o in outcomes}
    results = [compute_effectiveness(outcomes, name) for name in names]
    results.sort(key=lambda e: e.effectiveness_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Rust-accelerated ranking & drift detection
# ---------------------------------------------------------------------------


def _python_wilson(successes: int, total: int, z: float = 1.96) -> float:
    """Python fallback for Wilson score lower bound.

    Accounts for sample size — a generator with 5/5 success ranks
    lower than one with 50/50 because the confidence is less.

    Args:
        successes: Number of successes.
        total: Total number of trials.
        z: Z-score for confidence level (1.96 = 95%).

    Returns:
        Wilson score lower bound (0.0 to 1.0).
    """
    if total == 0:
        return 0.0
    import math

    p = successes / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return (center - spread) / denominator


def _python_ks(baseline: list[float], recent: list[float]) -> float:
    """Python fallback for Kolmogorov-Smirnov statistic.

    Computes the maximum absolute difference between two empirical CDFs.

    Args:
        baseline: Baseline distribution values.
        recent: Recent distribution values.

    Returns:
        KS statistic (0.0 to 1.0). Higher = more divergence.
    """
    if not baseline or not recent:
        return 0.0

    all_values = sorted(set(baseline + recent))
    max_diff = 0.0

    for v in all_values:
        cdf_base = sum(1 for x in baseline if x <= v) / len(baseline)
        cdf_recent = sum(1 for x in recent if x <= v) / len(recent)
        max_diff = max(max_diff, abs(cdf_base - cdf_recent))

    return max_diff


def wilson_rank_generators(
    effectiveness: list[GeneratorEffectiveness],
) -> list[tuple[str, float]]:
    """Rank generators by Wilson score (confidence-weighted success rate).

    Uses Rust WilsonRanker when available for ~5x speedup over batch.
    Falls back to pure Python implementation otherwise.

    Args:
        effectiveness: List of effectiveness metrics.

    Returns:
        List of (generator_name, wilson_score) tuples, sorted descending.
    """
    if not effectiveness:
        return []

    if _RUST_AVAILABLE:
        from claude_learning_kernel import WilsonRanker

        wr = WilsonRanker()
        data = [
            (
                int(e.success_rate * e.total_executions),
                e.total_executions,
            )
            for e in effectiveness
        ]
        scores = wr.wilson_scores_batch(data)
        ranked = list(zip([e.generator_name for e in effectiveness], scores))
    else:
        ranked = [
            (
                e.generator_name,
                _python_wilson(
                    int(e.success_rate * e.total_executions),
                    e.total_executions,
                ),
            )
            for e in effectiveness
        ]

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def detect_generator_drift(
    outcomes: list[GeneratorOutcome],
    generator_name: str,
    window: int = 10,
) -> tuple[float, str]:
    """Detect performance drift for a specific generator.

    Compares success rate distribution of baseline outcomes against
    the most recent *window* outcomes using KS statistic.

    Uses Rust DriftDetector when available for ~5x speedup.

    Args:
        outcomes: All recorded outcomes.
        generator_name: Name of generator to analyze.
        window: Number of recent outcomes to compare against baseline.

    Returns:
        Tuple of (ks_statistic, status) where status is one of:
        "ok" (KS < 0.5), "warning" (0.5 <= KS < 0.8), "alarm" (KS >= 0.8).
    """
    gen_outcomes = [o for o in outcomes if o.generator_name == generator_name]

    if len(gen_outcomes) < window * 2:
        return 0.0, "ok"

    baseline_scores = [
        1.0 if o.success else 0.0 for o in gen_outcomes[:-window]
    ]
    recent_scores = [
        1.0 if o.success else 0.0 for o in gen_outcomes[-window:]
    ]

    if _RUST_AVAILABLE:
        from claude_learning_kernel import DriftDetector

        dd = DriftDetector()
        ks = dd.ks_statistic(baseline_scores, recent_scores)
    else:
        ks = _python_ks(baseline_scores, recent_scores)

    if ks >= 0.8:
        status = "alarm"
    elif ks >= 0.5:
        status = "warning"
    else:
        status = "ok"

    return round(ks, 4), status


# ---------------------------------------------------------------------------
# Pattern extraction
# ---------------------------------------------------------------------------


def _pattern_most_reliable(outcomes: list[GeneratorOutcome]) -> str | None:
    """Find the most reliable generator by success rate (min 3 runs)."""
    by_gen: dict[str, list[GeneratorOutcome]] = defaultdict(list)
    for o in outcomes:
        by_gen[o.generator_name].append(o)

    reliable = []
    for name, gen_outcomes in by_gen.items():
        if len(gen_outcomes) >= 3:
            rate = sum(1 for o in gen_outcomes if o.success) / len(gen_outcomes)
            reliable.append((name, rate, len(gen_outcomes)))

    reliable.sort(key=lambda x: x[1], reverse=True)
    if reliable:
        top = reliable[0]
        return f"Most reliable: {top[0]} ({top[1]:.0%} success over {top[2]} runs)"
    return None


def _pattern_common_failures(outcomes: list[GeneratorOutcome]) -> str | None:
    """Identify common failure modes by error type."""
    errors: Counter[str] = Counter()
    for o in outcomes:
        if not o.success and o.error_type:
            errors[o.error_type] += 1

    if errors:
        top_errors = errors.most_common(3)
        error_strs = [f"{e[0]} ({e[1]}x)" for e in top_errors]
        return f"Common failures: {', '.join(error_strs)}"
    return None


def _pattern_loc_range(outcomes: list[GeneratorOutcome]) -> str | None:
    """Compute LOC statistics for successful generations."""
    locs = [o.output_loc for o in outcomes if o.success and o.output_loc > 0]
    if locs:
        avg_loc = sum(locs) / len(locs)
        return f"Successful output LOC: avg={avg_loc:.0f}, range=[{min(locs)}, {max(locs)}]"
    return None


def _pattern_peak_hour(outcomes: list[GeneratorOutcome]) -> str | None:
    """Find peak activity hour from timestamps."""
    hours: Counter[int] = Counter()
    for o in outcomes:
        try:
            dt = datetime.fromisoformat(o.timestamp)
            hours[dt.hour] += 1
        except (ValueError, TypeError):
            continue

    if hours:
        peak = hours.most_common(1)[0]
        return f"Peak activity hour: {peak[0]:02d}:00 ({peak[1]} executions)"
    return None


def _pattern_action_distribution(outcomes: list[GeneratorOutcome]) -> str | None:
    """Compute action type distribution."""
    actions: Counter[str] = Counter()
    for o in outcomes:
        actions[o.action] += 1

    if actions:
        parts = [f"{a}: {c}" for a, c in actions.most_common()]
        return f"Action distribution: {', '.join(parts)}"
    return None


def extract_patterns(outcomes: list[GeneratorOutcome]) -> list[str]:
    """Extract human-readable patterns from execution history.

    Identifies:
    - Most reliable generators (highest success rate)
    - Common failure modes (error types and counts)
    - Optimal LOC ranges (most successful output sizes)
    - Time-of-day patterns (hour distribution of executions)
    - Action type distribution

    Args:
        outcomes: All recorded outcomes.

    Returns:
        List of pattern description strings.
    """
    if not outcomes:
        return ["No outcomes recorded yet."]

    extractors = [
        _pattern_most_reliable,
        _pattern_common_failures,
        _pattern_loc_range,
        _pattern_peak_hour,
        _pattern_action_distribution,
    ]

    patterns: list[str] = []
    for extractor in extractors:
        result = extractor(outcomes)
        if result is not None:
            patterns.append(result)

    return patterns


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def generate_recommendations(
    effectiveness: list[GeneratorEffectiveness],
) -> list[str]:
    """Generate actionable recommendations from effectiveness data.

    Produces targeted advice for generators that need attention:
    - Low success rate: review for common errors
    - High validation but slow: optimize execution
    - No recorded executions: run validation
    - Declining trend: investigate regression

    Args:
        effectiveness: List of effectiveness metrics for all generators.

    Returns:
        List of recommendation strings, most urgent first.
    """
    if not effectiveness:
        return ["No generator data available. Run generators to build history."]

    recs: list[str] = []

    for eff in effectiveness:
        # High failure rate
        if eff.success_rate < 0.6:
            failure_pct = (1.0 - eff.success_rate) * 100
            recs.append(
                f"Review {eff.generator_name} — "
                f"{failure_pct:.0f}% failure rate "
                f"({eff.total_executions} executions)"
            )

        # Slow execution with good validation
        if eff.avg_duration > 30.0 and eff.validation_pass_rate > 0.8:
            recs.append(
                f"Optimize {eff.generator_name} — "
                f"avg {eff.avg_duration:.1f}s per execution "
                f"(validation pass rate is good at "
                f"{eff.validation_pass_rate:.0%})"
            )

        # Declining trend
        if eff.trend == "declining":
            recs.append(
                f"Investigate {eff.generator_name} — "
                f"declining trend detected "
                f"(score: {eff.effectiveness_score:.2f})"
            )

        # Low validation pass rate but high success
        if eff.success_rate > 0.8 and eff.validation_pass_rate < 0.5 and eff.total_executions >= 3:
            recs.append(
                f"Fix validation for {eff.generator_name} — "
                f"executes well ({eff.success_rate:.0%}) but "
                f"validation fails ({eff.validation_pass_rate:.0%})"
            )

    # Check for untested generators (very few executions)
    for eff in effectiveness:
        if eff.total_executions < 2:
            recs.append(
                f"{eff.generator_name} has only "
                f"{eff.total_executions} recorded execution(s) "
                f"— run validation to build confidence"
            )

    if not recs:
        recs.append(
            "All generators performing well. Continue monitoring for regressions."
        )

    return recs


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_learning_report(
    metrics_path: Path | None = None,
) -> LearningReport:
    """Build a comprehensive learning report from all recorded outcomes.

    Loads outcomes, computes effectiveness for every generator, extracts
    patterns, and generates recommendations.

    Args:
        metrics_path: Path to the JSONL file. Defaults to
            `.claude/metrics/generator_learning.jsonl`.

    Returns:
        Frozen LearningReport with all computed data.
    """
    outcomes = load_outcomes(metrics_path)

    if not outcomes:
        return LearningReport(
            generated_at=datetime.now(tz=UTC).isoformat(),
            total_outcomes=0,
            unique_generators=0,
            overall_success_rate=0.0,
            top_generators=(),
            struggling_generators=(),
            patterns=("No outcomes recorded yet.",),
            recommendations=("No generator data available. Run generators to build history.",),
        )

    all_eff = compute_all_effectiveness(outcomes)
    patterns = extract_patterns(outcomes)
    recommendations = generate_recommendations(all_eff)

    unique_names = {o.generator_name for o in outcomes}
    overall_success = sum(1 for o in outcomes if o.success) / len(outcomes)

    top_generators = tuple(all_eff[:10])
    struggling = sorted(all_eff, key=lambda e: e.effectiveness_score)[:5]

    return LearningReport(
        generated_at=datetime.now(tz=UTC).isoformat(),
        total_outcomes=len(outcomes),
        unique_generators=len(unique_names),
        overall_success_rate=round(overall_success, 4),
        top_generators=top_generators,
        struggling_generators=tuple(struggling),
        patterns=tuple(patterns),
        recommendations=tuple(recommendations),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the learning CLI."""
    parser = argparse.ArgumentParser(
        description="Generator Learning System — metrics and insights",
    )
    parser.add_argument(
        "--record",
        type=str,
        default=None,
        help="JSON string of a GeneratorOutcome to record",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Show top N generators by effectiveness score",
    )
    parser.add_argument(
        "--struggling",
        action="store_true",
        help="Show generators needing attention",
    )
    parser.add_argument(
        "--metrics-path",
        type=str,
        default=None,
        help="Path to JSONL metrics file (default: auto)",
    )
    return parser


def _handle_record(raw_json: str, metrics_path: Path | None) -> int:
    """Handle the --record subcommand.

    Args:
        raw_json: JSON string representing a GeneratorOutcome.
        metrics_path: Optional override for metrics file location.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    # Fill defaults for convenience
    data.setdefault("timestamp", datetime.now(tz=UTC).isoformat())
    data.setdefault("session_id", "cli")
    data.setdefault("generator_path", "")
    data.setdefault("action", "generate")
    data.setdefault("success", True)
    data.setdefault("duration_seconds", 0.0)
    data.setdefault("output_loc", 0)

    try:
        outcome = GeneratorOutcome.model_validate(data)
    except Exception as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 1

    record_outcome(outcome, metrics_path)
    print(json.dumps({"status": "recorded", "generator": outcome.generator_name}))
    return 0


def _handle_top(n: int, metrics_path: Path | None) -> int:
    """Handle the --top subcommand.

    Args:
        n: Number of top generators to display.
        metrics_path: Optional override for metrics file location.

    Returns:
        Exit code (always 0).
    """
    outcomes = load_outcomes(metrics_path)
    if not outcomes:
        print(json.dumps({"generators": [], "message": "No data"}))
        return 0

    all_eff = compute_all_effectiveness(outcomes)
    top = all_eff[:n]
    output = [e.model_dump() for e in top]
    print(json.dumps(output, indent=2))
    return 0


def _handle_struggling(metrics_path: Path | None) -> int:
    """Handle the --struggling subcommand.

    Args:
        metrics_path: Optional override for metrics file location.

    Returns:
        Exit code (always 0).
    """
    outcomes = load_outcomes(metrics_path)
    if not outcomes:
        print(json.dumps({"generators": [], "message": "No data"}))
        return 0

    all_eff = compute_all_effectiveness(outcomes)
    struggling = sorted(all_eff, key=lambda e: e.effectiveness_score)[:5]
    output = [e.model_dump() for e in struggling]
    print(json.dumps(output, indent=2))
    return 0


def main() -> int:
    """CLI entry point for the Generator Learning System.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = _build_parser()
    args = parser.parse_args()

    metrics_path = Path(args.metrics_path) if args.metrics_path else None

    if args.record is not None:
        return _handle_record(args.record, metrics_path)

    if args.top is not None:
        return _handle_top(args.top, metrics_path)

    if args.struggling:
        return _handle_struggling(metrics_path)

    # Default: full report
    report = build_learning_report(metrics_path)
    print(json.dumps(report.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    sys.exit(main())
