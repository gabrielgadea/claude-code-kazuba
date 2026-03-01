---
name: commands-prp
description: |
  PRP (Product Requirements Prompt) commands — create and execute structured
  product requirement prompts with quality and security enforcement.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  commands:
    - prp-base-create
    - prp-base-execute
  shared:
    - quality-patterns.yml
    - security-patterns.yml
    - universal-constants.yml
---

# commands-prp

PRP (Product Requirements Prompt) system — structured approach to defining
and executing product requirements.

## Contents

| Command | Purpose |
|---------|---------|
| `prp-base-create` | Research, generate, ultrathink, output a PRP |
| `prp-base-execute` | Load PRP, plan, implement, verify |

## Shared Resources

| File | Purpose |
|------|---------|
| `quality-patterns.yml` | Reusable quality enforcement patterns |
| `security-patterns.yml` | Reusable security enforcement patterns |
| `universal-constants.yml` | Symbol legend, abbreviations, standard references |
