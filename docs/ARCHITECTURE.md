# Architecture

## Overview

claude-code-kazuba is a modular configuration framework for Claude Code. It provides
reusable modules of hooks, skills, agents, commands, and configuration that can be
composed into presets and installed into any project's `.claude/` directory.

**Design philosophy**: Convention over configuration. Sensible defaults. Fail-open hooks.
Composable modules. Type-safe configuration.

## Directory Structure

```
claude-code-kazuba/
├── .claude/              # Framework's own Claude Code config
│   └── CLAUDE.md         # Project rules for developing the framework
├── .github/
│   └── workflows/
│       └── ci.yml        # Lint + typecheck + test pipeline
├── core/                 # Core module (always installed)
│   ├── MODULE.md         # Module manifest
│   ├── CLAUDE.md.template
│   ├── settings.json.template
│   ├── settings.local.json.template
│   └── rules/            # Universal rules (code-style, security, testing, git)
├── modules/              # Optional modules (installed by preset or selection)
│   ├── hooks-essential/  # Prompt enhancer, status monitor, auto-compact
│   ├── hooks-quality/    # Quality gate, secrets scanner, PII scanner, bash safety
│   ├── hooks-routing/    # CILA router, knowledge manager, compliance tracker
│   ├── skills-dev/       # Verification loop, problem solver, eval harness
│   ├── skills-meta/      # Hook master, skill master, skill writer
│   ├── skills-planning/  # Plan amplifier, plan execution, code-first planner
│   ├── skills-research/  # Academic research writer, literature review
│   ├── agents-dev/       # Code reviewer, security auditor, meta-orchestrator
│   ├── commands-dev/     # debug-RCA, smart-commit, orchestrate, verify
│   ├── commands-prp/     # PRP create and execute commands
│   ├── contexts/         # dev, review, research, audit mode contexts
│   ├── config-hypervisor/# Hypervisor, agent triggers, event mesh configs
│   └── team-orchestrator/# Multi-agent orchestration (agents, routing, SLA)
├── presets/              # Preset definitions (module lists)
│   ├── minimal.txt       # Core only
│   └── standard.txt      # Core + essential hooks + planning + meta + contexts
├── lib/                  # Shared Python library
│   ├── __init__.py       # Package root with version
│   ├── config.py         # Pydantic v2 models (manifest, settings, installer)
│   ├── hook_base.py      # Hook infrastructure (HookInput, HookResult, fail_open)
│   ├── json_output.py    # JSON output builders for hook contract
│   ├── patterns.py       # Regex patterns (secrets, PII, bash safety)
│   ├── template_engine.py# Jinja2 template rendering with custom filters
│   ├── checkpoint.py     # TOON format checkpoint save/load
│   └── performance.py    # L0Cache, ParallelExecutor, Rust accelerator
├── scripts/              # Build and generation scripts
│   └── generate_plan.py  # Plan generation and validation
├── tests/                # Test suite (pytest)
│   ├── conftest.py       # Shared fixtures
│   ├── phase_00/         # Bootstrap tests
│   ├── phase_01/         # Library module tests
│   ├── ...               # One directory per phase
│   └── phase_10/         # CI + documentation tests
├── plans/                # Phase execution plans
│   └── validation/       # Phase validation scripts
├── checkpoints/          # TOON format checkpoint files
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # This file
│   ├── HOOKS_REFERENCE.md# All 18 hook events with schemas
│   ├── MODULES_CATALOG.md# Module descriptions and dependencies
│   ├── CREATING_MODULES.md# Extensibility guide
│   └── MIGRATION.md      # Migration guide for existing users
└── pyproject.toml        # Python project configuration
```

## Module System

### Module Manifest (MODULE.md)

Every module has a `MODULE.md` with YAML frontmatter:

```yaml
---
name: hooks-essential
version: "1.0.0"
description: "Essential hook infrastructure"
dependencies:
  - core
provides:
  hooks:
    - prompt_enhancer
    - status_monitor
    - auto_compact
hook_events:
  - UserPromptSubmit
  - SessionStart
  - PreCompact
---
```

The frontmatter declares the module's name, version, dependencies, and what it provides
(hooks, skills, agents, commands, config, contexts, templates, rules).

### Dependency Resolution

Dependencies are resolved using topological sort (depth-first). The algorithm in
`lib.config.resolve_dependencies()`:

1. Takes a list of requested modules and a map of all available manifests
2. For each requested module, recursively visits its dependencies first
3. Adds each module to the resolved list after all its dependencies
4. Raises `ValueError` if a dependency is missing

This ensures modules are installed in the correct order (dependencies before dependents).
Circular dependencies are implicitly handled by the visited set.

## Template Engine

The template engine (`lib.template_engine.TemplateEngine`) uses Jinja2 to render
module templates with project-specific variables.

### Custom Filters

