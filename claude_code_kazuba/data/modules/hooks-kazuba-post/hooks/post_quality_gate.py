#!/usr/bin/env python3
"""
Post Quality Gate - Claude Code PostToolUse Hook

6-stage quality validation pipeline with parallel execution.
Validates result after PRE-hook auto-fix and provides action plan guidance.

Hook Phase: PostToolUse (after Write, Edit, MultiEdit)
Exit Codes: 0 (PASS) | Non-zero (FAIL)
"""

import concurrent.futures
import importlib
import importlib.util
import json
import os
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

# Consolidated path setup for module imports (quality, hooks, common, qa, .claude)
_script_dir = Path(__file__).resolve().parent
_h = _script_dir.parent
sys.path[:0] = list(map(str, [_script_dir, _h, _h / "common", _h / "qa", _h.parent]))

# Import modular components (required)
from commands import (  # noqa: E402
    infra_cmds_for,
    node_format_cmds_for,
    node_lint_cmds_for,
    node_test_cmds_for,
    node_typecheck_cmds_for,
    py_format_cmds_for,
    py_test_cmds_for,
    py_typecheck_cmds_for,
    pylance_cmds_for,
)
from common.cache import ResultCache  # noqa: E402
from common.config import (  # noqa: E402
    AI_DIR,
    BACKEND_DIR,
    FAIL_FAST,
    FRONTEND_DIR,
    PACKAGES_DIR,
    PARALLEL,
    PROJECT_ROOT,
    RUN_TESTS,
    STANDALONE,
    STRICT,
    VERBOSE,
    WARN_ONLY,
)
from common.output import OutputBuffer  # noqa: E402
from common.utils import ext, is_subpath, run_with_cache  # noqa: E402

# Optional: error pattern extractor for learning system
extract_and_store_errors: Any = None
HAS_ERROR_EXTRACTOR = False
try:
    from error_pattern_extractor import extract_and_store_errors as _extract_fn

    extract_and_store_errors = _extract_fn
    HAS_ERROR_EXTRACTOR = True
except ImportError:
    pass

# Optional: QA Loop module for auto-fix
QALoopOrchestrator: Any = None
get_metrics: Any = None
QAConfig: Any = None
StageIssue: Any = None
IssueCategory: Any = None
HAS_QA_LOOP = False
try:
    # QA module paths already in consolidated path setup above
    #
    #
    from qa.config import IssueCategory as _IssueCategory
    from qa.config import QAConfig as _QAConfig
    from qa.config import StageIssue as _StageIssue
    from qa.qa_loop_orchestrator import QALoopOrchestrator as _QALoopOrchestrator
    from qa.qa_metrics import get_metrics as _get_metrics

    QALoopOrchestrator = _QALoopOrchestrator
    get_metrics = _get_metrics
    QAConfig = _QAConfig
    StageIssue = _StageIssue
    IssueCategory = _IssueCategory
    HAS_QA_LOOP = True
except ImportError:
    pass


# Fallback logger (always defined, may be overridden by hook_logger)
class FallbackLogger:
    """Minimal logger fallback."""

    def __init__(self, name: str) -> None:
        self.name = name

    def info(self, msg: str, **_kw: Any) -> None:
        print(f"[INFO] {msg}")

    def debug(self, msg: str, **_kw: Any) -> None:
        if os.environ.get("DEBUG", "0") == "1":
            print(f"[DEBUG] {msg}")

    def warning(self, msg: str, **_kw: Any) -> None:
        print(f"[WARN] {msg}")

    def error(self, msg: str, **_kw: Any) -> None:
        print(f"[ERROR] {msg}")

    def critical(self, msg: str, **_kw: Any) -> None:
        print(f"[CRITICAL] {msg}")
        if "exception" in _kw:
            traceback.print_exc()

    def start_execution(self, evt: dict[str, Any]) -> None:
        self.info(f"Starting execution for event: {evt.get('hook_event_name', 'unknown')}")

    def end_execution(self, success: bool, msg: str) -> None:
        self.info(f"Execution {'SUCCESS' if success else 'FAILED'}: {msg}")


def _fallback_create_logger(name: str) -> FallbackLogger:
    return FallbackLogger(name)


