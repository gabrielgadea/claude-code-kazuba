"""Generator Library — catalog, search, and quality scoring for ACO N1 generators.

Standalone module (no dependency on base_generator.py) that discovers, catalogs,
and scores all gen_*.py generators in the codebase. Designed for hook consumption,
CLI usage, and programmatic access.

Usage:
    python scripts/aco/generators/library.py              # JSON catalog to stdout
    python scripts/aco/generators/library.py --search dspy # filtered results
    python scripts/aco/generators/library.py --scattered   # list scattered generators
    python scripts/aco/generators/library.py --scores      # generators sorted by quality
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CANONICAL_PATH = "scripts/aco/generators"

# ---------------------------------------------------------------------------
# Tag classification rules
# ---------------------------------------------------------------------------

_TAG_RULES: tuple[tuple[str, str], ...] = (
    ("dspy", "dspy"),
    ("agent", "agent"),
    ("pipeline", "pipeline"),
    ("swarm", "swarm"),
    ("phase", "phase"),
    ("hook", "hook"),
    ("perception", "perception"),
    ("metric", "metrics"),
    ("validator", "validator"),
    ("evolution", "evolution"),
    ("gitnexus", "gitnexus"),
    ("serena", "serena"),
    ("tantivy", "tantivy"),
    ("cognitive", "cognitive"),
    ("planner", "planner"),
    ("ecc", "ecc"),
    ("compact", "compact"),
    ("observer", "observer"),
    ("training", "training"),
    ("cache", "cache"),
    ("goal", "goal"),
    ("kb", "knowledge-base"),
    ("indexer", "knowledge-base"),
)

# Generator ID patterns found in docstrings: (G3), G-CKI, G0, etc.
_GID_PATTERN = re.compile(
    r"\(G(\d+)\)|^G(\d+)[:\s]|^G-([A-Z]+)[:\s]",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class GeneratorMeta(BaseModel, frozen=True):
    """Metadata for a single ACO generator file."""

    name: str
    path: str
    description: str
    generator_id: str
    loc: int
    has_execute_source: bool
    has_dry_run: bool
    has_force: bool
    triad_complete: bool
    imports: tuple[str, ...]
    output_dir: str | None
    created_date: str | None
    tags: tuple[str, ...]


class GeneratorCatalog(BaseModel, frozen=True):
    """Full catalog of all discovered generators."""

    version: str
    generated_at: str
    canonical_path: str
    total_generators: int
    total_loc: int
    generators: tuple[GeneratorMeta, ...]
    scattered: tuple[str, ...]
    tag_summary: dict[str, int]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _extract_docstring(source: str) -> str:
    """Extract first line of module docstring from source code.

    Args:
        source: Python source code.

    Returns:
        First meaningful line of the docstring, or empty string.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""

    docstring = ast.get_docstring(tree)
    if not docstring:
        return ""

    first_line = docstring.split("\n")[0].strip()
    return first_line


def _extract_generator_id(docstring_first_line: str, filename: str) -> str:
    """Extract generator ID from docstring or auto-generate from filename.

    Patterns recognized:
      - '(G3)' -> 'G3'
      - 'G0: ...' -> 'G0'
      - 'G-CKI: ...' -> 'G-CKI'

    Falls back to auto-generated ID from filename stem.

    Args:
        docstring_first_line: First line of the module docstring.
        filename: The generator filename (e.g., 'gen_phase_agent.py').

    Returns:
        Generator ID string.
    """
    match = _GID_PATTERN.search(docstring_first_line)
    if match:
        # Groups: (G3) -> group 1, G0: -> group 2, G-CKI: -> group 3
        if match.group(1):
            return f"G{match.group(1)}"
        if match.group(2):
            return f"G{match.group(2)}"
        if match.group(3):
            return f"G-{match.group(3)}"

    # Auto-generate from filename: gen_phase_agent.py -> AUTO-phase-agent
    stem = filename.removesuffix(".py").removeprefix("gen_")
    return f"AUTO-{stem.replace('_', '-')}"


def _extract_imports(source: str) -> tuple[str, ...]:
    """Extract non-stdlib import module names from source.

    Args:
        source: Python source code.

    Returns:
        Tuple of top-level external package names.
    """
    _STDLIB_TOP = sys.stdlib_module_names | {"__future__", "_thread"}

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()

    external: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in _STDLIB_TOP:
                    external.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                top = node.module.split(".")[0]
                if top not in _STDLIB_TOP:
                    external.add(top)

    return tuple(sorted(external))


def _extract_output_dir(source: str) -> str | None:
    """Extract _OUTPUT_DIR value from source if defined.

    Args:
        source: Python source code.

    Returns:
        The string representation of the output dir, or None.
    """
    match = re.search(
        r"_OUTPUT_DIR\s*=\s*(.+?)$",
        source,
        re.MULTILINE,
    )
    if not match:
        return None
    raw = match.group(1).strip()
    # Try to extract a readable path from common patterns
    # e.g., _PROJECT_ROOT / ".claude" / "agents" / "phase"
    parts = re.findall(r'"([^"]+)"', raw)
    if parts:
        return "/".join(parts)
    return raw


