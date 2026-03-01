#!/usr/bin/env python3
"""Phase 2: Move installer scripts into claude_code_kazuba.installer package.

Replaces 'from scripts.X' imports with 'from claude_code_kazuba.installer.X'.
Also updates install.sh inline Python blocks.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", "__pycache__", ".venv", ".ruff_cache", ".pytest_cache", "dist", "build", "pypi"}

# Map of old → new import prefixes
REPLACEMENTS = [
    ("from scripts.detect_stack", "from claude_code_kazuba.installer.detect_stack"),
    ("from scripts.resolve_deps", "from claude_code_kazuba.installer.resolve_deps"),
    ("from scripts.install_module", "from claude_code_kazuba.installer.install_module"),
    ("from scripts.merge_settings", "from claude_code_kazuba.installer.merge_settings"),
    ("from scripts.validate_installation", "from claude_code_kazuba.installer.validate_installation"),
]


def should_skip(path: Path) -> bool:
    parts = path.relative_to(PROJECT_ROOT).parts
    return any(part in SKIP_DIRS for part in parts)


def step_replace_imports() -> None:
    """Replace 'from scripts.X' imports in .py files."""
    count = 0
    for path in PROJECT_ROOT.rglob("*.py"):
        if should_skip(path):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        new_content = content
        for old, new in REPLACEMENTS:
            new_content = new_content.replace(old, new)
        if content != new_content:
            path.write_text(new_content, encoding="utf-8")
            count += 1
            print(f"  [OK] {path.relative_to(PROJECT_ROOT)}")
    print(f"[OK] Replaced imports in {count} Python files")


def step_update_install_sh() -> None:
    """Update inline Python blocks in install.sh."""
    install_sh = PROJECT_ROOT / "install.sh"
    if not install_sh.exists():
        print("[WARN] install.sh not found")
        return
    content = install_sh.read_text()
    new_content = content
    for old, new in REPLACEMENTS:
        new_content = new_content.replace(old, new)
    if content != new_content:
        install_sh.write_text(new_content)
        print("[OK] Updated install.sh")
    else:
        print("[SKIP] install.sh already updated")


def main() -> int:
    print("=" * 60)
    print("Phase 2: Replace 'from scripts.' imports")
    print("=" * 60)
    step_replace_imports()
    step_update_install_sh()
    print("\n[DONE] Phase 2 import replacement complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
