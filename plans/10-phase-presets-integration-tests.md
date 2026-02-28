      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 9
      title: "Presets + Integration Tests"
      effort: "M"
      estimated_tokens: 12000
      depends_on: [8]
      parallel_group: null
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_09.py"
      checkpoint: "checkpoints/phase_09.toon"
      status: "pending"
      cross_refs:
        - {file: "08-phase-installer-cli.md", relation: "depends_on"}
- {file: "10-phase-github-ci-documentation.md", relation: "blocks"}
      ---

# Phase 9: Presets + Integration Tests

**Effort**: M | **Tokens**: ~12,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 8


## Description

Define all 5 presets with exact module lists, run integration tests that install each preset and validate the result.


## Objectives

- [ ] Define module lists for all 5 presets
- [ ] Create integration test that installs each preset to temp dir
- [ ] Verify all hooks fire correctly in mock Claude Code session
- [ ] Verify settings.json is valid after each preset install
- [ ] Create E2E test script


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `tests/integration/test_preset_minimal.py` | Minimal preset E2E | 40 |
| `tests/integration/test_preset_standard.py` | Standard preset E2E | 50 |
| `tests/integration/test_preset_professional.py` | Professional preset E2E | 50 |
| `tests/integration/test_preset_enterprise.py` | Enterprise preset E2E | 60 |
| `tests/integration/test_preset_research.py` | Research preset E2E | 40 |
| `tests/integration/conftest.py` | Shared integration fixtures | 40 |


## Testing

- **Test directory**: `tests/integration/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_preset_minimal.py`
  - `test_preset_standard.py`
  - `test_preset_professional.py`
  - `test_preset_enterprise.py`
  - `test_preset_research.py`


## Acceptance Criteria

- [ ] All 5 preset installations succeed in clean temp directories
- [ ] Installed settings.json passes JSON Schema validation
- [ ] All hook scripts are executable and exit 0 on empty input
- [ ] All SKILL.md files have valid YAML frontmatter
- [ ] validate_installation.py passes for each preset


## Tools Required

- Bash, Write, Edit


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_09.py
```
Checkpoint saved to: `checkpoints/phase_09.toon`