def _fallback_read_event() -> dict[str, Any]:
    """Fallback event reader."""
    for source in [
        lambda: os.environ.get("CLAUDE_HOOK_EVENT", ""),
        lambda: sys.stdin.read() if not sys.stdin.isatty() else "",
        *[lambda a=a: a for a in sys.argv[1:]],
    ]:
        try:
            raw = source()
            if raw and raw.strip():
                evt = json.loads(raw)
                if isinstance(evt, dict):
                    return evt
        except Exception:
            pass
    return {}


create_hook_logger = _fallback_create_logger
safe_read_hook_event = _fallback_read_event

# Try to load centralized logging system
try:
    # Hook logger paths already in consolidated setup (see path setup for details)
    #
    #
    #
    spec = importlib.util.find_spec("hook_logger")
    if spec is not None:
        _mod = importlib.import_module("hook_logger")
        create_hook_logger = _mod.create_hook_logger
        safe_read_hook_event = _mod.safe_read_hook_event
except Exception:
    pass

INFRA_DIR = PROJECT_ROOT / "infrastructure"

# Initialize logger
logger = create_hook_logger("post_quality_gate_v4")

# Global instances
output_buffer = OutputBuffer()
result_cache = ResultCache()

CommandSpec = tuple[list[str], Path, str, Path]


def regulatory_cmds_for(file: Path) -> list[list[str]]:
    """ANTT Regulatory compliance validation commands (Stage 7)"""
    cmds: list[list[str]] = []

    # Check if this is an ANTT document requiring regulatory validation
    # Applies to: markdown files in analise/, VOTO files, RELATORIO files
    file_str = str(file)

    is_antt_doc = (
        # Markdown files in analise/ directory
        ("analise/" in file_str and ext(file) == ".md")
        or
        # Vote documents
        ("VOTO" in file_str.upper() and ext(file) in (".md", ".docx"))
        or
        # Report documents
        ("RELATORIO" in file_str.upper() and ext(file) in (".md", ".docx"))
        or ("RELATÓRIO" in file_str.upper() and ext(file) in (".md", ".docx"))
        or
        # Process analysis files
        ("processo" in file_str.lower() and ext(file) == ".md")
        or
        # Nota técnica files
        ("nota" in file_str.lower() and "tecnica" in file_str.lower() and ext(file) == ".md")
    )

    if is_antt_doc:
        # Use antt_document_validator.py hook for regulatory compliance
        validator_path = PROJECT_ROOT / ".claude" / "hooks" / "validation" / "antt_document_validator.py"

        if validator_path.exists():
            # Call validator with Write tool and file path
            # Validator will check: citation accuracy, process metadata, obligatory sections
            cmds.append(["python3", str(validator_path), "Write", str(file)])
        elif STRICT:
            cmds.append(["__MISSING__", "antt_document_validator.py"])

    return cmds


# ---------- Smart Execution System ----------


def process_pylance_output(json_output: str, file: Path) -> str:
    """Process Pylance/Pyright JSON output into readable format"""
    try:
        result = json.loads(json_output)
        diagnostics = result.get("generalDiagnostics", [])

        if not diagnostics:
            return "No specific errors reported"

        error_lines = []
        error_count = 0
        warning_count = 0

        for diag in diagnostics[:20]:  # Limit to 20 most important
            severity = diag.get("severity", "error")
            message = diag.get("message", "Unknown error")
            rule = diag.get("rule", "")

            # Extract line/column info
            range_info = diag.get("range", {})
            start_info = range_info.get("start", {})
            line = start_info.get("line", 0) + 1  # Convert 0-based to 1-based
            column = start_info.get("character", 0) + 1

            if severity == "error":
                error_count += 1
                prefix = "❌"
            elif severity == "warning":
                warning_count += 1
                prefix = "⚠️"
            else:
                prefix = "ℹ️"

            rule_suffix = f" [{rule}]" if rule else ""
            error_lines.append(f"{prefix} L{line}:{column} {message}{rule_suffix}")

        if len(diagnostics) > 20:
            error_lines.append(f"... and {len(diagnostics) - 20} more issues")

        summary = []
        if error_count:
            summary.append(f"{error_count} errors")
        if warning_count:
            summary.append(f"{warning_count} warnings")

        header = f"Pylance found {', '.join(summary)}:"
        return f"{header}\n" + "\n".join(error_lines)

    except json.JSONDecodeError:
        # Fallback to raw output if JSON parsing fails
        return f"Pylance output parsing failed. Raw error:\n{json_output[:500]}"
    except Exception as e:
        return f"Error processing Pylance output: {e!s}"


