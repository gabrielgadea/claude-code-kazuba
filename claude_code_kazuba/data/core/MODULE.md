---
name: core
version: "0.1.0"
description: "Core configuration module — always installed"
author: "Gabriel Gadea"
dependencies: []
provides:
  templates:
    - CLAUDE.md
    - settings.json
    - settings.local.json
    - .gitignore
  rules:
    - code-style
    - security
    - testing
    - git-workflow
---

# core

The core module is the foundation of every claude-code-kazuba installation.
It is always installed and provides the base templates and universal rules
that all other modules build upon.

## Templates

| Template | Output | Description |
|----------|--------|-------------|
| `CLAUDE.md.template` | `.claude/CLAUDE.md` | Master project configuration with CRC cycle, circuit breakers, validation gate |
| `settings.json.template` | `.claude/settings.json` | Claude Code settings with permissions, hooks, and env vars |
| `settings.local.json.template` | `.claude/settings.local.json` | Personal overrides (gitignored) |
| `.gitignore.template` | `.claude/.gitignore` | Gitignore patterns for the .claude/ directory |

## Rules

| Rule | Scope |
|------|-------|
| `code-style.md` | Universal naming, file organization, imports, comments |
| `security.md` | OWASP awareness, secrets, PII, input validation, dependencies |
| `testing.md` | TDD workflow, coverage targets, test pyramid, naming |
| `git-workflow.md` | Branches, commits, PRs, force-push policy |

## Usage

The core module is automatically installed by `kazuba init`. Its templates
are rendered with project-specific variables and placed in `.claude/`.
Rules are concatenated into the CLAUDE.md rules section.