def _classify_tags(filename: str) -> tuple[str, ...]:
    """Auto-classify tags from generator filename.

    Args:
        filename: The generator filename stem (without .py).

    Returns:
        Tuple of tag strings.
    """
    lower = filename.lower()
    tags: list[str] = []
    for pattern, tag in _TAG_RULES:
        if pattern in lower:
            tags.append(tag)
    return tuple(sorted(set(tags)))


def _get_file_created_date(filepath: Path) -> str | None:
    """Get file creation date from mtime (git log is too slow for batch).

    Args:
        filepath: Path to the file.

    Returns:
        ISO date string or None.
    """
    try:
        mtime = filepath.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y-%m-%d")
    except OSError:
        return None


def _check_triad(filepath: Path) -> bool:
    """Check if matching validate_*.py and rollback_*.py exist.

    Naming convention:
      gen_X.py -> validators/val_X.py + rollbacks/rb_X.py

    Args:
        filepath: Path to the generator file.

    Returns:
        True if both validator and rollback exist.
    """
    stem = filepath.stem  # e.g., gen_phase_agent
    name_part = stem.removeprefix("gen_")  # e.g., phase_agent

    project_root = filepath.resolve().parents[3]
    val_path = project_root / "scripts" / "aco" / "validators" / f"val_{name_part}.py"
    rb_path = project_root / "scripts" / "aco" / "rollbacks" / f"rb_{name_part}.py"

    return val_path.exists() and rb_path.exists()


# ---------------------------------------------------------------------------
# Core discovery functions
# ---------------------------------------------------------------------------


def _extract_meta_from_file(filepath: Path, project_root: Path) -> GeneratorMeta:
    """Extract full metadata from a single generator file.

    Args:
        filepath: Absolute path to the generator file.
        project_root: Absolute path to the project root.

    Returns:
        GeneratorMeta with all fields populated.
    """
    source = filepath.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    loc = len(lines)

    docstring_line = _extract_docstring(source)
    generator_id = _extract_generator_id(docstring_line, filepath.name)
    imports = _extract_imports(source)
    output_dir = _extract_output_dir(source)
    tags = _classify_tags(filepath.stem)
    triad = _check_triad(filepath)
    created = _get_file_created_date(filepath)

    rel_path = str(filepath.relative_to(project_root))

    return GeneratorMeta(
        name=filepath.stem,
        path=rel_path,
        description=docstring_line,
        generator_id=generator_id,
        loc=loc,
        has_execute_source="_EXECUTE_SOURCE" in source,
        has_dry_run="--dry-run" in source or "dry_run" in source,
        has_force="--force" in source,
        triad_complete=triad,
        imports=imports,
        output_dir=output_dir,
        created_date=created,
        tags=tags,
    )


def discover_generators(project_root: Path) -> list[GeneratorMeta]:
    """Discover all generators in the canonical path.

    Globs scripts/aco/generators/gen_*.py and extracts metadata from each.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        List of GeneratorMeta, sorted by name.
    """
    canonical = project_root / _CANONICAL_PATH
    if not canonical.is_dir():
        logger.warning("Canonical generator path not found: %s", canonical)
        return []

    generators: list[GeneratorMeta] = []
    for filepath in sorted(canonical.glob("gen_*.py")):
        if filepath.name == "library.py":
            continue  # skip self
        try:
            meta = _extract_meta_from_file(filepath, project_root)
            generators.append(meta)
        except Exception:
            logger.exception("Failed to extract metadata from %s", filepath)

    return generators


def discover_scattered(project_root: Path) -> list[str]:
    """Find gen_*.py files outside the canonical path.

    Searches the entire scripts/ directory tree and reports generators
    that are not in scripts/aco/generators/.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        List of relative paths to scattered generators, sorted.
    """
    scripts_dir = project_root / "scripts"
    if not scripts_dir.is_dir():
        return []

    canonical = project_root / _CANONICAL_PATH
    scattered: list[str] = []

    for filepath in sorted(scripts_dir.rglob("gen_*.py")):
        if filepath.is_relative_to(canonical):
            continue

        rel = str(filepath.relative_to(project_root))
        scattered.append(rel)

    return scattered


def build_catalog(project_root: Path) -> GeneratorCatalog:
    """Build a complete catalog of all generators.

    Combines canonical discovery + scattered discovery + tag summary.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Frozen GeneratorCatalog with all metadata.
    """
    generators = discover_generators(project_root)
    scattered = discover_scattered(project_root)

    # Compute tag summary
    tag_counts: dict[str, int] = {}
    for gen in generators:
        for tag in gen.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    total_loc = sum(g.loc for g in generators)

    return GeneratorCatalog(
        version="1.0.0",
        generated_at=datetime.now(tz=UTC).isoformat(),
        canonical_path=_CANONICAL_PATH,
        total_generators=len(generators),
        total_loc=total_loc,
        generators=tuple(generators),
        scattered=tuple(scattered),
        tag_summary=dict(sorted(tag_counts.items())),
    )


