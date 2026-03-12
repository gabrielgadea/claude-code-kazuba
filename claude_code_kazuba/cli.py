"""CLI entry point: kazuba install/validate/list-presets/list-modules/build-rust.

IMPORTANT: kazuba install is a COMPLEMENT to the user's existing Claude Code
configuration. It MERGES content (hooks, skills, agents, etc.) on top of the
user's existing .claude/ setup. It NEVER replaces or overwrites existing files
unless they are explicitly managed by kazuba modules.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def _lazy_version() -> str:
    """Lazy import to avoid loading pydantic/jinja2 for --version."""
    from claude_code_kazuba import __version__

    return __version__


def cmd_install(args: argparse.Namespace) -> int:
    """Install modules to target project."""
    from claude_code_kazuba.data.paths import get_core_dir, get_data_dir, get_modules_dir, get_presets_dir
    from claude_code_kazuba.installer.detect_stack import detect_stack
    from claude_code_kazuba.installer.install_module import install_module
    from claude_code_kazuba.installer.resolve_deps import resolve_dependencies
    from claude_code_kazuba.installer.validate_installation import validate_installation

    target = Path(args.target).resolve()
    if args.preset:
        preset_file = get_presets_dir() / f"{args.preset}.txt"
        if not preset_file.exists():
            print(f"Error: unknown preset '{args.preset}'", file=sys.stderr)
            available = [f.stem for f in get_presets_dir().glob("*.txt")]
            print(f"Available: {', '.join(sorted(available))}", file=sys.stderr)
            return 1
        module_names = [
            line.strip() for line in preset_file.read_text().splitlines() if line.strip() and not line.startswith("#")
        ]
    else:
        module_names = [m.strip() for m in args.modules.split(",")]

    # Load optional TOML sidecar for domain config (e.g. cila_router keywords)
    toml_config: dict[str, Any] = {}
    if args.preset:
        import tomllib

        toml_file = get_presets_dir() / f"{args.preset}.toml"
        if toml_file.exists():
            toml_config = tomllib.loads(toml_file.read_text())

    stack_vars = detect_stack(target)
    if "cila_router" in toml_config:
        stack_vars["cila_router_config"] = toml_config["cila_router"]
    if "project" in toml_config:
        stack_vars["project_config"] = toml_config["project"]

    ordered = resolve_dependencies(module_names, get_modules_dir(), core_dir=get_core_dir())

    if args.dry_run:
        print(f"Would install {len(ordered)} module(s): {', '.join(ordered)}")
        return 0

    source_dir = get_data_dir()
    for mod_name in ordered:
        result = install_module(mod_name, source_dir, target, stack_vars)
        copied = len(result.get("copied", []))
        merged = len(result.get("merged", []))
        rendered = len(result.get("rendered", []))
        print(f"  [OK] {mod_name}: {copied} copied, {merged} merged, {rendered} rendered")

    validation = validate_installation(target)
    if validation.get("all_passed"):
        print(f"\nAll {len(ordered)} modules installed successfully!")
        return 0
    print("\nWarning: some validation checks did not pass.", file=sys.stderr)
    return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate an existing installation."""
    from claude_code_kazuba.installer.validate_installation import validate_installation

    target = Path(args.target).resolve()
    results = validate_installation(target)
    return 0 if results.get("all_passed") else 1


def cmd_list_presets(_: argparse.Namespace) -> int:
    """List available presets."""
    from claude_code_kazuba.data.paths import get_presets_dir

    for f in sorted(get_presets_dir().glob("*.txt")):
        modules = [line.strip() for line in f.read_text().splitlines() if line.strip()]
        print(f"  {f.stem}: {', '.join(modules)}")
    return 0


def cmd_list_modules(_: argparse.Namespace) -> int:
    """List available modules."""
    from claude_code_kazuba.data.paths import get_modules_dir

    for d in sorted(get_modules_dir().iterdir()):
        if (d / "MODULE.md").exists():
            print(f"  {d.name}")
    return 0


def cmd_build_rust(args: argparse.Namespace) -> int:
    """Build Rust core from source in target project."""
    import glob
    import subprocess

    target = Path(args.target).resolve()
    rust_dir = target / ".claude" / "rust-core"
    if not rust_dir.exists():
        print(f"Error: {rust_dir} does not exist", file=sys.stderr)
        print("Install a preset with aco-rust-core first.", file=sys.stderr)
        return 1

    (target / ".claude" / "bin").mkdir(parents=True, exist_ok=True)

    print(f"Building Rust core in {rust_dir}...")
    build_result = subprocess.run(
        ["maturin", "build", "--features", "python", "--release"],
        cwd=rust_dir,
        capture_output=True,
        text=True,
    )
    if build_result.returncode != 0:
        print(f"maturin build failed:\n{build_result.stderr}", file=sys.stderr)
        return 1
    print("  [OK] maturin build --release")

    wheels = glob.glob(str(rust_dir / "target" / "wheels" / "*.whl"))
    if not wheels:
        print("Error: no wheel found after build", file=sys.stderr)
        return 1
    wheel = sorted(wheels)[-1]
    install_result = subprocess.run(
        ["pip", "install", "--user", "--force-reinstall", "--break-system-packages", wheel],
        capture_output=True,
        text=True,
    )
    if install_result.returncode != 0:
        print(f"pip install failed:\n{install_result.stderr}", file=sys.stderr)
        return 1
    print(f"  [OK] installed {Path(wheel).name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for kazuba command."""
    parser = argparse.ArgumentParser(
        prog="kazuba",
        description="Claude Code Kazuba — Excellence Configuration Framework",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_lazy_version()}")
    sub = parser.add_subparsers(dest="command")

    p_install = sub.add_parser("install", help="Install modules to target project")
    grp = p_install.add_mutually_exclusive_group(required=True)
    grp.add_argument(
        "--preset",
        choices=["minimal", "standard", "professional", "enterprise", "research", "full-stack", "lexcore"],
    )
    grp.add_argument("--modules", help="Comma-separated module names")
    p_install.add_argument("--target", default=".", help="Target project directory (default: .)")
    p_install.add_argument("--dry-run", action="store_true", help="Show plan without installing")
    p_install.set_defaults(func=cmd_install)

    p_validate = sub.add_parser("validate", help="Validate an existing installation")
    p_validate.add_argument("target", nargs="?", default=".", help="Target project directory")
    p_validate.set_defaults(func=cmd_validate)

    sub.add_parser("list-presets", help="List available presets").set_defaults(func=cmd_list_presets)
    sub.add_parser("list-modules", help="List available modules").set_defaults(func=cmd_list_modules)

    p_build_rust = sub.add_parser("build-rust", help="Build Rust core from source in target project")
    p_build_rust.add_argument("--target", default=".", help="Target project directory")
    p_build_rust.set_defaults(func=cmd_build_rust)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