def execute_command_batch(commands: list[CommandSpec]) -> bool:
    """Execute commands with smart output control"""
    ok = True

    def process_command(args: CommandSpec) -> bool:
        cmd, cwd, label, file = args

        # Handle missing tools
        if cmd and cmd[0] == "__MISSING__":
            tool = cmd[1]
            msg = f"Required tool '{tool}' not found"

            if STRICT or tool in ("ruff", "mypy", "eslint", "prettier", "tsc", "pyright"):
                output_buffer.add_error(label, str(file), msg, is_critical=True)
                return False
            else:
                output_buffer.add_warning(f"{label}: {msg}")
                return True

        # Run command with cache
        rc, out, err = run_with_cache(cmd, cwd, file)

        if rc == 0:
            output_buffer.add_info(f"{label} ✅ {file.name}")
            return True
        else:
            # Determine criticality
            is_critical = label in ("mypy", "tsc", "pytest", "pylance") and rc > 1

            # Special handling for Pylance/Pyright JSON output
            if label == "pylance" and out:
                error_msg = process_pylance_output(out, file)
            else:
                error_msg = (err or out or f"Exit {rc}").strip()

            output_buffer.add_error(label, str(file.relative_to(PROJECT_ROOT)), error_msg, is_critical)

            # Check fail-fast
            if output_buffer.should_fail_fast():
                output_buffer.add_warning(f"Stopping after {FAIL_FAST} critical errors")
                return False

            return False

    # Execute with parallelization
    if PARALLEL and len(commands) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures: list[concurrent.futures.Future] = []

            for cmd_args in commands:
                if output_buffer.should_fail_fast():
                    break

                future = executor.submit(process_command, cmd_args)
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                try:
                    if not future.result():
                        ok = False
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    ok = False

                if output_buffer.should_fail_fast():
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break
    else:
        for cmd_args in commands:
            if output_buffer.should_fail_fast():
                break

            if not process_command(cmd_args):
                ok = False

    return ok


def execute_for(files: list[Path]) -> bool:
    """Execute quality checks with smart batching"""
    ok = True

    # Group commands by type
    format_commands: list[CommandSpec] = []
    lint_commands: list[CommandSpec] = []
    typecheck_commands: list[CommandSpec] = []
    pylance_commands: list[CommandSpec] = []
    test_commands: list[CommandSpec] = []
    infra_commands: list[CommandSpec] = []
    regulatory_commands: list[CommandSpec] = []  # NEW: Stage 7

    # Detect if all modified files are backend-only (apps/backend or apps/ai-service)
    # If true, skip TypeScript checks to avoid false positives from frontend errors
    all_backend = all(
        is_subpath(f, BACKEND_DIR) or is_subpath(f, AI_DIR)
        for f in files
        if not any(part in {"node_modules", ".git", ".venv", "venv", ".mypy_cache", ".ruff_cache"} for part in f.parts)
    )

    if all_backend and files:
        print("ℹ️ Backend-only changes detected - skipping TypeScript checks")

    for f in files:
        # Skip vendor dirs
        if any(part in {"node_modules", ".git", ".venv", "venv", ".mypy_cache", ".ruff_cache"} for part in f.parts):
            continue

        # Node/TypeScript (skip if all changes are backend-only)
        if not all_backend and (is_subpath(f, FRONTEND_DIR) or is_subpath(f, PACKAGES_DIR)):
            cwd = FRONTEND_DIR if is_subpath(f, FRONTEND_DIR) else PROJECT_ROOT

            format_commands.extend((cmd, cwd, "prettier", f) for cmd in node_format_cmds_for(f))
            lint_commands.extend((cmd, cwd, "eslint", f) for cmd in node_lint_cmds_for(f))
            typecheck_commands.extend((cmd, cwd, "tsc", f) for cmd in node_typecheck_cmds_for(f))
            test_commands.extend((cmd, cwd, "vitest", f) for cmd in node_test_cmds_for(f))

        # Python
        if is_subpath(f, BACKEND_DIR) or is_subpath(f, AI_DIR):
            app_root = BACKEND_DIR if is_subpath(f, BACKEND_DIR) else AI_DIR

            format_commands.extend((cmd, app_root, "ruff", f) for cmd in py_format_cmds_for(f))
            typecheck_commands.extend((cmd, app_root, "mypy", f) for cmd in py_typecheck_cmds_for(f))
            pylance_commands.extend((cmd, app_root, "pylance", f) for cmd in pylance_cmds_for(f))
            test_commands.extend((cmd, app_root, "pytest", f) for cmd in py_test_cmds_for(f))

        # Infrastructure
        if is_subpath(f, INFRA_DIR):
            infra_commands.extend((cmd, PROJECT_ROOT, "infra", f) for cmd in infra_cmds_for(f))

        # STAGE 7: ANTT Regulatory Compliance (NEW)
        # Applies to all files (validator will filter ANTT documents internally)
        regulatory_commands.extend((cmd, PROJECT_ROOT, "regulatory", f) for cmd in regulatory_cmds_for(f))

    # Execute batches with progress indicators
    stages: list[tuple[str, list[CommandSpec]]] = []
    if format_commands:
        stages.append(("🎨 Formatting", format_commands))
    if lint_commands:
        stages.append(("🔍 Linting", lint_commands))
    if typecheck_commands:
        stages.append(("🔎 Type Checking", typecheck_commands))
    if pylance_commands:
        stages.append(("🔬 Pylance Analysis", pylance_commands))
    if RUN_TESTS and test_commands:
        stages.append(("🧪 Testing", test_commands))
    if infra_commands:
        stages.append(("🏗️ Infrastructure", infra_commands))
    if regulatory_commands:
        stages.append(("⚖️ Regulatory Compliance", regulatory_commands))

    for stage_name, commands in stages:
        if not commands:
            continue

        print(f"{stage_name}...", end="", flush=True)

        if execute_command_batch(commands):
            print(" ✅")
        else:
            print(" ❌")
            ok = False

        if output_buffer.should_fail_fast():
            print("⛔ Fail-fast triggered")
            break

    return ok


