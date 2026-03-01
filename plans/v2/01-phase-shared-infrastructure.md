---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 11
title: "Shared Infrastructure"
effort: "M"
estimated_tokens: 12000
depends_on: []
parallel_group: null
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_11.py"
checkpoint: "checkpoints/phase_11.toon"
recovery_plan: "If circuit breaker threading issues: simplify to single-threaded with asyncio.Lock"
agent_execution_spec: "general-purpose with worktree isolation"
status: "pending"
cross_refs:
  - {file: "02-phase-rust-acceleration-layer.md", relation: "blocks"}
  - {file: "03-phase-core-governance-cila-formal.md", relation: "blocks"}
  - {file: "04-phase-agent-triggers-recovery-triggers.md", relation: "blocks"}
  - {file: "05-phase-hypervisor-executable.md", relation: "blocks"}
  - {file: "06-phase-advanced-hooks-batch-1.md", relation: "blocks"}
  - {file: "07-phase-advanced-hooks-batch-2.md", relation: "blocks"}
  - {file: "08-phase-rlm-learning-memory.md", relation: "blocks"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 11: Shared Infrastructure

**Effort**: M | **Tokens**: ~12,000 | **Context**: 1 context window (~180k tokens)


## Description

Build the shared infrastructure layer that all v2 components depend on. Circuit breaker, trace manager, hook logger, and event bus form the foundation for reliability, observability, and decoupled communication.


## Objectives

- [ ] Extract and adapt circuit breaker from analise hooks (thread-safe, Pydantic v2 config)
- [ ] Extract and adapt trace manager (pure Python, no Rust dependency)
- [ ] Extract and adapt hook logger (JSON-structured output)
- [ ] Implement event bus based on hypervisor_v2.py event mesh pattern
- [ ] Achieve 90%+ coverage per file with TDD approach


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `lib/circuit_breaker.py` | Thread-safe circuit breaker with Pydantic config | 200 |
| `lib/trace_manager.py` | Trace tree for hook execution | 80 |
| `lib/hook_logger.py` | Structured JSON hook logger | 80 |
| `lib/event_bus.py` | Pub/sub event bus for decoupled communication | 100 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `analise/.claude/hooks/common/hook_circuit_breaker_v2.py` | `lib/circuit_breaker.py` | ADAPT_IMPORTS | 150 | HookCircuitBreaker, CircuitBreakerConfig, CircuitBreakerRegistry |
| `analise/.claude/hooks/common/trace_manager.py` | `lib/trace_manager.py` | ADAPT_IMPORTS | 80 | TraceManager |
| `analise/.claude/hooks/common/hook_logger.py` | `lib/hook_logger.py` | ADAPT_IMPORTS | 80 | HookLogger, LogLevel |
| `(new)` | `lib/event_bus.py` | REIMPLEMENT | 120 | EventBus |

### Adaptation Notes

- **`lib/circuit_breaker.py`**: Remove kazuba_rust_core import, use Pydantic v2 config
- **`lib/trace_manager.py`**: Remove kazuba_rust_core.TraceSession dep, pure Python
- **`lib/hook_logger.py`**: Use json_output.py for formatting
- **`lib/event_bus.py`**: Based on event mesh pattern from hypervisor_v2.py

### External Dependencies from Sources

- `threading`


## Pydantic Models

### `CircuitBreakerConfig` (frozen=True)

Thread-safe circuit breaker config

- **Module**: `lib/circuit_breaker.py`
- **Fields**:
  - `max_failures: int = 5`
  - `cooldown_seconds: float = 60.0`
  - `half_open_max: int = 1`

### `TraceNode` (frozen=True)

Trace tree node

- **Module**: `lib/trace_manager.py`
- **Fields**:
  - `name: str = ""`
  - `start_time: float = 0.0`
  - `children: list[TraceNode] = []`


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_11/test_circuit_breaker.py` | 20 | 90% | unit |
| `tests/phase_11/test_trace_manager.py` | 15 | 90% | unit |
| `tests/phase_11/test_hook_logger.py` | 10 | 90% | unit |
| `tests/phase_11/test_event_bus.py` | 15 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_11/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_circuit_breaker.py`
  - `test_trace_manager.py`
  - `test_hook_logger.py`
  - `test_event_bus.py`


## Acceptance Criteria

- [ ] All 4 lib files importable and pyright clean
- [ ] Circuit breaker transitions CLOSED->OPEN->HALF_OPEN correctly
- [ ] Event bus pub/sub works with multiple subscribers
- [ ] 90%+ coverage per file
- [ ] 723 existing tests still pass (regression)


## Tools Required

- Bash, Write, Edit, Agent(general-purpose)


## Recovery Plan

If circuit breaker threading issues: simplify to single-threaded with asyncio.Lock


## Agent Execution

**Spec**: general-purpose with worktree isolation


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_11.py
```
Checkpoint saved to: `checkpoints/phase_11.toon`
