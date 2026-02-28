#!/usr/bin/env python3
"""
Validation Script — Phase 6: Skills + Agents + Commands

Verifies all deliverables, runs tests, checks coverage, saves checkpoint.
Exit 0 = PASS, Exit 1 = FAIL
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import msgpack
except ImportError:
    msgpack = None  # type: ignore[assignment]

PHASE_ID = 6
PHASE_TITLE = "Skills + Agents + Commands"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)

EXPECTED_FILES = [
    "modules/skills-meta/MODULE.md",
"modules/skills-meta/skills/hook-master/SKILL.md",
"modules/skills-meta/skills/skill-master/SKILL.md",
"modules/skills-meta/skills/skill-writer/SKILL.md",
"modules/skills-dev/MODULE.md",
"modules/skills-dev/skills/verification-loop/SKILL.md",
"modules/skills-dev/skills/supreme-problem-solver/SKILL.md",
"modules/skills-dev/skills/eval-harness/SKILL.md",
"modules/skills-planning/MODULE.md",
"modules/skills-planning/skills/plan-amplifier/SKILL.md",
"modules/skills-planning/skills/plan-execution/SKILL.md",
"modules/skills-research/MODULE.md",
"modules/skills-research/skills/academic-research-writer/SKILL.md",
"modules/skills-research/skills/literature-review/SKILL.md",
"modules/agents-dev/MODULE.md",
"modules/agents-dev/agents/code-reviewer.md",
"modules/agents-dev/agents/security-auditor.md",
"modules/agents-dev/agents/meta-orchestrator.md",
"modules/commands-dev/MODULE.md",
"modules/commands-dev/commands/debug-RCA.md",
"modules/commands-dev/commands/smart-commit.md",
"modules/commands-dev/commands/orchestrate.md",
"modules/commands-dev/commands/verify.md",
"modules/commands-prp/MODULE.md",
"modules/commands-prp/commands/prp-base-create.md",
"modules/commands-prp/commands/prp-base-execute.md",
"modules/commands-prp/commands/shared/quality-patterns.yml",
"modules/commands-prp/commands/shared/security-patterns.yml"
]
MIN_LINES = {"modules/skills-meta/MODULE.md": 20, "modules/skills-meta/skills/hook-master/SKILL.md": 200, "modules/skills-meta/skills/skill-master/SKILL.md": 200, "modules/skills-meta/skills/skill-writer/SKILL.md": 100, "modules/skills-dev/MODULE.md": 20, "modules/skills-dev/skills/verification-loop/SKILL.md": 100, "modules/skills-dev/skills/supreme-problem-solver/SKILL.md": 120, "modules/skills-dev/skills/eval-harness/SKILL.md": 80, "modules/skills-planning/MODULE.md": 20, "modules/skills-planning/skills/plan-amplifier/SKILL.md": 150, "modules/skills-planning/skills/plan-execution/SKILL.md": 120, "modules/skills-research/MODULE.md": 20, "modules/skills-research/skills/academic-research-writer/SKILL.md": 100, "modules/skills-research/skills/literature-review/SKILL.md": 80, "modules/agents-dev/MODULE.md": 20, "modules/agents-dev/agents/code-reviewer.md": 60, "modules/agents-dev/agents/security-auditor.md": 60, "modules/agents-dev/agents/meta-orchestrator.md": 80, "modules/commands-dev/MODULE.md": 20, "modules/commands-dev/commands/debug-RCA.md": 60, "modules/commands-dev/commands/smart-commit.md": 40, "modules/commands-dev/commands/orchestrate.md": 60, "modules/commands-dev/commands/verify.md": 40, "modules/commands-prp/MODULE.md": 20, "modules/commands-prp/commands/prp-base-create.md": 60, "modules/commands-prp/commands/prp-base-execute.md": 60, "modules/commands-prp/commands/shared/quality-patterns.yml": 30, "modules/commands-prp/commands/shared/security-patterns.yml": 30}
TEST_DIR = "tests/phase_06/"
MIN_COVERAGE = 90


def check_files_exist() -> list[str]:
    """Verify all expected files exist and meet minimum line counts."""
    errors: list[str] = []
    for fpath in EXPECTED_FILES:
        full = BASE_DIR / fpath
        if not full.exists():
            errors.append(f"MISSING: {fpath}")
            continue
        lines = len(full.read_text().splitlines())
        min_l = MIN_LINES.get(fpath, 1)
        if lines < min_l:
            errors.append(f"TOO_SHORT: {fpath} ({lines} < {min_l} lines)")
    return errors


def run_tests() -> dict:
    """Run pytest with coverage for this phase."""
    test_path = BASE_DIR / TEST_DIR
    if not test_path.exists():
        return {"status": "SKIP", "reason": f"Test dir {TEST_DIR} not found"}

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", str(test_path),
            "--tb=short", "-q",
            f"--cov={BASE_DIR / 'lib'}",
            "--cov-report=json:coverage.json",
            f"--cov-fail-under={MIN_COVERAGE}",
        ],
        capture_output=True, text=True, cwd=str(BASE_DIR),
    )

    cov_data = {}
    cov_file = BASE_DIR / "coverage.json"
    if cov_file.exists():
        cov_data = json.loads(cov_file.read_text())
        cov_file.unlink()

    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "returncode": result.returncode,
        "stdout": result.stdout[-500:] if result.stdout else "",
        "stderr": result.stderr[-500:] if result.stderr else "",
        "coverage": cov_data.get("totals", {}).get("percent_covered", 0),
    }


def run_lint() -> dict:
    """Run ruff check on lib/ directory."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(BASE_DIR / "lib"), "--quiet"],
        capture_output=True, text=True, cwd=str(BASE_DIR),
    )
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "errors": result.stdout.strip() if result.stdout else "",
    }