# ---------- Hook Event Processing ----------


def read_event() -> dict[str, Any]:
    """Read and parse hook event."""
    return safe_read_hook_event()


def extract_files(evt: dict[str, Any]) -> list[Path]:
    """Extract file paths from event"""
    files: list[str] = []
    ti = evt.get("tool_input") or {}
    tr = evt.get("tool_response") or {}

    # Single path keys
    for key in ("file_path", "path", "target_path", "filePath", "targetPath"):
        v = ti.get(key) or tr.get(key)
        if isinstance(v, str):
            files.append(v)

    # Arrays
    for key in ("files", "file_paths", "paths"):
        v = ti.get(key) or tr.get(key)
        if isinstance(v, list):
            files.extend([p for p in v if isinstance(p, str)])

    # Edits array
    if "edits" in ti:
        edits = ti.get("edits", [])
        if isinstance(edits, list):
            files.extend(edit["file_path"] for edit in edits if isinstance(edit, dict) and "file_path" in edit)

    # De-duplicate and resolve
    out: list[Path] = []
    seen: set[Path] = set()

    for f in files:
        try:
            p = Path(f).resolve()
            if p not in seen and p.exists():
                out.append(p)
                seen.add(p)
        except (ValueError, OSError):
            continue

    return out


# ---------- Standalone Mode for Testing ----------


def standalone_mode() -> int:
    """Run in standalone mode with test files"""
    print("🧪 Running in STANDALONE mode")

    # Look for test files in current directory or specified paths
    test_files: list[Path] = []

    # Check for command-line specified files
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.exists():
                test_files.append(p.resolve())

    # If no files specified, scan current directory
    if not test_files:
        print("Scanning for code files in current directory...")
        for pattern in ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"]:
            test_files.extend(Path.cwd().glob(pattern))

    if not test_files:
        print("ℹ️ No files to check in standalone mode")
        print("Usage: python post_quality_gate_fixed.py [file1] [file2] ...")
        return 0

    print(f"Found {len(test_files)} file(s) to check")

    # Execute checks
    ok = execute_for(test_files)

    # Show results
    print("-" * 50)
    summary = output_buffer.get_summary()
    print(summary)

    return 0 if ok or WARN_ONLY else 2


# ---------- Main Entry Point ----------