| Filter | Purpose | Example |
|--------|---------|---------|
| `slug` | Convert to kebab-case | `"My Module"` -> `"my-module"` |
| `upper_first` | Capitalize first char | `"hello"` -> `"Hello"` |
| `indent_block` | Indent all lines | 4-space indentation by default |

### Rendering Pipeline

1. `TemplateEngine` is initialized with a templates directory
2. `render(template_name, variables)` loads the template and renders it
3. `render_string(template_str, variables)` renders from a string directly
4. Variables are project-specific (name, stack, author, etc.)

## Hook Lifecycle

Claude Code provides 18 hook events that fire at specific points during a session.
Hooks receive JSON via stdin and respond via stdout + exit code.

### Hook Contract

- **Input**: JSON on stdin with `session_id`, `cwd`, `hook_event_name`, and event-specific fields
- **Output**: JSON on stdout with `hookSpecificOutput` containing event-specific response
- **Exit codes**: 0 = allow/continue, 1 = block (with reason), 2 = deny (hard block)
- **Timeout**: Default 10 seconds per hook
- **Fail-open**: All hooks MUST use the `fail_open` decorator to prevent blocking Claude Code

### Event Flow

```
Session Start
  │
  ├── SessionStart ──────────────────────► Status monitor, context injection
  │
  ├── [User types prompt]
  │   └── UserPromptSubmit ──────────────► Prompt enhancement, CILA routing
  │
  ├── [Claude plans response]
  │   ├── PreAssistantTurn ──────────────► Turn-level context
  │   │
  │   ├── [Tool usage]
  │   │   ├── PreToolUse ────────────────► Quality gate, secrets, PII, bash safety
  │   │   └── PostToolUse ───────────────► Compliance tracking
  │   │
  │   ├── [Subagent usage]
  │   │   ├── SubagentToolUse ───────────► Subagent tool control
  │   │   └── PostSubagentToolUse ───────► Subagent result tracking
  │   │
  │   └── PostAssistantTurn ─────────────► Turn completion
  │
  ├── [Approval flows]
  │   ├── PreApproval / PostApproval
  │   └── PrePlanModeApproval / PostPlanModeApproval
  │
  ├── [Context management]
  │   └── PreCompact ────────────────────► Save checkpoint before compaction
  │
  ├── [Notifications]
  │   ├── PreNotification ───────────────► Filter notifications
  │   └── PostNotification ──────────────► Log notifications
  │
  ├── Stop ──────────────────────────────► Decide whether to stop or continue
  │
  ├── Heartbeat ─────────────────────────► Periodic health check
  │
  └── SessionStop ───────────────────────► Cleanup, final checkpoint
```

## Preset System

Presets are simple text files listing module names (one per line). They define
which modules to install together.

| Preset | Modules |
|--------|---------|
| `minimal` | core |
| `standard` | core, hooks-essential, skills-meta, skills-planning, contexts |
| `research` | core, hooks-essential, skills-meta, skills-planning, skills-research, contexts |
| `professional` | core, hooks-essential, hooks-quality, hooks-routing, skills-meta, skills-planning, skills-dev, agents-dev, commands-dev, contexts |
| `enterprise` | All 14 modules |

Users select a preset during installation. The installer reads the preset file,
resolves dependencies, and installs modules in order.

## Config Merging Strategy

When multiple modules provide configuration (especially `settings.json` hooks),
the installer merges them:

1. Start with the core template output
2. For each module (in dependency order), merge its `settings.hooks.json`
3. Hooks are appended to the appropriate event array
4. Permissions are unioned (allow lists merged, deny lists merged)
5. Environment variables are merged (later modules override earlier)

## Checkpoint (.toon) Format

TOON (Tool Output Notation) is a binary checkpoint format:

```
Offset  Size  Field
0       4     Magic bytes: "TOON"
4       1     Version: 1
5       N     msgpack payload (dictionary)
```

The payload contains:
- `phase_id`: Phase number
- `title`: Human-readable title
- `timestamp`: ISO 8601 UTC timestamp
- `results`: Phase-specific results dictionary

## Design Decisions

1. **Jinja2 over string interpolation**: Templates need conditionals and loops
   for generating complex CLAUDE.md files with optional sections per module.

2. **Pydantic v2 for config**: Type safety, validation, and serialization
   out of the box. Models serve as both documentation and runtime contracts.

3. **msgpack for checkpoints**: Compact binary format, faster than JSON for
   large payloads, while supporting the same data types.

4. **fail-open hooks**: A broken hook should never prevent Claude Code from
   working. All exceptions are caught and logged to stderr.

5. **Preset files as plain text**: Simple, diff-friendly, no parsing needed.
   One module name per line.

6. **Topological sort for dependencies**: Standard algorithm, deterministic
   ordering, clear error messages for missing dependencies.

7. **Module-per-directory convention**: Each module is self-contained with
   its own MODULE.md manifest, making it easy to add, remove, or fork modules.

8. **Separation of lib/ and modules/**: Library code is reusable Python;
   modules are configuration content. This prevents circular dependencies
   and keeps the library testable independently.
