# claude-code-kazuba

[![CI](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Modular configuration framework for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).
Reusable hooks, skills, agents, commands, and presets that make Claude Code better
at writing code, safer with secrets, and smarter with context.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/gabrielgadea/claude-code-kazuba.git
cd claude-code-kazuba

# 2. Choose a preset
cat presets/standard.txt   # See what's included

# 3. Install into your project
python scripts/install.py --preset standard --target /path/to/your/project
```

The installer resolves dependencies, renders templates, registers hooks, and
sets up your `.claude/` directory with everything the preset includes.

## What You Get

### Hooks — Automated Quality Gates

| Hook | Event | What it does |
|------|-------|-------------|
| Prompt Enhancer | UserPromptSubmit | Classifies intent and injects cognitive techniques |
| Secrets Scanner | PreToolUse | Blocks API keys, tokens, credentials in code |
| PII Scanner | PreToolUse | Detects CPF, CNPJ, SSN, email, phone numbers |
| Bash Safety | PreToolUse | Blocks `rm -rf /`, `chmod 777`, `curl\|bash`, fork bombs |
| Quality Gate | PreToolUse | File size limits, debug code detection |
| CILA Router | UserPromptSubmit | L0-L6 complexity classification for smart routing |
| Status Monitor | SessionStart | Reports environment info at session start |
| Auto Compact | PreCompact | Saves checkpoint before context compaction |
| Knowledge Manager | PreToolUse | 3-tier context injection |
| Compliance Tracker | PostToolUse | Tool usage audit logging |

### Skills — Structured Workflows

| Skill | Purpose |
|-------|---------|
| Verification Loop | 6-phase pre-PR verification |
| Plan Amplifier | 8-dimension plan amplification |
| Plan Execution | 6-phase execution with checkpoints |
| Hook Master | Create and debug Claude Code hooks |
| Skill Master | Create skills with proper structure |
| Academic Research Writer | IEEE citations, 7-step workflow |

### Agents — Specialist Roles

| Agent | Model | Purpose |
|-------|-------|---------|
| Code Reviewer | Sonnet | Bugs, security, performance, style review |
| Security Auditor | Sonnet | OWASP Top 10, secrets, PII, dependency audit |
| Meta Orchestrator | Opus | Create Claude Code infrastructure |

### Commands — Slash Commands

| Command | Purpose |
|---------|---------|
| `/debug-RCA` | Structured 6-step Root Cause Analysis |
| `/smart-commit` | Intelligent commit with generated message |
| `/orchestrate` | Multi-agent orchestration |
| `/verify` | Pre-PR verification loop |
| `/prp-base-create` | Create Product Requirements Prompt |
| `/prp-base-execute` | Execute a PRP |

## Module Catalog

14 modules organized by category:

| Category | Modules | Description |
|----------|---------|-------------|
| Foundation | core | Base templates, rules, settings |
| Hooks | hooks-essential, hooks-quality, hooks-routing | Automated quality and security gates |
| Skills | skills-dev, skills-meta, skills-planning, skills-research | Structured workflows |
| Agents | agents-dev | Specialist agent definitions |
| Commands | commands-dev, commands-prp | Slash commands |
| Contexts | contexts | Mode switching (dev, review, research, audit) |
| Config | config-hypervisor | Central automation configuration |
| Orchestration | team-orchestrator | Multi-agent team coordination |

See [docs/MODULES_CATALOG.md](docs/MODULES_CATALOG.md) for full details.

## Presets

| Preset | Modules | Best for |
|--------|---------|----------|
| **minimal** | core | Lightweight setup, just the essentials |
| **standard** | core, hooks-essential, skills-meta, skills-planning, contexts | Balanced development workflow |
| **research** | core, hooks-essential, skills-meta, skills-planning, skills-research, contexts | Academic and research projects |
| **professional** | core, hooks-essential, hooks-quality, hooks-routing, skills-meta, skills-planning, skills-dev, agents-dev, commands-dev, contexts | Full professional development |
| **enterprise** | All 14 modules | Maximum coverage with team orchestration |

Presets are simple text files listing module names. Create your own by listing
the modules you want, one per line.

## Architecture

The framework is built on:

- **Pydantic v2** for type-safe configuration models
- **Jinja2** for template rendering with custom filters
- **msgpack** for compact binary checkpoints (TOON format)
- **Topological sort** for dependency resolution

All hooks follow the **fail-open** pattern: internal errors never block Claude Code.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Framework design, directory structure, algorithms |
| [HOOKS_REFERENCE.md](docs/HOOKS_REFERENCE.md) | All 18 hook events with JSON schemas |
| [MODULES_CATALOG.md](docs/MODULES_CATALOG.md) | Complete module descriptions and dependencies |
| [CREATING_MODULES.md](docs/CREATING_MODULES.md) | How to create custom modules |
| [MIGRATION.md](docs/MIGRATION.md) | Migration guide for existing `.claude/` users |

## Development

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ --cov=lib --cov-report=term-missing

# Lint
ruff check lib/ scripts/ tests/
ruff format lib/ scripts/ tests/

# Type check
pyright lib/
```

### Test Suite

The framework has 565+ tests organized by development phase (phase_00 through phase_10).
Coverage target is 90% per file.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-module`)
3. Write tests first (TDD preferred)
4. Implement your changes
5. Run the full quality gate: `ruff check && ruff format --check && pyright lib/ && pytest tests/`
6. Submit a pull request

### Creating a Module

See [docs/CREATING_MODULES.md](docs/CREATING_MODULES.md) for the complete guide.
In short:

1. Create `modules/my-module/MODULE.md` with YAML frontmatter
2. Add your hooks, skills, agents, or commands
3. Add `settings.hooks.json` if you have hooks
4. Write tests
5. Optionally add to a preset

## License

MIT License. See [pyproject.toml](pyproject.toml) for details.
