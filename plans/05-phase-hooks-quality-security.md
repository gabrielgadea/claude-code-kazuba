      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 4
      title: "Hooks Quality + Security"
      effort: "L"
      estimated_tokens: 15000
      depends_on: [1]
      parallel_group: "hooks"
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_04.py"
      checkpoint: "checkpoints/phase_04.toon"
      status: "pending"
      cross_refs:
        - {file: "01-phase-shared-library-lib-.md", relation: "depends_on"}
- {file: "08-phase-installer-cli.md", relation: "blocks"}
      ---

# Phase 4: Hooks Quality + Security

**Effort**: L | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 1

**Parallel with**: Phase 3 (Hooks Essential Module), Phase 5 (Hooks Routing + Knowledge + Metrics)


## Description

Extract quality gate pipeline and security hooks. These hooks form the defensive layer that prevents bad code and secrets from entering the codebase.


## Objectives

- [ ] Generalize post_quality_gate.py (6-stage parallel pipeline)
- [ ] Generalize code_standards_enforcer.py (auto-fix before block)
- [ ] Generalize stop_validator.py (block if tasks incomplete)
- [ ] Generalize secrets_detector.py (pattern-based)
- [ ] Create pii_detector.py (country-configurable via lib/patterns.py)
- [ ] Create bash_safety.py (block dangerous commands)


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/hooks-quality/MODULE.md` | Module manifest | 30 |
| `modules/hooks-quality/hooks/post_quality_gate.py` | 6-stage parallel QA | 200 |
| `modules/hooks-quality/hooks/code_standards_enforcer.py` | Auto-fix or block | 150 |
| `modules/hooks-quality/hooks/stop_validator.py` | Block if incomplete | 80 |
| `modules/hooks-quality/settings.hooks.json` | Hook registration | 25 |
| `modules/hooks-security/MODULE.md` | Module manifest | 30 |
| `modules/hooks-security/hooks/secrets_detector.py` | Secret/credential detection | 120 |
| `modules/hooks-security/hooks/pii_detector.py` | PII detection (configurable country) | 100 |
| `modules/hooks-security/hooks/bash_safety.py` | Block dangerous bash commands | 60 |
| `modules/hooks-security/settings.hooks.json` | Hook registration | 25 |


## Source Files (extract from)

- `analise/.claude/hooks/quality/post_quality_gate.py (6-stage, ThreadPoolExecutor)`
- `kazuba-cargo/.claude/hooks/quality/code_standards_enforcer.py (auto-fix)`
- `kazuba-cargo/.claude/hooks/lifecycle/stop_validator.py (transcript parsing)`
- `kazuba-cargo/.claude/hooks/security/secrets_detector.py`
- `analise/.claude/hooks/security/antt_pii_detector.py (L0 cache)`
- `analise/.claude/hooks/security/bash_safety_validator.py`


## Testing

- **Test directory**: `tests/phase_04/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_quality_gate.py`
  - `test_standards_enforcer.py`
  - `test_stop_validator.py`
  - `test_secrets_detector.py`
  - `test_pii_detector.py`
  - `test_bash_safety.py`


## Acceptance Criteria

- [ ] post_quality_gate runs 6 stages in parallel (ThreadPoolExecutor)
- [ ] code_standards_enforcer attempts auto-fix before blocking
- [ ] secrets_detector catches all patterns from lib/patterns.py
- [ ] pii_detector works with BR (CPF/CNPJ) and is extensible to other countries
- [ ] bash_safety blocks rm -rf /, chmod 777, curl | bash patterns
- [ ] All hooks use lib/hook_base.py dataclasses
- [ ] 90%+ coverage per file


## Tools Required

- Bash, Write, Edit


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_04.py
```
Checkpoint saved to: `checkpoints/phase_04.toon`