def capture_error_patterns_for_learning(files: list[Path]) -> None:
    """
    Extract and store error patterns for learning system (H1).

    Processes errors from OutputBuffer and stores them in .cipher/error_patterns/
    for future retrieval by the knowledge system.
    """
    if not HAS_ERROR_EXTRACTOR:
        return

    # Map stage tool names to stage identifiers
    stage_map = {
        "prettier": "format",
        "ruff": "lint",
        "eslint": "lint",
        "tsc": "types",
        "mypy": "types",
        "pylance": "types",
        "pyright": "types",
        "pytest": "tests",
        "vitest": "tests",
        "hadolint": "infra",
        "yamllint": "infra",
    }

    # Group errors by file
    errors_by_file: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for error in output_buffer.errors:
        file_path = error.get("file", "")
        tool = error.get("tool", "unknown")
        message = error.get("message", "")

        if file_path and message:
            errors_by_file[file_path].append((tool, message))

    # Extract and store patterns for each file
    extracted_count = 0
    for file_path, file_errors in errors_by_file.items():
        # Combine all error messages for this file
        combined_output = "\n\n".join([f"[{tool}] {msg}" for tool, msg in file_errors])

        # Determine stage (use first tool, or "unknown")
        stage = "unknown"
        if file_errors:
            first_tool = file_errors[0][0].lower()
            for tool_name, stage_name in stage_map.items():
                if tool_name in first_tool:
                    stage = stage_name
                    break

        try:
            # Call error_pattern_extractor
            result = extract_and_store_errors(file_path=file_path, errors_output=combined_output, error_stage=stage)

            if result.get("success"):
                extracted_count += 1
                logger.debug(
                    f"Extracted error pattern: {result.get('pattern_id')} "
                    f"with {len(result.get('error_codes', []))} error codes"
                )
        except Exception as e:
            logger.warning(f"Failed to extract error pattern for {file_path}: {e}")

    if extracted_count > 0:
        logger.info(f"Captured {extracted_count} error patterns for learning system")


_TOOL_CATEGORY_MAP: dict[str, str] = {
    "prettier": "FORMAT",
    "ruff": "LINT",
    "eslint": "LINT",
    "tsc": "TYPE",
    "mypy": "TYPE",
    "pylance": "TYPE",
    "pyright": "TYPE",
    "pytest": "TEST",
    "vitest": "TEST",
    "hadolint": "LINT",
    "yamllint": "LINT",
}

_TOOL_STAGE_MAP: dict[str, str] = {
    "prettier": "format",
    "ruff": "lint",
    "eslint": "lint",
    "tsc": "types",
    "mypy": "types",
    "pylance": "pylance",
    "pyright": "pylance",
    "pytest": "tests",
    "vitest": "tests",
    "hadolint": "infra",
    "yamllint": "infra",
}


def _errors_to_stage_issues(errors: list[dict[str, Any]]) -> list[Any]:
    """Convert output_buffer errors to StageIssue objects."""
    if not HAS_QA_LOOP:
        return []

    issues: list[Any] = []
    for error in errors:
        tool = error.get("tool", "unknown").lower()

        category_name = "LINT"
        for tool_name, cat_name in _TOOL_CATEGORY_MAP.items():
            if tool_name in tool:
                category_name = cat_name
                break
        category = getattr(IssueCategory, category_name, IssueCategory.LINT)

        stage = "lint"
        for tool_name, stg in _TOOL_STAGE_MAP.items():
            if tool_name in tool:
                stage = stg
                break

        fixable = category_name in ("FORMAT", "LINT", "IMPORT")
        issues.append(
            StageIssue(
                stage=stage,
                category=category,
                file_path=error.get("file", ""),
                line=0,
                column=0,
                message=error.get("message", "")[:500],
                severity="error" if error.get("is_critical", False) else "warning",
                fixable=fixable,
            )
        )
    return issues


