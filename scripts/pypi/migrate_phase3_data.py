#!/usr/bin/env python3
"""Phase 3: Update path references after data relocation.

Replaces:
  'modules/' → 'claude_code_kazuba/data/modules/'
  'core/' → 'claude_code_kazuba/data/core/'
  'presets/' → 'claude_code_kazuba/data/presets/'
in test files, conftest, and config files.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", "__pycache__", ".venv", ".ruff_cache", ".pytest_cache", "dist", "build", "pypi"}

# Path replacements for test fixtures that reference project root paths
# These are string literals in Python code that reference directories relative to PROJECT_ROOT
PATH_REPLACEMENTS = [
    # Quoted path strings in Python
    ('"modules/', '"claude_code_kazuba/data/modules/'),
    ('"modules"', '"claude_code_kazuba/data/modules"'),
    ("'modules/", "'claude_code_kazuba/data/modules/"),
    ("'modules'", "'claude_code_kazuba/data/modules'"),
    # Path concatenation with /
    ('/ "modules"', '/ "claude_code_kazuba" / "data" / "modules"'),
    ('/ "core"', '/ "claude_code_kazuba" / "data" / "core"'),
    ('/ "presets"', '/ "claude_code_kazuba" / "data" / "presets"'),
    # String refs in test assertions
    ('"core/', '"claude_code_kazuba/data/core/'),
    ("'core/", "'claude_code_kazuba/data/core/"),
    ('"presets/', '"claude_code_kazuba/data/presets/'),
    ("'presets/", "'claude_code_kazuba/data/presets/"),
    # project_root / "core"
    ('/ "core"', '/ "claude_code_kazuba" / "data" / "core"'),
]

# Structure test: directory names that moved
STRUCTURE_REPLACEMENTS = [
    # phase_00/test_structure.py REQUIRED_DIRS
    ('"modules",', '"claude_code_kazuba/data/modules",'),
    ('"presets",', '"claude_code_kazuba/data/presets",'),
    ('"core",', '"claude_code_kazuba/data/core",'),
    ('"core/rules",', '"claude_code_kazuba/data/core/rules",'),
]


def should_skip(path: Path) -> bool:
    parts = path.relative_to(PROJECT_ROOT).parts
    return any(part in SKIP_DIRS for part in parts)


def update_test_files() -> int:
    """Update path references in test files."""
    count = 0
    test_dir = PROJECT_ROOT / "tests"
    for path in test_dir.rglob("*.py"):
        if should_skip(path):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        new_content = content

        # Apply path replacements
        for old, new in PATH_REPLACEMENTS:
            new_content = new_content.replace(old, new)

        # Apply structure replacements (only for test_structure.py)
        if path.name == "test_structure.py":
            for old, new in STRUCTURE_REPLACEMENTS:
                new_content = new_content.replace(old, new)

        if content != new_content:
            path.write_text(new_content, encoding="utf-8")
            count += 1
            print(f"  [OK] {path.relative_to(PROJECT_ROOT)}")

    return count


def update_conftest() -> int:
    """Update conftest.py files."""
    count = 0
    for path in (PROJECT_ROOT / "tests").rglob("conftest.py"):
        content = path.read_text()
        new_content = content
        for old, new in PATH_REPLACEMENTS:
            new_content = new_content.replace(old, new)
        if content != new_content:
            path.write_text(new_content)
            count += 1
            print(f"  [OK] {path.relative_to(PROJECT_ROOT)}")
    return count


def main() -> int:
    print("=" * 60)
    print("Phase 3: Update data path references in tests")
    print("=" * 60)

    test_count = update_test_files()
    print(f"[OK] Updated {test_count} test files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
