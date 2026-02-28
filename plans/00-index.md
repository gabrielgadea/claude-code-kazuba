---
plan: claude-code-kazuba
version: "2.0"
type: index
total_phases: 11
total_estimated_tokens: 143000
generated: "2026-02-28T20:13:51Z"
---

# Claude Code Kazuba — Pln2 Master Index

## Overview

Framework de configuração de excelência para Claude Code.
Pln2 = (Pln1)² — amplificado em 9 dimensões.

## Dependency Graph (DAG)

```
Phase 0 (Bootstrap)
    ├── Phase 1 (Shared Lib)
    │   ├── Phase 3 (Hooks Essential)  ─┐
    │   ├── Phase 4 (Hooks Quality)     ├─ PARALLEL (hooks)
    │   └── Phase 5 (Hooks Routing)    ─┘
    └── Phase 2 (Core Module)
Phase 0
    ├── Phase 6 (Skills/Agents)  ─┐
    └── Phase 7 (Config/Contexts) ┘─ PARALLEL (content)

Phase 2,3,4,5,6,7 → Phase 8 (Installer CLI)
Phase 8 → Phase 9 (Integration Tests)
Phase 9 → Phase 10 (GitHub + CI + Docs)
```

**Critical Path**: 0 → 1 → 3 → 8 → 9 → 10 (6 sequential phases)
**With parallelism**: ~8 context windows instead of 11

## Phase Summary

| # | Title | Effort | Tokens | Group | Status |
|---|-------|--------|--------|-------|--------|

| 0 | [Bootstrap & Scaffolding](00-phase-bootstrap-&-scaffolding.md) | S | ~8,000 | sequential | pending |
| 1 | [Shared Library (lib/)](01-phase-shared-library-lib-.md) | M | ~15,000 | sequential | pending |
| 2 | [Core Module](02-phase-core-module.md) | M | ~12,000 | sequential | pending |
| 3 | [Hooks Essential Module](03-phase-hooks-essential-module.md) | L | ~15,000 | hooks | pending |
| 4 | [Hooks Quality + Security](04-phase-hooks-quality-security.md) | L | ~15,000 | hooks | pending |
| 5 | [Hooks Routing + Knowledge + Metrics](05-phase-hooks-routing-knowledge-metrics.md) | M | ~14,000 | hooks | pending |
| 6 | [Skills + Agents + Commands](06-phase-skills-agents-commands.md) | L | ~15,000 | content | pending |
| 7 | [Config + Contexts + Team Orchestrator](07-phase-config-contexts-team-orchestrator.md) | M | ~12,000 | content | pending |
| 8 | [Installer CLI](08-phase-installer-cli.md) | L | ~15,000 | sequential | pending |
| 9 | [Presets + Integration Tests](09-phase-presets-integration-tests.md) | M | ~12,000 | sequential | pending |
| 10 | [GitHub + CI + Documentation](10-phase-github-ci-documentation.md) | S | ~10,000 | sequential | pending |


## Execution Strategy

### Sequential Phases (must be in order)
- Phase 0 → Phase 1 → Phase 2 (foundation)
- Phase 8 → Phase 9 → Phase 10 (integration & delivery)

### Parallel Groups
- **hooks** (after Phase 1): Phases 3, 4, 5 via Agent Team (3 agents, worktree isolation)
- **content** (after Phase 0): Phases 6, 7 via Agent Team (2 agents, worktree isolation)

### Swarm Configuration
```yaml
team: claude-code-kazuba-build
parallel_groups:
  hooks:
    phases: [3, 4, 5]
    agents: 3
    isolation: worktree
    merge_strategy: git merge --no-ff
  content:
    phases: [6, 7]
    agents: 2
    isolation: worktree
    merge_strategy: git merge --no-ff
```

## Validation

Each phase has a validation script in `validation/validate_phase_NN.py`.
Run all validations: `python plans/validation/validate_all.py`

## Checkpoints

Checkpoints saved in `.toon` format (msgpack) at `checkpoints/phase_NN.toon`.
Recovery: load last .toon checkpoint to resume from any phase.
