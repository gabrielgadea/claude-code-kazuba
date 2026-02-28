---
name: commands-dev
description: |
  Development slash commands — debugging, committing, orchestration, and verification.
  Each command maps to a `/command` invocable from the Claude Code prompt.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  commands:
    - debug-RCA
    - smart-commit
    - orchestrate
    - verify
---

# commands-dev

Slash commands for common development workflows.

## Contents

| Command | Invocation | Purpose |
|---------|-----------|---------|
| `debug-RCA` | `/debug-RCA` | Structured 6-step Root Cause Analysis |
| `smart-commit` | `/smart-commit` | Intelligent commit with generated message |
| `orchestrate` | `/orchestrate` | Multi-agent orchestration (feature, bugfix, refactor, security) |
| `verify` | `/verify` | Pre-PR verification loop |
