---
name: team-orchestrator
description: |
  Multi-agent team orchestration — agent registry, routing rules, SLA targets,
  and delegation templates. Coordinates work across specialized agents.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - config-hypervisor
provides:
  config:
    - agents.yaml
    - routing_rules.yaml
    - sla.yaml
  src:
    - models.py
  templates:
    - task-delegation.md
    - status-report.md
---

# team-orchestrator

Configuration, typed models, and templates for multi-agent orchestration.

## Contents

| File | Purpose |
|------|---------|
| `config/agents.yaml` | Agent registry with capabilities and SLA |
| `config/routing_rules.yaml` | Declarative routing rules |
| `config/sla.yaml` | SLA targets and rate limits |
| `src/models.py` | Pydantic v2 typed models (TaskRequest, AgentConfig, etc.) |
| `templates/task-delegation.md` | Task delegation template |
| `templates/status-report.md` | Status report template |