def run_typecheck() -> dict:
    """Run pyright on lib/ directory."""
    result = subprocess.run(
        [sys.executable, "-m", "pyright", str(BASE_DIR / "lib"), "--outputjson"],
        capture_output=True, text=True, cwd=str(BASE_DIR),
    )
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "output": result.stdout[-300:] if result.stdout else "",
    }


def save_checkpoint(results: dict) -> Path:
    """Save checkpoint in .toon format (msgpack)."""
    checkpoint = {
        "phase_id": PHASE_ID,
        "phase_title": PHASE_TITLE,
        "timestamp": time.time(),
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
        "version": "2.0",
    }

    path = CHECKPOINT_DIR / f"phase_{PHASE_ID:02d}.toon"
    if msgpack is not None:
        path.write_bytes(msgpack.packb(checkpoint, use_bin_type=True))
    else:
        # Fallback: JSON with .toon extension
        path.write_text(json.dumps(checkpoint, indent=2, default=str))

    return path


def main() -> int:
    print(f"\n============================================================")
    print(f"  Phase {PHASE_ID} Validation: {PHASE_TITLE}")
    print(f"============================================================\n")

    results: dict = {"phase": PHASE_ID, "checks": {}}
    all_pass = True

    # Check 1: Files exist
    file_errors = check_files_exist()
    results["checks"]["files"] = {
        "status": "PASS" if not file_errors else "FAIL",
        "total": len(EXPECTED_FILES),
        "missing": len(file_errors),
        "errors": file_errors,
    }
    if file_errors:
        all_pass = False
        for e in file_errors:
            print(f"  [FAIL] {e}")
    else:
        print(f"  [PASS] All {len(EXPECTED_FILES)} files present")

    # Check 2: Tests
    test_results = run_tests()
    results["checks"]["tests"] = test_results
    if test_results["status"] == "FAIL":
        all_pass = False
        print(f"  [FAIL] Tests failed (coverage: {test_results.get('coverage', 'N/A')}%)")
    elif test_results["status"] == "SKIP":
        print(f"  [SKIP] {test_results['reason']}")
    else:
        print(f"  [PASS] Tests passed (coverage: {test_results.get('coverage', 'N/A')}%)")

    # Check 3: Lint
    lint_results = run_lint()
    results["checks"]["lint"] = lint_results
    if lint_results["status"] == "FAIL":
        all_pass = False
        print(f"  [FAIL] Lint errors found")
    else:
        print(f"  [PASS] Lint clean")

    # Check 4: Type check
    type_results = run_typecheck()
    results["checks"]["typecheck"] = type_results
    if type_results["status"] == "FAIL":
        print(f"  [WARN] Type check issues (non-blocking)")
    else:
        print(f"  [PASS] Type check clean")

    # Save checkpoint
    results["overall"] = "PASS" if all_pass else "FAIL"
    cp_path = save_checkpoint(results)
    print(f"\n  Checkpoint: {cp_path}")

    print(f"\n  Overall: {results['overall']}")
    print(f"============================================================\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
