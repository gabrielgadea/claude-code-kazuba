# RLM Learning Memory Module

## Module Identity

| Field       | Value                           |
|-------------|---------------------------------|
| Name        | rlm                             |
| Version     | 1.0.0                           |
| Phase       | 18                              |
| Status      | stable                          |
| Author      | Gabriel Gadea                   |

## Description

Reinforcement Learning Memory (RLM) module for Claude Code Kazuba. Provides
persistent Q-table learning, configurable working memory with LRU eviction,
session checkpoint management, and reward calculation for hook-level
performance optimization.

The RLM module enables the Claude Code hooks framework to learn from past
interactions, adapting its behavior based on accumulated experience stored
across sessions.

## Architecture

```
modules/rlm/
├── MODULE.md               — This manifest
├── src/
│   ├── __init__.py         — Package exports
│   ├── config.py           — Pydantic configuration models
│   ├── models.py           — Core data models (LearningRecord, Episode, etc.)
│   ├── q_table.py          — Persistent Q-table with JSON persistence
│   ├── working_memory.py   — LRU working memory with configurable capacity
│   ├── session_manager.py  — Session lifecycle and checkpoint management
│   └── reward_calculator.py — Performance-based reward computation
└── config/
    └── rlm.yaml            — Default configuration values
```

## Components

### Q-Table (`q_table.py`)
- Stores state-action quality values as `(state, action) -> float`
- Persists to disk in JSON format for cross-session continuity
- Implements TD(λ) updates with eligibility traces
- Thread-safe via explicit locking primitives

### Working Memory (`working_memory.py`)
- Configurable maximum capacity (default: 1000 entries)
- LRU eviction based on access time and importance score
- Tags-based categorization and retrieval
- O(1) lookup by entry ID using internal index

### Session Manager (`session_manager.py`)
- Wraps `lib/checkpoint.py` for TOON-format persistence
- Tracks session start/end, duration, and episodes per session
- Provides episode lifecycle management (start → step → end)
- Auto-saves checkpoint on session close

### Reward Calculator (`reward_calculator.py`)
- Computes scalar rewards from performance metrics
- Supports composite reward functions (weighted sum)
- Clips reward to `[-1.0, 1.0]` range by default
- Handles missing metrics gracefully (defaults to 0.0)

## Dependencies

| Dependency     | Version   | Purpose                     |
|----------------|-----------|-----------------------------|
| pydantic       | >=2.10    | Configuration validation    |
| msgpack        | >=1.1     | TOON checkpoint format      |
| pyyaml         | >=6.0     | YAML config loading         |
| lib/checkpoint | internal  | TOON file I/O               |

## Integration

The facade `lib/rlm.py` provides a single entry point for hook integration:

```python
from claude_code_kazuba.rlm import RLMFacade

rlm = RLMFacade()
rlm.start_session("session-001")

# Record a learning step
rlm.record_step(state="hook_start", action="cache_hit", reward=0.8)

# Get best action for current state
best = rlm.best_action("hook_start")

rlm.end_session()
```

## Configuration

Override defaults via `modules/rlm/config/rlm.yaml` or environment variables:

| Key                 | Default | Description                    |
|---------------------|---------|--------------------------------|
| learning_rate       | 0.1     | Q-learning alpha               |
| discount_factor     | 0.95    | Future reward discount gamma   |
| epsilon             | 0.1     | Exploration rate               |
| max_history         | 1000    | Max records in working memory  |
| persist_path        | null    | Path for Q-table persistence   |

## Testing

Tests live in `tests/phase_18/` and cover all components with >=90% coverage.
Run via: `pytest tests/phase_18/ -q`
