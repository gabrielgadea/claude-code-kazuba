# Code Style Rules

Universal code style guidelines. Apply to all languages unless a
language-specific module overrides a particular rule.

---

## Naming Conventions

- **Variables and functions**: Use descriptive, intention-revealing names.
  - Prefer `user_count` over `n`, `calculate_total_price` over `calc`.
  - Boolean variables start with `is_`, `has_`, `can_`, `should_`.
  - Avoid abbreviations unless universally understood (e.g., `id`, `url`, `api`).
- **Classes and types**: PascalCase. Noun or noun phrase (`UserAccount`, `HttpClient`).
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`).
- **Files**: kebab-case or snake_case depending on language convention.
- **Consistency**: Within a project, one convention. Never mix.

---

## File Organization

- **One concern per file.** A file should have a single, clear responsibility.
- **Group related files** in directories by feature or domain, not by type.
  - Prefer `auth/handler.py`, `auth/models.py` over `handlers/auth.py`, `models/auth.py`.
- **Keep files under 300 lines.** If longer, consider splitting.
- **Entry points at top level.** Main modules, CLI entrypoints, and `__init__.py` stay at package root.
- **Tests mirror source structure.** `src/auth/handler.py` -> `tests/auth/test_handler.py`.

---

## Comment Guidelines

- **Code comments**: English preferred for maintainability across teams.
- **User-facing documentation**: Native language of the target audience.
- **Comment the WHY, not the WHAT.** Code should be self-documenting for the "what."
  - Bad: `# increment counter` / Good: `# retry up to 3 times to handle transient network errors`
- **Docstrings on all public functions** — parameters, return values, exceptions.
- **TODO comments**: Include context — `# TODO(author): description — issue #123`
- **Remove commented-out code.** Use version control instead.

---

## Import Ordering

Imports are organized in three groups, separated by blank lines:

1. **Standard library** — `os`, `sys`, `pathlib`, `json`, etc.
2. **Third-party packages** — `pydantic`, `jinja2`, `pytest`, etc.
3. **Local/project imports** — `from lib.config import ...`, `from .models import ...`

Within each group, sort alphabetically. Use an automated formatter
(e.g., `isort`, `ruff`) to enforce this.

---

## Code Structure

- **Early returns** over deep nesting. Guard clauses first.
- **Small functions**: Each function does one thing. Under 25 lines preferred.
- **Explicit over implicit.** Avoid magic numbers, implicit conversions, hidden side effects.
- **Type hints everywhere** (Python). Use modern syntax: `list[T]`, `T | None`.
- **Immutable by default.** Use `frozen=True` for dataclasses, `const` where available.
- **No over-engineering.** If YAGNI (You Aren't Gonna Need It), don't build it.
  The simplest solution meeting current requirements wins.

---

## Formatting

- Use automated formatters. Never argue about style — automate it.
- Consistent indentation: 4 spaces for Python, 2 spaces for YAML/JSON/JS.
- Line length: 99 characters (configurable per project).
- Trailing commas in multi-line collections (prevents noisy diffs).
- One blank line between functions, two between top-level classes.
