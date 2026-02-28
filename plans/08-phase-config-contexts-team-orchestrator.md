      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 7
      title: "Config + Contexts + Team Orchestrator"
      effort: "M"
      estimated_tokens: 12000
      depends_on: [0]
      parallel_group: "content"
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_07.py"
      checkpoint: "checkpoints/phase_07.toon"
      status: "pending"
      cross_refs:
        - {file: "00-phase-bootstrap-&-scaffolding.md", relation: "depends_on"}
- {file: "08-phase-installer-cli.md", relation: "blocks"}
      ---

# Phase 7: Config + Contexts + Team Orchestrator

**Effort**: M | **Tokens**: ~12,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 0

**Parallel with**: Phase 6 (Skills + Agents + Commands)


## Description

Extract centralized automation configs, context modifiers, and the team orchestrator framework.


## Objectives

- [ ] Extract and generalize hypervisor.yaml (circuit breakers, SLA, thinking levels)
- [ ] Extract agent_triggers.yaml (declarative agent auto-selection)
- [ ] Extract event_mesh.yaml (event bus architecture)
- [ ] Create 4 context modifiers (dev, review, research, audit)
- [ ] Extract team orchestrator with Pydantic models and config YAML


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/config-hypervisor/MODULE.md` | Module manifest | 20 |
| `modules/config-hypervisor/config/hypervisor.yaml` | Automation config | 80 |
| `modules/config-hypervisor/config/agent_triggers.yaml` | Agent triggers | 60 |
| `modules/config-hypervisor/config/event_mesh.yaml` | Event bus config | 50 |
| `modules/contexts/MODULE.md` | Module manifest | 20 |
| `modules/contexts/contexts/dev.md` | Dev mode (relaxed) | 30 |
| `modules/contexts/contexts/review.md` | Review mode (strict) | 30 |
| `modules/contexts/contexts/research.md` | Research mode (deep) | 30 |
| `modules/contexts/contexts/audit.md` | Audit mode (thorough) | 30 |
| `modules/team-orchestrator/MODULE.md` | Module manifest | 20 |
| `modules/team-orchestrator/config/agents.yaml` | Agent registry | 40 |
| `modules/team-orchestrator/config/routing_rules.yaml` | Routing rules | 40 |
| `modules/team-orchestrator/config/sla.yaml` | SLA targets | 30 |
| `modules/team-orchestrator/src/models.py` | Pydantic v2 models | 150 |
| `modules/team-orchestrator/templates/task-delegation.md` | Delegation template | 20 |
| `modules/team-orchestrator/templates/status-report.md` | Status template | 20 |


## Source Files (extract from)

- `kazuba-cargo/.claude/config/hypervisor.yaml`
- `kazuba-cargo/.claude/config/agent_triggers.yaml`
- `kazuba-cargo/.claude/config/event_mesh.yaml`
- `kazuba-cargo/.claude/contexts/ (dev, review, research, tir-audit)`
- `~/.claude/skills/team-orchestrator/ (config, src, templates)`


## Testing

- **Test directory**: `tests/phase_07/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_yaml_configs.py`
  - `test_orchestrator_models.py`
  - `test_contexts.py`


## Acceptance Criteria

- [ ] All YAML files pass yaml.safe_load() validation
- [ ] Pydantic models validate sample data without errors
- [ ] Contexts modify behavior descriptors appropriately
- [ ] hypervisor.yaml has circuit_breakers, sla, thinking sections


## Tools Required

- Write, Edit, Bash


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_07.py
```
Checkpoint saved to: `checkpoints/phase_07.toon`
