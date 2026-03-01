---
plan: claude-code-kazuba-v2
version: "3.0"
phase: 12
title: "Rust Acceleration Layer"
effort: "L"
estimated_tokens: 15000
depends_on: [11]
parallel_group: "infra"
context_budget: "1 context window (~180k tokens)"
validation_script: "validation/validate_phase_12.py"
checkpoint: "checkpoints/phase_12.toon"
recovery_plan: "If Rust compilation fails: mark phase as OPTIONAL, Python-only fallback is sufficient"
agent_execution_spec: "general-purpose with Rust toolchain"
status: "pending"
cross_refs:
  - {file: "01-phase-shared-infrastructure.md", relation: "depends_on"}
  - {file: "09-phase-integration-presets-migration.md", relation: "blocks"}
---

# Phase 12: Rust Acceleration Layer

**Effort**: L | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 11

**Parallel with**: Phase 13 (Core Governance + CILA Formal)


## Description

Integrate the Rust acceleration crate for high-performance pattern matching, secrets detection, and code quality validation. This phase is OPTIONAL: the Python fallback must always work without Rust installed.


## Objectives

- [ ] Copy kazuba-hooks Rust crate and verify cargo check passes
- [ ] Create Python facade (lib/rust_bridge.py) with try/except fallback
- [ ] Benchmark Rust vs Python performance (target: 5x speedup)
- [ ] Add optional [rust] dependency group to pyproject.toml
- [ ] Ensure all code paths work WITHOUT Rust installed


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `rust/kazuba-hooks/Cargo.toml` | Rust crate manifest | 50 |
| `rust/kazuba-hooks/src/lib.rs` | Rust crate entry point with PyO3 | 800 |
| `lib/rust_bridge.py` | Python facade with Rust fallback | 150 |


## Source Files (Extraction Map)

| Source Path | Target | Type | LOC | Key Classes |
|-------------|--------|------|-----|-------------|
| `kazuba-cargo/.claude/rust/kazuba-hooks/` | `rust/kazuba-hooks/` | DIRECT_COPY | 7000 | SecretsDetector, BashSafetyValidator, CodeQualityValidator, SkillMatcher |
| `(new)` | `lib/rust_bridge.py` | REIMPLEMENT | 150 | RustBridge |

### Adaptation Notes

- **`rust/kazuba-hooks/`**: Copy entire crate, verify cargo check passes
- **`lib/rust_bridge.py`**: Python facade with try/except import fallback to lib/patterns.py

### External Dependencies from Sources

- `aho-corasick`
- `pyo3`
- `rayon`
- `regex`
- `serde`


## Test Specifications

| Test File | Min Tests | Coverage | Categories |
|-----------|-----------|----------|------------|
| `tests/phase_12/test_rust_bridge.py` | 20 | 90% | unit, integration |
| `tests/phase_12/test_rust_fallback.py` | 15 | 90% | unit |


## Testing

- **Test directory**: `tests/phase_12/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_rust_bridge.py`
  - `test_rust_fallback.py`


## Acceptance Criteria

- [ ] cargo check passes in rust/kazuba-hooks/
- [ ] lib/rust_bridge.py works WITH Rust installed (if available)
- [ ] lib/rust_bridge.py gracefully falls back to Python WITHOUT Rust
- [ ] Benchmark: Rust >=5x faster than Python for pattern matching
- [ ] pyproject.toml has optional [rust] dep group


## Tools Required

- Bash, Write, Edit


## Risks

- Rust toolchain not available on all machines -- fallback must work
- PyO3 version mismatch -- pin to 0.28.2


## Recovery Plan

If Rust compilation fails: mark phase as OPTIONAL, Python-only fallback is sufficient


## Agent Execution

**Spec**: general-purpose with Rust toolchain


## Checkpoint

After completing this phase, run:
```bash
python plans/v2/validation/validate_phase_12.py
```
Checkpoint saved to: `checkpoints/phase_12.toon`
