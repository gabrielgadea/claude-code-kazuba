# Claude Code Kazuba — Project Config

## About
Framework de configuração de excelência para Claude Code. Módulos reutilizáveis de hooks, skills, agents e commands.

## Stack
- Python 3.12+ | Pydantic v2 | pytest | ruff | pyright
- Checkpoints: msgpack (.toon format)
- Templates: Jinja2

## Commands
```bash
source .venv/bin/activate
pytest tests/ --cov=claude_code_kazuba --cov-report=term-missing  # Run tests
ruff check claude_code_kazuba/ tests/ scripts/                     # Lint
ruff format claude_code_kazuba/ tests/ scripts/                    # Format
pyright claude_code_kazuba/                                        # Type check
python scripts/generate_plan.py --validate          # Regenerate plan
python plans/validation/validate_all.py             # Validate all phases
```

## Rules
- TDD: write tests BEFORE implementation, 90% coverage PER FILE (not average)
- All dataclasses: `frozen=True`
- All files: `from __future__ import annotations` first
- Type hints: modern syntax `list[T]`, `T | None` (not `List[T]`, `Optional[T]`)
- Hooks: ALWAYS fail-open (exit 0 on error). Exit 2 = block.
- Comments: English for code, Portuguese for user-facing docs

## Module Structure
Each module in `modules/` has:
- `MODULE.md` — manifest with name, description, dependencies
- Content dirs (`hooks/`, `skills/`, `agents/`, `commands/`, `config/`, `contexts/`)
- `settings.hooks.json` — hook registration fragment (for installer merge)

## Meta-Code-First Principle
Plans and structured artifacts are generated via Python scripts, not written manually.
Change data in Python → regenerate → validate.
