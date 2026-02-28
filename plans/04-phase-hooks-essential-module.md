      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 3
      title: "Hooks Essential Module"
      effort: "L"
      estimated_tokens: 15000
      depends_on: [1]
      parallel_group: "hooks"
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_03.py"
      checkpoint: "checkpoints/phase_03.toon"
      status: "pending"
      cross_refs:
        - {file: "01-phase-shared-library-lib-.md", relation: "depends_on"}
- {file: "08-phase-installer-cli.md", relation: "blocks"}
      ---

# Phase 3: Hooks Essential Module

**Effort**: L | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 1

**Parallel with**: Phase 4 (Hooks Quality + Security), Phase 5 (Hooks Routing + Knowledge + Metrics)


## Description

Extract and generalize the 5 fundamental hooks that form the context management nervous system. These hooks work together to monitor, warn, preserve, and enhance.


## Objectives

- [ ] Generalize prompt_enhancer.py (remove ANTT-specific, parametrize)
- [ ] Parametrize status_monitor.sh (configurable thresholds)
- [ ] Extract check_context.sh + auto_compact.sh coordination pattern
- [ ] Generalize compact_reinjector.py (configurable rules)
- [ ] Create settings.hooks.json fragment for module registration
- [ ] Validate with 46 golden prompts (EN + PT-BR)


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/hooks-essential/MODULE.md` | Module manifest | 30 |
| `modules/hooks-essential/hooks/prompt_enhancer.py` | Intent classifier + technique injector | 400 |
| `modules/hooks-essential/hooks/prompt_enhancer_config.yaml` | Templates and technique map | 80 |
| `modules/hooks-essential/hooks/status_monitor.sh` | StatusLine context bar | 60 |
| `modules/hooks-essential/hooks/check_context.sh` | PostToolUse context warning | 25 |
| `modules/hooks-essential/hooks/auto_compact.sh` | Stop auto-compaction trigger | 30 |
| `modules/hooks-essential/hooks/compact_reinjector.py` | PreCompact rules preservation | 50 |
| `modules/hooks-essential/settings.hooks.json` | Hook registration fragment | 30 |


## Source Files (extract from)

- `~/.claude/hooks/prompt_enhancer.py (938 lines, 100% accuracy, P99<50ms)`
- `~/.claude/hooks/prompt_enhancer_config.yaml`
- `~/.claude/hooks/status_monitor.sh`
- `~/.claude/hooks/check_context.sh`
- `~/.claude/hooks/auto_compact.sh`
- `analise/.claude/hooks/lifecycle/post_compact_reinjector.py`


## Testing

- **Test directory**: `tests/phase_03/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_prompt_enhancer.py`
  - `test_compact_reinjector.py`
  - `test_golden_prompts.py`


## Acceptance Criteria

- [ ] prompt_enhancer.py classifies 46/46 golden prompts correctly
- [ ] status_monitor.sh shows colored progress bar with configurable threshold
- [ ] auto_compact + check_context coordinate via flag file pattern
- [ ] compact_reinjector preserves configurable rules through compaction
- [ ] All hooks follow fail-open pattern (exit 0 on error)
- [ ] pytest with 90%+ coverage per file


## Tools Required

- Bash, Write, Edit, Agent(general-purpose)


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_03.py
```
Checkpoint saved to: `checkpoints/phase_03.toon`
