---
name: skills-dev
description: |
  Development workflow skills — verification loops, problem solving escalation,
  and evaluation-driven development. These skills enforce quality and rigor
  during implementation.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  skills:
    - verification-loop
    - supreme-problem-solver
    - eval-harness
---

# skills-dev

Development skills that enforce quality gates and provide structured
problem-solving approaches.

## Contents

| Skill | Purpose |
|-------|---------|
| `verification-loop` | 6-phase pre-PR verification (build, typecheck, lint, test, security, diff) |
| `supreme-problem-solver` | Last-resort escalation solver with H0/H1/H2 horizons |
| `eval-harness` | Evaluation-driven development with measurable before/after |
