---
name: config-hypervisor
description: |
  Central configuration hub — hypervisor settings, agent triggers, and event mesh.
  Controls automation behavior, thinking levels, circuit breakers, and quality gates.
version: "1.0.0"
author: "Gabriel Gadea"
dependencies: []
provides:
  config:
    - hypervisor.yaml
    - agent_triggers.yaml
    - event_mesh.yaml
---

# config-hypervisor

Central configuration for the Kazuba framework automation layer.

## Contents

| Config | Purpose |
|--------|---------|
| `hypervisor.yaml` | Context management, thinking levels, circuit breakers, quality, SLA |
| `agent_triggers.yaml` | Declarative agent activation rules |
| `event_mesh.yaml` | Event bus categories, priorities, and handler routing |
