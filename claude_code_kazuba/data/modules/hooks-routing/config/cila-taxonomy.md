# CILA Taxonomy — Code-Integration Levels for AI

> Priority: 6
> Scope: All skills and hooks in the framework
> Runtime: `modules/hooks-routing/hooks/cila_router.py`

---

## Overview

CILA (Code-Integration Levels for AI) classifies tasks by their code-integration complexity.
Used by the strategy enforcer and skill auto-router to determine required workflow behavior.

---

## Levels

| Level | Name            | Description                                               | Example                            |
|-------|-----------------|-----------------------------------------------------------|------------------------------------|
| L0    | Direct          | Direct prompt without code                                | Simple questions, chat             |
| L1    | PAL             | Program-Aided Language — generates simple code            | Calculations, formatting           |
| L2    | Tool-Augmented  | Uses external tools (Bash, Read/Write, search)            | File queries, web search           |
| L3    | Pipelines       | Executes multi-phase pipelines with state verification    | Multi-step analysis workflows      |
| L4    | Agent Loops     | ReAct loops with self-correction (max 3 iterations)       | Orchestrators, complex debugging   |
| L5    | Self-Modifying  | Modifies own behavior or capabilities                     | Capability Evolver, self-evolution |
| L6    | Multi-Agent     | Orchestrates multiple agents (swarm/team)                 | Cognitive Orchestrator, sprints    |

---

## Classification Heuristics

For automated classification by `cila_router.py`:

- Mentions `pipeline_state`, `pipeline_runner`, multi-phase execution → **L3+**
- Mentions `ReAct`, `auto-correction`, `iteration loop`, `max_iterations` → **L4+**
- Mentions `self-evolution`, `mutation`, `drift detection`, `capability` → **L5+**
- Mentions `swarm`, `team`, `multi-agent`, `orchestrate agents` → **L6**
- Mentions `Bash`, `Read`, `Write`, `tool_use`, file operations → **L2+**
- Mentions `calculate`, `format`, `convert` only → **L1**
- No code indicators → **L0**

---

## Compliance Requirements by Level

| Level | Pipeline Required | Quality Gate | Coverage Target | Planning Required |
|-------|-------------------|--------------|-----------------|-------------------|
| L0-L1 | No                | No           | N/A             | No                |
| L2    | No                | Optional     | 80%             | No                |
| L3    | YES (state check) | YES          | 90%             | Recommended       |
| L4    | YES               | YES          | 90%             | YES               |
| L5-L6 | Project-specific  | YES          | 95%             | YES (mandatory)   |

---

## Enforcement

The `strategy_enforcer.py` hook (PreToolUse event) enforces CILA requirements:

- L0-L1: No enforcement — advisory only
- L2+: DISCOVER warning injected (find existing scripts before creating)
- L3+: Pipeline state check required
- L4+: ReAct loop control (max 3 iterations)
- L5+: Explicit user approval required
- L6: Full team orchestration sequence enforced

Exit codes:
- Exit 0: Allow (advisory warnings via additionalContext)
- Exit 2: Block (hard violations only — e.g., security breach)

---

## Implementation Files

| Component           | Path                                                   |
|---------------------|--------------------------------------------------------|
| Strategy Enforcer   | `modules/hooks-routing/hooks/strategy_enforcer.py`     |
| CILA Router         | `modules/hooks-routing/hooks/cila_router.py`           |
| Governance Library  | `lib/governance.py`                                    |
| Compliance Tracker  | `modules/hooks-routing/hooks/compliance_tracker.py`    |
