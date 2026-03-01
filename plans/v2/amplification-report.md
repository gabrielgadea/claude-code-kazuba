---
plan: claude-code-kazuba-v2
type: amplification-report
generated: "2026-02-28T22:13:48Z"
---

# Amplification Report: Pln1 vs Pln2

## Overview

Pln2 = (Pln1)^2 -- amplified across 9 dimensions to integrate source
components from 3 projects (analise, kazuba-cargo, inter-agent-relay)
into the claude-code-kazuba framework.

## Dimension Comparison

| Dimension | Pln1 (v0.1.0) | Pln2 (v0.2.0) | Amplification |
|-----------|---------------|---------------|---------------|
| Phases | 11 (0-10) | 12 (11-22) | 1.1x |
| Source files mapped | 0 (string refs) | 25 (structured) | 25x |
| Source LOC tracked | ~0 | ~11,271 | -- |
| Pydantic models defined | 0 | 8 | 8x |
| Hook specs with SLA | 0 | 6 | 6x |
| Test file specs | 0 | 34 | 34x |
| Recovery plans | 0 | 12 | 12x |
| Agent execution specs | 0 | 12 | 12x |
| Files to create | ~85 | 37 | -- |

## Source Extraction Analysis

| Extraction Type | Count | Description |
|----------------|-------|-------------|
| DIRECT_COPY | 2 | Copy as-is, minimal changes |
| ADAPT_IMPORTS | 17 | Refactor imports, remove domain-specific code |
| REIMPLEMENT | 6 | Rewrite from scratch using reference |
| **Total** | **25** | |

### Source Projects

| Project | Files | LOC | Primary Extractions |
|---------|-------|-----|---------------------|
| analise | ~10 | ~1,500 | Hooks (lifecycle, governance, validation) |
| kazuba-cargo | ~8 | ~8,500 | Rust crate, hypervisor, RLM, triggers |
| (new) | ~4 | ~620 | Event bus, governance, rust bridge |

## Estimated Effort

| Metric | Value |
|--------|-------|
| Total estimated tokens | ~140,000 |
| Total files to create | 37 |
| Total acceptance criteria | 53 |
| Total test specs | 34 |
| Critical path length | 6 phases |
| Parallelizable groups | 4 (infra, triggers, hooks, finalize) |
| Estimated context windows | ~7 (with parallelism) |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Rust toolchain unavailable | Medium | Low | Python fallback always works |
| Threading issues in CB | Low | Medium | Simplify to asyncio.Lock |
| Regression in 723 tests | Low | High | Run regression after each phase |
| Q-table unbounded growth | Medium | Medium | LRU eviction with max_entries |
| Doc cross-ref breakage | Low | Low | Generate link index programmatically |

## Key Differences from Pln1

1. **Structured source files**: Each source has `SourceFile` with path, target,
   extraction type, LOC, key classes, and adaptation notes
2. **Pydantic model specs**: Models defined upfront with fields, types, and defaults
3. **Hook specs with SLA**: Each hook has event, exit codes, and P99 latency target
4. **Test specs per file**: Minimum test count and coverage target per test file
5. **Recovery plans**: Every phase has a fallback strategy
6. **Agent execution specs**: Which agent type to use for each phase
7. **Validation scripts**: Include regression check and test spec verification
8. **Extraction types**: DIRECT_COPY, ADAPT_IMPORTS, REIMPLEMENT classification
9. **Parallel groups**: 4 groups (infra, triggers, hooks, finalize) for efficiency
