"""Resolve module dependencies via topological sort."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _parse_yaml_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from MODULE.md content.

    Minimal parser: handles name, dependencies list, and version.
    Does not require pyyaml for simple cases.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    frontmatter = match.group(1)
    result: dict[str, Any] = {}
    collecting_deps = False

    # Parse simple key: value pairs
    for line in frontmatter.splitlines():
        stripped = line.strip()

        # Check if this is a list item continuation
        if stripped.startswith("- ") and collecting_deps:
            dep = stripped[2:].strip().strip('"').strip("'")
            if dep:
                result["dependencies"].append(dep)
            continue

        # Check for top-level key: value
        kv = re.match(r"^(\w[\w-]*)\s*:\s*(.*)", stripped)
        if kv:
            collecting_deps = False  # Any new key stops dependency collection
            key = kv.group(1)
            value = kv.group(2).strip().strip('"').strip("'")
            if key == "dependencies":
                # Could be inline [] or multiline list
                if value.startswith("[") and value.endswith("]"):
                    inner = value[1:-1].strip()
                    if inner:
                        result["dependencies"] = [
                            v.strip().strip('"').strip("'")
                            for v in inner.split(",")
                            if v.strip()
                        ]
                    else:
                        result["dependencies"] = []
                else:
                    result["dependencies"] = []
                    collecting_deps = True
            elif key == "name":
                result["name"] = value
            elif key == "version":
                result["version"] = value
        elif not stripped.startswith("- "):
            # Non-list-item, non-key line: stop collecting
            collecting_deps = False

    return result


def _load_module_info(module_name: str, modules_dir: Path, core_dir: Path) -> dict[str, Any]:
    """Load module info from MODULE.md.

    Args:
        module_name: Name of the module.
        modules_dir: Path to modules/ directory.
        core_dir: Path to core/ directory.

    Returns:
        Parsed frontmatter dict.

    Raises:
        FileNotFoundError: If module MODULE.md doesn't exist.
    """
    if module_name == "core":
        module_md = core_dir / "MODULE.md"
    else:
        module_md = modules_dir / module_name / "MODULE.md"

    if not module_md.exists():
        msg = f"Module not found: {module_name} (no MODULE.md at {module_md})"
        raise FileNotFoundError(msg)

    text = module_md.read_text(encoding="utf-8")
    return _parse_yaml_frontmatter(text)


def resolve_dependencies(
    module_names: list[str],
    modules_dir: Path,
    *,
    core_dir: Path | None = None,
) -> list[str]:
    """Resolve module dependencies in topological order.

    Reads MODULE.md files, builds a dependency graph, and returns
    modules sorted so dependencies come before dependents.

    Args:
        module_names: List of requested module names.
        modules_dir: Path to modules/ directory.
        core_dir: Path to core/ directory (default: modules_dir parent / "core").

    Returns:
        Ordered list of module names (dependencies first).

    Raises:
        FileNotFoundError: If a module doesn't exist.
        ValueError: If a circular dependency is detected.
    """
    if core_dir is None:
        core_dir = modules_dir.parent / "core"

    # Build graph: module_name -> list of dependencies
    graph: dict[str, list[str]] = {}
    to_process = list(module_names)
    processed: set[str] = set()

    while to_process:
        name = to_process.pop(0)
        if name in processed:
            continue
        processed.add(name)

        info = _load_module_info(name, modules_dir, core_dir)
        deps = info.get("dependencies", [])
        graph[name] = deps

        for dep in deps:
            if dep not in processed:
                to_process.append(dep)

    # Topological sort with cycle detection
    resolved: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            msg = f"Circular dependency detected involving: {node}"
            raise ValueError(msg)

        visiting.add(node)
        for dep in graph.get(node, []):
            _visit(dep)
        visiting.remove(node)
        visited.add(node)
        resolved.append(node)

    for name in sorted(graph.keys()):
        _visit(name)

    return resolved


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: resolve_deps.py MODULE [MODULE ...]", file=sys.stderr)
        print("  Reads MODULE.md from modules/ and core/ directories.", file=sys.stderr)
        sys.exit(1)

    project_root = Path(__file__).resolve().parent.parent
    mods_dir = project_root / "modules"
    c_dir = project_root / "core"

    names = sys.argv[1:]
    try:
        order = resolve_dependencies(names, mods_dir, core_dir=c_dir)
        for m in order:
            print(m)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
