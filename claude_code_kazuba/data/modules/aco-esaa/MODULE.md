---
name: aco-esaa
description: |
  Event-Sourced Agent Architecture (ESAA) — append-only event store with
  CQRS separation, saga-based compensation, SHA-256 hash chain integrity,
  time-travel state reconstruction, and offline RL buffer.
  Foundation layer for ACO (Agentic Code Orchestrator).
version: "1.0.0"
author: "Gabriel Gadea"
dependencies:
  - core
provides:
  aco:
    - event_sourcing
    - cqrs
    - saga_orchestration
    - hash_chain
    - time_travel
    - offline_rl
    - cila_routing
---

# aco-esaa

Event-Sourced Agent Architecture — 18 Python modules.

## Key Modification from Source

### `cila_router.py` — parametric keywords

The original had `"antt"` hardcoded as a L3 keyword. This version uses
`build_cila_router(domain_keywords)` to merge domain-specific keywords
onto `DEFAULT_CILA_KEYWORDS` (additive, not replace).

```python
from aco_esaa.cila_router import build_cila_router

# Default — no ANTT, full L0-L6 coverage
router = build_cila_router()

# LexCore domain — adds L3 keywords
router = build_cila_router({3: ["lexcore", "convert", "lei"]})
```
