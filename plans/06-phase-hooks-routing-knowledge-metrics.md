      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 5
      title: "Hooks Routing + Knowledge + Metrics"
      effort: "M"
      estimated_tokens: 14000
      depends_on: [1]
      parallel_group: "hooks"
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_05.py"
      checkpoint: "checkpoints/phase_05.toon"
      status: "pending"
      cross_refs:
        - {file: "01-phase-shared-library-lib-.md", relation: "depends_on"}
- {file: "08-phase-installer-cli.md", relation: "blocks"}
      ---

# Phase 5: Hooks Routing + Knowledge + Metrics

**Effort**: M | **Tokens**: ~14,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 1

**Parallel with**: Phase 3 (Hooks Essential Module), Phase 4 (Hooks Quality + Security)


## Description

Extract intent classification (CILA), knowledge management (3-tier), and compliance metrics hooks.


## Objectives

- [ ] Generalize CILA intent_router.py (remove ANTT L3 patterns, keep L0-L6 framework)
- [ ] Generalize intent_patterns.py (configurable pattern registry)
- [ ] Create strategy_enforcer.py (inject DISCOVER warnings for L2+)
- [ ] Create knowledge_retrieval.py (local cache → MCP → fallback)
- [ ] Create knowledge_capture.py (PostToolUse pattern capture)
- [ ] Create compliance_collector.py + compliance_dashboard.py


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/hooks-routing/MODULE.md` | Module manifest | 30 |
| `modules/hooks-routing/hooks/intent_router.py` | CILA L0-L6 classifier | 120 |
| `modules/hooks-routing/hooks/intent_patterns.py` | Configurable regex patterns | 80 |
| `modules/hooks-routing/hooks/strategy_enforcer.py` | DISCOVER warning injection | 60 |
| `modules/hooks-routing/settings.hooks.json` | Hook registration | 20 |
| `modules/hooks-knowledge/MODULE.md` | Module manifest | 30 |
| `modules/hooks-knowledge/hooks/knowledge_retrieval.py` | 3-tier knowledge lookup | 100 |
| `modules/hooks-knowledge/hooks/knowledge_capture.py` | Pattern capture PostToolUse | 80 |
| `modules/hooks-knowledge/hooks/session_context.py` | SessionStart context loader | 60 |
| `modules/hooks-knowledge/settings.hooks.json` | Hook registration | 20 |
| `modules/hooks-metrics/MODULE.md` | Module manifest | 30 |
| `modules/hooks-metrics/hooks/compliance_collector.py` | Enforcement score recorder | 80 |
| `modules/hooks-metrics/hooks/compliance_dashboard.py` | Rich/JSON/MD dashboard | 100 |
| `modules/hooks-metrics/settings.hooks.json` | Hook registration | 20 |


## Source Files (extract from)

- `analise/.claude/hooks/routing/intent_router.py (CILA <1ms)`
- `analise/.claude/hooks/routing/intent_patterns.py`
- `analise/.claude/hooks/routing/strategy_enforcer.py`
- `analise/.claude/hooks/knowledge/cipher_knowledge_retrieval.py`
- `analise/.claude/hooks/knowledge/cipher_knowledge_capture.py`
- `analise/.claude/hooks/metrics/compliance_collector.py`
- `analise/.claude/hooks/metrics/compliance_dashboard.py`


## Testing

- **Test directory**: `tests/phase_05/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_intent_router.py`
  - `test_intent_patterns.py`
  - `test_knowledge_retrieval.py`
  - `test_compliance.py`


## Acceptance Criteria

- [ ] CILA classifier works for L0-L6 without domain-specific patterns
- [ ] Intent patterns are configurable via YAML or Python dict
- [ ] Knowledge retrieval follows 3-tier: local → MCP → fallback
- [ ] Compliance dashboard outputs rich, JSON, and markdown formats
- [ ] 90%+ coverage per file


## Tools Required

- Bash, Write, Edit


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_05.py
```
Checkpoint saved to: `checkpoints/phase_05.toon`
