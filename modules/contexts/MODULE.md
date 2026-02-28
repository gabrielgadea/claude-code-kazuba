---
name: contexts
description: |
  Mode-switching contexts that adjust Claude Code behavior for different tasks.
  Each context defines quality gates, response style, and focus areas.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  contexts:
    - dev
    - review
    - research
    - audit
---

# contexts

Behavioral contexts that tune Claude Code for specific workflows.

## Contents

| Context | Purpose |
|---------|---------|
| `dev` | Fast iteration, relaxed gates, terse responses |
| `review` | Strict checks, comprehensive analysis, detailed output |
| `research` | Deep exploration, multiple sources, thorough documentation |
| `audit` | Compliance focus, evidence-based, full traceability |