def run_qa_auto_fix_loop(files: list[Path]) -> tuple[bool, Any]:
    """Run QA auto-fix loop on detected issues. Returns (success, loop_result)."""
    if not HAS_QA_LOOP:
        logger.warning("QA Loop module not available - skipping auto-fix")
        return False, None

    issues = _errors_to_stage_issues(output_buffer.errors)
    if not issues:
        logger.info("No issues to auto-fix")
        return True, None

    logger.info(f"Starting QA Auto-Fix Loop with {len(issues)} issues...")
    print(f"\n🔧 Stage 7: QA Auto-Fix Loop ({len(issues)} issues)")
    print("-" * 50)

    config = QAConfig(
        auto_fix=True,
        max_iterations=3,
        ruff_fix=True,
        ruff_format=True,
        import_fix=True,
        type_suggest=True,
    )

    def validate_after_fix() -> list[Any]:
        """Re-run quality checks and return remaining issues."""
        global output_buffer
        output_buffer = OutputBuffer()
        execute_for(files)
        return _errors_to_stage_issues(output_buffer.errors)

    try:
        orchestrator = QALoopOrchestrator(config)
        result = orchestrator.run(issues, validator=validate_after_fix)

        metrics = get_metrics()
        metrics.record_session(result)

        status_emoji = {"pass": "✅", "improved": "📈", "no_improvement": "⚠️", "failed": "❌"}
        emoji = status_emoji.get(result.status, "❓")

        print(f"\n{emoji} QA Loop Result: {result.status.upper()}")
        print(f"   Iterations: {result.iterations_completed}/{config.max_iterations}")
        print(f"   Initial issues: {result.initial_issues}")
        print(f"   Final issues: {result.final_issues}")
        print(f"   Fixes applied: {result.total_fixes_applied}")
        print(f"   Success rate: {result.fix_success_rate:.1%}")

        if result.recommendations:
            print("\n📋 Recommendations:")
            for rec in result.recommendations[:5]:
                print(f"   - {rec}")

        logger.info(
            f"QA Loop completed: {result.status} "
            f"({result.initial_issues}->{result.final_issues} issues, "
            f"{result.fix_success_rate:.1%} success rate)"
        )

        return result.status in ("pass", "improved"), result

    except Exception as e:
        logger.error(f"QA Loop failed: {e}")
        print(f"\n❌ QA Loop error: {e}")
        return False, None


def main() -> int:
    """Main entry point."""
    try:
        if STANDALONE or os.environ.get("CLAUDE_QGATE_TEST", "0") == "1":
            return standalone_mode()

        start_time = time.time()
        evt = read_event()

        if not evt:
            if "--test" in sys.argv:
                print("ℹ️ Test mode - hook is operational")
            else:
                logger.warning("Empty event received")
            return 0

        logger.start_execution(evt)

        if evt.get("hook_event_name") != "PostToolUse":
            return 0

        if evt.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
            return 0

        files = extract_files(evt)
        if not files:
            logger.end_execution(True, "No files to process")
            return 0

        print(f"🚀 Quality Gate - Checking {len(files)} file(s)")
        print("-" * 50)

        ok = execute_for(files)
        elapsed = time.time() - start_time

        cache_stats = result_cache.get_stats()
        if cache_stats:
            print(cache_stats)

        print("-" * 50)

        summary = output_buffer.get_summary()

        if WARN_ONLY:
            print(summary)
            print(f"\n⏱️ Completed in {elapsed:.1f}s (WARN_ONLY mode)")
            logger.end_execution(True, f"WARN_ONLY - {output_buffer.error_counts.total()} issues")
            return 0

        if ok:
            print("✅ All quality checks passed!")
            if VERBOSE:
                print(summary)
            print(f"\n⏱️ Completed in {elapsed:.1f}s")
            logger.end_execution(True, f"Passed in {elapsed:.1f}s")
            return 0

        # QA auto-fix loop
        if HAS_QA_LOOP and output_buffer.error_counts.total() > 0:
            qa_success, qa_result = run_qa_auto_fix_loop(files)

            if qa_success and qa_result:
                elapsed = time.time() - start_time
                summary = output_buffer.get_summary()

                if qa_result.status == "pass":
                    print("\n" + "=" * 50)
                    print("✅ All quality issues auto-fixed!")
                    print(f"\n⏱️ Completed in {elapsed:.1f}s (with auto-fix)")
                    logger.end_execution(True, f"Passed after auto-fix in {elapsed:.1f}s")
                    return 0

                if qa_result.status == "improved":
                    print("\n" + "=" * 50)
                    print(f"📈 Auto-fix improved issues ({qa_result.initial_issues}->{qa_result.final_issues})")

        # Failed
        print(summary)
        print("\n❌ Quality checks failed")
        print(f"⏱️ Completed in {elapsed:.1f}s")

        try:
            capture_error_patterns_for_learning(files)
        except Exception as e:
            logger.warning(f"Error pattern extraction failed: {e}")

        logger.end_execution(False, f"Failed - {output_buffer.error_counts.total()} errors")
        return 2

    except Exception as e:
        logger.critical("Unexpected error", exception=e)
        print(f"Unexpected error: {e}")
        if os.environ.get("DEBUG", "0") == "1":
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
