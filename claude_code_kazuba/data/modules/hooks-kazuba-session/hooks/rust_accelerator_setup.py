#!/usr/bin/env python3
"""
Rust Accelerator Auto-Setup Hook (SessionStart)

Automatically ensures complete Rust acceleration is available at session start.
Includes: claude_learning_kernel (PyO3), rlm-cli, and rlm-hooks binaries.

Hook Type: SessionStart
Execution: Once per session (uses installation marker)
Performance Target: <15s for installation, <100ms for check

Features:
- Automatic detection and installation of PyO3 bindings
- RLM CLI and hooks binary verification
- Uses maturin develop for reliable venv installation
- Graceful degradation (never blocks session)
- Complete Rust ecosystem activation
"""

from __future__ import annotations

import functools
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Resolve tool paths once to satisfy S607 (partial executable path)
_CARGO_CMD = shutil.which("cargo") or "cargo"


@dataclass
class RustStatus:
    """Status of Rust components."""

    pyo3_available: bool
    pyo3_version: str
    rlm_cli_available: bool
    rlm_hooks_available: bool
    message: str

    @property
    def fully_operational(self) -> bool:
        """Check if all components are operational."""
        return self.pyo3_available and self.rlm_cli_available and self.rlm_hooks_available


@functools.lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Get the project root directory. Cached -- called multiple times."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).parent.parent.parent.parent))


@functools.lru_cache(maxsize=1)
def get_venv_python() -> Path:
    """Get the virtualenv Python path. Cached -- called multiple times."""
    project_root = get_project_root()
    for venv_name in [".venv", "venv", ".env"]:
        venv_python = project_root / venv_name / "bin" / "python"
        if venv_python.exists():
            return venv_python
    return Path(sys.executable)


def check_pyo3_module() -> tuple[bool, str]:
    """Check if claude_learning_kernel PyO3 module is available."""
    try:
        venv_python = get_venv_python()
        result = subprocess.run(
            [
                str(venv_python),
                "-c",
                "import claude_learning_kernel; print(claude_learning_kernel.__version__)",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()[:200]
    except Exception as e:
        return False, str(e)[:200]


def check_rlm_binaries() -> tuple[bool, bool]:
    """Check if RLM CLI and hooks binaries are available."""
    project_root = get_project_root()
    bin_dir = project_root / ".claude" / "bin"

    rlm_cli = bin_dir / "rlm-cli"
    rlm_hooks = bin_dir / "rlm-hooks"

    cli_ok = rlm_cli.exists() and os.access(rlm_cli, os.X_OK)
    hooks_ok = rlm_hooks.exists() and os.access(rlm_hooks, os.X_OK)

    return cli_ok, hooks_ok


def find_maturin() -> Path | None:
    """Find maturin executable."""
    locations = [
        Path.home() / ".local" / "bin" / "maturin",
        Path.home() / ".cargo" / "bin" / "maturin",
        Path("/usr/local/bin/maturin"),
        Path("/usr/bin/maturin"),
    ]
    for loc in locations:
        if loc.exists():
            return loc
    maturin_path = shutil.which("maturin")
    if maturin_path:
        return Path(maturin_path)
    return None


def install_pyo3_module() -> tuple[bool, str]:
    """Install claude_learning_kernel using maturin develop."""
    project_root = get_project_root()
    rust_core = project_root / ".claude" / "rust-core"

    if not rust_core.exists():
        return False, f"rust-core not found at {rust_core}"

    maturin = find_maturin()
    if not maturin:
        return False, "maturin not found"

    try:
        # Use maturin develop for direct venv installation
        result = subprocess.run(
            [str(maturin), "develop", "--release"],
            cwd=str(rust_core),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "VIRTUAL_ENV": str(project_root / ".venv")},
        )

        if result.returncode != 0:
            return False, result.stderr[-300:]

        # Verify
        available, version = check_pyo3_module()
        if available:
            return True, version
        return False, "Installation verification failed"

    except subprocess.TimeoutExpired:
        return False, "Build timed out"
    except Exception as e:
        return False, str(e)[:200]


def build_rlm_binaries() -> tuple[bool, str]:
    """Build RLM CLI and hooks binaries."""
    project_root = get_project_root()
    crates_dir = project_root / ".claude" / "crates"
    bin_dir = project_root / ".claude" / "bin"

    if not crates_dir.exists():
        return False, f"crates not found at {crates_dir}"

    try:
        # Build with cargo
        result = subprocess.run(
            [_CARGO_CMD, "build", "--release"],
            cwd=str(crates_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            return False, result.stderr[-300:]

        # Copy binaries
        bin_dir.mkdir(parents=True, exist_ok=True)
        release_dir = crates_dir / "target" / "release"

        for binary in ["rlm-cli", "rlm-hooks"]:
            src = release_dir / binary
            dst = bin_dir / binary
            if src.exists():
                shutil.copy2(src, dst)
                dst.chmod(0o755)

        cli_ok, hooks_ok = check_rlm_binaries()
        if cli_ok and hooks_ok:
            return True, "Binaries installed"
        return False, "Binary copy failed"

    except subprocess.TimeoutExpired:
        return False, "Build timed out"
    except Exception as e:
        return False, str(e)[:200]


def get_full_status() -> RustStatus:
    """Get complete Rust acceleration status."""
    pyo3_ok, pyo3_info = check_pyo3_module()
    cli_ok, hooks_ok = check_rlm_binaries()

    components = []
    if pyo3_ok:
        components.append(f"PyO3 v{pyo3_info}")
    if cli_ok:
        components.append("rlm-cli")
    if hooks_ok:
        components.append("rlm-hooks")

    if components:
        message = ", ".join(components)
    else:
        message = "No components available"

    return RustStatus(
        pyo3_available=pyo3_ok,
        pyo3_version=pyo3_info if pyo3_ok else "",
        rlm_cli_available=cli_ok,
        rlm_hooks_available=hooks_ok,
        message=message,
    )


def main() -> None:
    """Main entry point."""
    status = get_full_status()

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "",
        }
    }

    if status.fully_operational:
        output["hookSpecificOutput"]["additionalContext"] = f"[RustAccelerator] ✓ Ready ({status.message})"
        print(json.dumps(output))
        return

    # Try to install missing components
    installed = []
    errors = []

    if not status.pyo3_available:
        success, msg = install_pyo3_module()
        if success:
            installed.append(f"PyO3 v{msg}")
        else:
            errors.append(f"PyO3: {msg}")

    if not status.rlm_cli_available or not status.rlm_hooks_available:
        success, msg = build_rlm_binaries()
        if success:
            installed.append("RLM binaries")
        else:
            errors.append(f"RLM: {msg}")

    # Build result message
    if installed and not errors:
        output["hookSpecificOutput"]["additionalContext"] = f"[RustAccelerator] ✓ Installed: {', '.join(installed)}"
    elif installed:
        output["hookSpecificOutput"]["additionalContext"] = (
            f"[RustAccelerator] Partial: {', '.join(installed)} | Errors: {'; '.join(errors)}"
        )
    else:
        project_root = get_project_root()
        output["hookSpecificOutput"]["additionalContext"] = (
            f"[RustAccelerator] Fallback Python.\n"
            f"Manual install:\n"
            f"  cd {project_root}/.claude/rust-core && maturin develop --release\n"
            f"  cd {project_root}/.claude/crates && cargo build --release\n"
            f"Errors: {'; '.join(errors)}"
        )

    print(json.dumps(output))


if __name__ == "__main__":
    main()
