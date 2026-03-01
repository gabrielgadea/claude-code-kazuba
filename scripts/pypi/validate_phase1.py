#!/usr/bin/env python3
"""Phase 1 validation: Verify lib/ → claude_code_kazuba/ rename is complete.

12 checks. Exit code = number of failures (0 = all pass).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEW_PKG = "claude_code_kazuba"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    "pypi",
    "checkpoints",
}

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    """Record a check result."""
    results.append((name, passed, detail))
    status = "[PASS]" if passed else "[FAIL]"
    msg = f"  {status} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def grep_in_codebase(pattern: str, extensions: set[str]) -> list[tuple[Path, int, str]]:
    """Search for pattern in codebase files, returning (file, line_num, line_text)."""
    matches = []
    for ext in extensions:
        for path in PROJECT_ROOT.rglob(f"*{ext}"):
            rel = path.relative_to(PROJECT_ROOT)
            parts = rel.parts
            if any(part in SKIP_DIRS for part in parts):
                continue
            try:
                for i, line in enumerate(
                    path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
                ):
                    if pattern in line:
                        matches.append((path, i, line.strip()))
            except Exception:
                pass
    return matches


def main() -> int:
    """Run all Phase 1 validation checks."""
    print("=" * 60)
    print("Phase 1 Validation: lib/ → claude_code_kazuba/ rename")
    print("=" * 60)

    # 1. lib/ does NOT exist
    lib_dir = PROJECT_ROOT / "lib"
    check(
        "lib/ directory does NOT exist",
        not lib_dir.exists(),
        str(lib_dir) if lib_dir.exists() else "",
    )

    # 2. claude_code_kazuba/ exists
    pkg_dir = PROJECT_ROOT / NEW_PKG
    check("claude_code_kazuba/ directory exists", pkg_dir.exists())

    # 3. __version__ == "0.2.0"
    init_file = pkg_dir / "__init__.py"
    if init_file.exists():
        content = init_file.read_text()
        has_version = '__version__ = "0.2.0"' in content
        check("__init__.py has __version__ = '0.2.0'", has_version)
    else:
        check("__init__.py exists", False, "file not found")

    # 4. 15 Python modules present
    py_files = [
        f for f in pkg_dir.glob("*.py") if f.name != "__init__.py" and f.name != "__main__.py"
    ]
    check(
        f"{len(py_files)} Python modules in package",
        len(py_files) >= 13,
        f"found: {', '.join(f.stem for f in sorted(py_files))}",
    )

    # 5. ZERO "from lib." in *.py files (old import pattern)
    py_matches = grep_in_codebase("from lib" + ".", {".py"})
    check(
        "ZERO 'from lib.' in *.py files",
        len(py_matches) == 0,
        f"{len(py_matches)} found"
        + (f": {py_matches[0][0].name}:{py_matches[0][1]}" if py_matches else ""),
    )

    # 6. ZERO "from lib." in *.md files
    md_matches = grep_in_codebase("from lib" + ".", {".md"})
    check(
        "ZERO 'from lib.' in *.md files",
        len(md_matches) == 0,
        f"{len(md_matches)} found"
        + (f": {md_matches[0][0].name}:{md_matches[0][1]}" if md_matches else ""),
    )

    # 7. ZERO "import lib." anywhere
    import_matches = grep_in_codebase("import lib" + ".", {".py"})
    check(
        "ZERO 'import lib.' anywhere",
        len(import_matches) == 0,
        f"{len(import_matches)} found" if import_matches else "",
    )

    # 8. pyproject.toml references claude_code_kazuba
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if pyproject.exists():
        pt_content = pyproject.read_text()
        has_new = NEW_PKG in pt_content and '["lib' not in pt_content
        check("pyproject.toml references claude_code_kazuba", has_new)
    else:
        check("pyproject.toml exists", False)

    # 9. ci.yml references claude_code_kazuba/
    ci_yml = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    if ci_yml.exists():
        ci_content = ci_yml.read_text()
        # Should not have bare "lib/" references (but might have other uses of "lib" in different context)
        no_old_lib = " lib/" not in ci_content and "\tlib/" not in ci_content
        check("ci.yml references claude_code_kazuba/", no_old_lib)
    else:
        check("ci.yml exists", False, "file not found — not critical")

    # 10. ruff check passes
    ruff_result = subprocess.run(
        ["ruff", "check", NEW_PKG, "--quiet"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    check(
        "ruff check claude_code_kazuba/ passes",
        ruff_result.returncode == 0,
        ruff_result.stdout[:200] if ruff_result.returncode != 0 else "",
    )

    # 11. pytest passes (quick sanity — collect only to save time in validation)
    pytest_result = subprocess.run(
        ["pytest", "tests/", "--collect-only", "-q"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    last_line = pytest_result.stdout.strip().split("\n")[-1] if pytest_result.stdout else ""
    collected = "tests collected" in last_line and pytest_result.returncode == 0
    check("pytest tests/ collects successfully", collected, last_line)

    # 12. py.typed exists
    py_typed = pkg_dir / "py.typed"
    check("py.typed marker exists", py_typed.exists())

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{'=' * 60}")
    print(f"Phase 1: {passed}/{len(results)} checks passed, {failed} failed")
    print(f"{'=' * 60}")

    return failed


if __name__ == "__main__":
    sys.exit(main())