# ---------------------------------------------------------------------------
# Search and scoring
# ---------------------------------------------------------------------------


def search_generators(
    catalog: GeneratorCatalog,
    query: str,
) -> list[GeneratorMeta]:
    """Search generators by name, description, or tags.

    Performs case-insensitive substring matching across name, description,
    tags, and generator_id. Results are ranked by number of field matches.

    Args:
        catalog: The generator catalog to search.
        query: Search query string.

    Returns:
        List of matching GeneratorMeta, sorted by relevance (most matches first).
    """
    q = query.lower()
    scored: list[tuple[int, GeneratorMeta]] = []

    for gen in catalog.generators:
        hits = 0
        if q in gen.name.lower():
            hits += 2  # name match is worth more
        if q in gen.description.lower():
            hits += 1
        if q in gen.generator_id.lower():
            hits += 2
        if any(q in tag.lower() for tag in gen.tags):
            hits += 1
        if any(q in imp.lower() for imp in gen.imports):
            hits += 1

        if hits > 0:
            scored.append((hits, gen))

    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [gen for _, gen in scored]


def score_generator(meta: GeneratorMeta) -> float:
    """Compute quality score for a generator (0.0 to 1.0).

    Scoring weights:
      - LOC in reasonable range 100-800: 0.4
      - triad_complete: 0.3
      - has_dry_run: 0.1
      - has_force: 0.1
      - description quality (non-empty, >20 chars): 0.1

    Args:
        meta: Generator metadata to score.

    Returns:
        Quality score between 0.0 and 1.0.
    """
    score = 0.0

    # LOC score (0.4 weight): optimal 100-800, penalize outside range
    if 100 <= meta.loc <= 800:
        score += 0.4
    elif meta.loc > 0:
        # Partial credit for being close to range
        if meta.loc < 100:
            score += 0.4 * (meta.loc / 100.0)
        else:
            # Above 800: gradual penalty, floor at 0.1
            penalty = min((meta.loc - 800) / 1600.0, 0.75)
            score += 0.4 * (1.0 - penalty)

    # Triad complete (0.3 weight)
    if meta.triad_complete:
        score += 0.3

    # Dry run support (0.1 weight)
    if meta.has_dry_run:
        score += 0.1

    # Force support (0.1 weight)
    if meta.has_force:
        score += 0.1

    # Description quality (0.1 weight)
    if len(meta.description) > 20:
        score += 0.1
    elif meta.description:
        score += 0.05

    return round(min(score, 1.0), 4)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_scores_table(
    generators: list[GeneratorMeta],
) -> str:
    """Format generators with scores as an aligned table.

    Args:
        generators: List of generator metadata.

    Returns:
        Formatted table string.
    """
    rows: list[tuple[str, str, float, bool, str]] = []
    for g in generators:
        s = score_generator(g)
        rows.append((g.name, g.generator_id, s, g.triad_complete, g.description[:50]))

    rows.sort(key=lambda r: -r[2])

    lines = [
        f"{'Name':<42} {'ID':<12} {'Score':>5} {'Triad':>5} Description",
        "-" * 120,
    ]
    for name, gid, sc, triad, desc in rows:
        t = "YES" if triad else "no"
        lines.append(f"{name:<42} {gid:<12} {sc:>5.2f} {t:>5} {desc}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the Generator Library.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success).
    """
    parser = argparse.ArgumentParser(
        description="ACO Generator Library — catalog, search, and score generators.",
    )
    parser.add_argument(
        "--search",
        type=str,
        default=None,
        help="Search generators by name, description, or tags.",
    )
    parser.add_argument(
        "--scattered",
        action="store_true",
        help="List generators outside the canonical path.",
    )
    parser.add_argument(
        "--scores",
        action="store_true",
        help="Show generators sorted by quality score.",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Project root override (default: auto-detect).",
    )

    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else _PROJECT_ROOT

    catalog = build_catalog(root)

    if args.scattered:
        if catalog.scattered:
            print(json.dumps(list(catalog.scattered), indent=2))
        else:
            print("No scattered generators found.")
        return 0

    if args.search:
        results = search_generators(catalog, args.search)
        if results:
            output = [g.model_dump(mode="json") for g in results]
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(f"No generators matching '{args.search}'.")
        return 0

    if args.scores:
        print(_format_scores_table(list(catalog.generators)))
        print(f"\nTotal: {catalog.total_generators} generators, {catalog.total_loc} LOC")
        return 0

    # Default: full catalog as JSON
    print(json.dumps(catalog.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    sys.exit(main())
