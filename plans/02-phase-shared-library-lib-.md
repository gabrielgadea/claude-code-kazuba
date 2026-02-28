      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 1
      title: "Shared Library (lib/)"
      effort: "M"
      estimated_tokens: 15000
      depends_on: [0]
      parallel_group: null
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_01.py"
      checkpoint: "checkpoints/phase_01.toon"
      status: "pending"
      cross_refs:
        - {file: "00-phase-bootstrap-&-scaffolding.md", relation: "depends_on"}
- {file: "02-phase-core-module.md", relation: "blocks"}
- {file: "03-phase-hooks-essential-module.md", relation: "blocks"}
- {file: "04-phase-hooks-quality-security.md", relation: "blocks"}
- {file: "05-phase-hooks-routing-knowledge-metrics.md", relation: "blocks"}
- {file: "08-phase-installer-cli.md", relation: "blocks"}
      ---

# Phase 1: Shared Library (lib/)

**Effort**: M | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 0


## Description

Build the shared Python library that all hooks depend on. This is the foundation layer providing standardized dataclasses, patterns, performance utilities, and JSON output helpers.


## Objectives

- [ ] Create hook_base.py with frozen dataclasses (HookConfig, HookInput, HookResult)
- [ ] Create patterns.py with configurable regex patterns (secrets, PII by country)
- [ ] Create performance.py with L0 cache, parallel executor, Rust accelerator singleton
- [ ] Create json_output.py with factory functions per hook event
- [ ] Create config.py with Pydantic v2 models for all config validation
- [ ] Create checkpoint.py with .toon save/load using msgpack
- [ ] Achieve 90%+ coverage per file with TDD approach


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `lib/hook_base.py` | Core hook dataclasses and exit code contracts | 120 |
| `lib/patterns.py` | Reusable regex patterns (secrets, PII, safety) | 150 |
| `lib/performance.py` | L0 cache, ParallelExecutor, RustAccelerator | 100 |
| `lib/json_output.py` | Standardized JSON output builders per event | 80 |
| `lib/config.py` | Pydantic v2 models for settings, hooks, modules | 200 |
| `lib/checkpoint.py` | Checkpoint save/load in .toon (msgpack) format | 80 |
| `lib/template_engine.py` | Jinja2-based template renderer for CLAUDE.md etc | 60 |


## Source Files (extract from)

- `~/.claude/hooks/prompt_enhancer.py (hook_base patterns)`
- `analise/.claude/hooks/security/antt_pii_detector.py (L0 cache, PII patterns)`
- `kazuba-cargo/.claude/hooks/security/secrets_detector.py (secret patterns)`
- `analise/.claude/hooks/quality/post_quality_gate.py (parallel executor)`


## TDD Specification

Write tests BEFORE implementation for each file:

### test_hook_base.py
- test_hook_input_from_dict: valid JSON → HookInput
- test_hook_input_from_stdin_invalid: bad JSON → exit BLOCK
- test_hook_result_emit_allow: exit 0, no stderr
- test_hook_result_emit_deny: exit 2, stderr message
- test_hook_config_frozen: cannot mutate after creation
- test_exit_codes_constants: ALLOW=0, BLOCK=1, DENY=2

### test_patterns.py
- test_secret_patterns_detect_api_key: match API key formats
- test_secret_patterns_no_false_positive: safe strings pass
- test_pii_patterns_brazil_cpf: detect CPF format
- test_pii_patterns_configurable_country: switch country, different patterns
- test_whitelist_patterns_env_vars: process.env.* not flagged

### test_performance.py
- test_l0_cache_hit: cached result returns without computation
- test_l0_cache_miss: uncached triggers computation
- test_l0_cache_ttl_expiry: expired entry triggers recomputation
- test_parallel_executor_runs_parallel: verify concurrent execution
- test_rust_accelerator_fallback: when unavailable, returns None

### test_checkpoint.py
- test_save_toon: save dict → .toon file exists
- test_load_toon: load .toon → same dict
- test_roundtrip: save → load → equal
- test_checkpoint_metadata: includes timestamp, phase_id, version


## Key Design Decisions

- All dataclasses use `frozen=True` for immutability
- Type hints use modern syntax: `list[T]`, `T | None` (not `List[T]`, `Optional[T]`)
- `from __future__ import annotations` in every file
- PII patterns configurable via country code: `PIIPatterns.for_country("BR")`
- L0 cache uses SHA-256 hash key with configurable TTL (default 300s)
- .toon format: msgpack header (4 bytes magic + version) + msgpack payload
- Template engine wraps Jinja2 with custom filters for CLAUDE.md rendering


## Testing

- **Test directory**: `tests/phase_01/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_hook_base.py`
  - `test_patterns.py`
  - `test_performance.py`
  - `test_json_output.py`
  - `test_config.py`
  - `test_checkpoint.py`
  - `test_template_engine.py`


## Acceptance Criteria

- [ ] All 7 lib/ files created and importable
- [ ] pytest tests/phase_01/ passes with 90%+ coverage per file
- [ ] pyright --strict lib/ passes with 0 errors
- [ ] ruff check lib/ passes with 0 errors
- [ ] Checkpoint .toon roundtrip verified


## Tools Required

- Bash, Write, Edit, Agent(general-purpose)
- MCP: context7


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_01.py
```
Checkpoint saved to: `checkpoints/phase_01.toon`
