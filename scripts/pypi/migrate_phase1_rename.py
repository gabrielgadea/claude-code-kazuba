#!/usr/bin/env python3
"""Phase 1: Rename lib/ to claude_code_kazuba/ and mass-replace imports.

Code-first migration script. Idempotent — safe to run multiple times.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OLD_PKG = "lib"
NEW_PKG = "claude_code_kazuba"
NEW_VERSION = "0.2.0"

# Directories to skip during replacement
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    "scripts/pypi",
}

# File extensions to process
CODE_EXTS = {".py", ".md"}


def run(cmd: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    """Run command with error checking."""
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, **kw)  # type: ignore[arg-type]
    if result.returncode != 0:
        print(f"[FAIL] Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result


def step_git_mv() -> None:
    """Step 1: Rename lib/ to claude_code_kazuba/ via git."""
    old_dir = PROJECT_ROOT / OLD_PKG
    new_dir = PROJECT_ROOT / NEW_PKG
    if new_dir.exists() and not old_dir.exists():
        print("[SKIP] Already renamed")
        return
    if not old_dir.exists():
        print(f"[FAIL] {old_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    run(["git", "mv", OLD_PKG, NEW_PKG])
    print(f"[OK] git mv {OLD_PKG}/ {NEW_PKG}/")


def step_bump_version() -> None:
    """Step 2: Update __version__ in __init__.py."""
    init_file = PROJECT_ROOT / NEW_PKG / "__init__.py"
    content = init_file.read_text()
    new_content = re.sub(
        r'__version__\s*=\s*"[^"]*"',
        f'__version__ = "{NEW_VERSION}"',
        content,
    )
    if content != new_content:
        init_file.write_text(new_content)
        print(f"[OK] Bumped __version__ to {NEW_VERSION}")
    else:
        print(f"[SKIP] Version already {NEW_VERSION}")


def step_create_py_typed() -> None:
    """Step 2b: Create py.typed marker for PEP 561."""
    py_typed = PROJECT_ROOT / NEW_PKG / "py.typed"
    if not py_typed.exists():
        py_typed.touch()
        print("[OK] Created py.typed marker")
    else:
        print("[SKIP] py.typed already exists")


def should_skip(path: Path) -> bool:
    """Check if path should be skipped during replacement."""
    parts = path.relative_to(PROJECT_ROOT).parts
    return any(part in SKIP_DIRS for part in parts)


def step_mass_replace_imports() -> None:
    """Step 3: Replace all 'from claude_code_kazuba.' and 'import claude_code_kazuba.' imports."""
    patterns = [
        (re.compile(r"\bfrom lib\."), f"from {NEW_PKG}."),
        (re.compile(r"\bimport lib\."), f"import {NEW_PKG}."),
        (re.compile(r'"lib\.'), f'"{NEW_PKG}.'),
    ]

    count = 0
    for ext in CODE_EXTS:
        for path in PROJECT_ROOT.rglob(f"*{ext}"):
            if should_skip(path):
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            new_content = content
            for pattern, replacement in patterns:
                new_content = pattern.sub(replacement, new_content)
            if content != new_content:
                path.write_text(new_content, encoding="utf-8")
                count += 1

    print(f"[OK] Replaced imports in {count} files")


def step_update_configs() -> None:
    """Step 4: Update config files that reference 'lib' as path/package."""
    replacements: list[tuple[str, list[tuple[str, str]]]] = [
        (
            "pyproject.toml",
            [
                ('source = ["lib"]', f'source = ["{NEW_PKG}"]'),
                ('include = ["lib*"]', f'include = ["{NEW_PKG}*"]'),
                ("ruff check lib/", f"ruff check {NEW_PKG}/"),
                ("ruff format lib/", f"ruff format {NEW_PKG}/"),
                ("pyright lib/", f"pyright {NEW_PKG}/"),
            ],
        ),
        (
            ".github/workflows/ci.yml",
            [
                ("lib/", f"{NEW_PKG}/"),
            ],
        ),
        (
            ".claude/CLAUDE.md",
            [
                ("--cov=lib", f"--cov={NEW_PKG}"),
                ("ruff check lib/", f"ruff check {NEW_PKG}/"),
                ("ruff format lib/", f"ruff format {NEW_PKG}/"),
                ("pyright lib/", f"pyright {NEW_PKG}/"),
            ],
        ),
        (
            "README.md",
            [
                ("--cov=lib", f"--cov={NEW_PKG}"),
            ],
        ),
    ]

    for rel_path, subs in replacements:
        fpath = PROJECT_ROOT / rel_path
        if not fpath.exists():
            print(f"[WARN] {rel_path} not found, skipping")
            continue
        content = fpath.read_text()
        new_content = content
        for old, new in subs:
            new_content = new_content.replace(old, new)
        if content != new_content:
            fpath.write_text(new_content)
            print(f"[OK] Updated {rel_path}")
        else:
            print(f"[SKIP] {rel_path} already updated")


def main() -> int:
    """Execute Phase 1 migration."""
    print("=" * 60)
    print("Phase 1: Rename lib/ → claude_code_kazuba/")
    print("=" * 60)

    step_git_mv()
    step_bump_version()
    step_create_py_typed()
    step_mass_replace_imports()
    step_update_configs()

    print("\n[DONE] Phase 1 complete. Run validate_phase1.py to verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
