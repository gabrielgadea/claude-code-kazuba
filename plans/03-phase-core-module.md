      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 2
      title: "Core Module"
      effort: "M"
      estimated_tokens: 12000
      depends_on: [1]
      parallel_group: null
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_02.py"
      checkpoint: "checkpoints/phase_02.toon"
      status: "pending"
      cross_refs:
        - {file: "01-phase-shared-library-lib-.md", relation: "depends_on"}
- {file: "08-phase-installer-cli.md", relation: "blocks"}
      ---

# Phase 2: Core Module

**Effort**: M | **Tokens**: ~12,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 1


## Description

Create the core module that is always installed. Contains CLAUDE.md template, settings.json template, and universal rules extracted from all 4 source configs.


## Objectives

- [ ] Create CLAUDE.md.template with CRC cycle, circuit breakers, validation gate
- [ ] Create settings.json.template with $schema, hooks stubs, env vars
- [ ] Create settings.local.json.template (gitignored, personal preferences)
- [ ] Create .gitignore.template for .claude/ directory
- [ ] Extract and generalize rules from kazuba-cargo/.claude/rules/
- [ ] Create MODULE.md manifest with metadata and dependencies


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `core/CLAUDE.md.template` | Master template with Jinja2 vars | 150 |
| `core/settings.json.template` | Base settings with $schema | 60 |
| `core/settings.local.json.template` | Local overrides template | 20 |
| `core/.gitignore.template` | Gitignore for .claude/ | 15 |
| `core/MODULE.md` | Core module manifest | 30 |
| `core/rules/code-style.md` | Universal code style rules | 50 |
| `core/rules/security.md` | Security rules (OWASP, secrets, PII) | 60 |
| `core/rules/testing.md` | Testing rules (TDD, coverage, pyramid) | 40 |
| `core/rules/git-workflow.md` | Git workflow rules (branches, commits) | 40 |


## Source Files (extract from)

- `~/.claude/CLAUDE.md (CRC cycle, circuit breakers, validation gate, L1-L5 taxonomy)`
- `kazuba-cargo/.claude/rules/ (code-style, security, testing, git-workflow)`
- `analise/.claude/rules/00-core-governance.md (CODE-FIRST, ZERO-HALLUCINATION)`
- `kazuba-cargo/.claude/CLAUDE.md (compact style, context optimization)`


## Testing

- **Test directory**: `tests/phase_02/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_core_templates.py`
  - `test_rules_content.py`


## Acceptance Criteria

- [ ] CLAUDE.md.template renders with sample vars without error
- [ ] settings.json.template is valid JSON after rendering
- [ ] All rules files have actionable content (not placeholder)
- [ ] Templates contain {{PROJECT_NAME}}, {{LANGUAGE}}, {{STACK}} variables
- [ ] pytest tests/phase_02/ passes


## Tools Required

- Write, Edit, Bash


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_02.py
```
Checkpoint saved to: `checkpoints/phase_02.toon`
