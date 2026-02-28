      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 8
      title: "Installer CLI"
      effort: "L"
      estimated_tokens: 15000
      depends_on: [1, 2, 3, 4, 5, 6, 7]
      parallel_group: null
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_08.py"
      checkpoint: "checkpoints/phase_08.toon"
      status: "pending"
      cross_refs:
        - {file: "01-phase-shared-library-lib-.md", relation: "depends_on"}
- {file: "02-phase-core-module.md", relation: "depends_on"}
- {file: "03-phase-hooks-essential-module.md", relation: "depends_on"}
- {file: "04-phase-hooks-quality-security.md", relation: "depends_on"}
- {file: "05-phase-hooks-routing-knowledge-metrics.md", relation: "depends_on"}
- {file: "06-phase-skills-agents-commands.md", relation: "depends_on"}
- {file: "07-phase-config-contexts-team-orchestrator.md", relation: "depends_on"}
- {file: "09-phase-presets-integration-tests.md", relation: "blocks"}
      ---

# Phase 8: Installer CLI

**Effort**: L | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7


## Description

Build the interactive installer CLI that detects project stack, offers presets, and installs selected modules with intelligent merging.


## Objectives

- [ ] Create install.sh with argument parser (--preset, --modules, --target, --dry-run)
- [ ] Implement stack detection (Python/Rust/JS/TS/Go/Java via manifest files)
- [ ] Implement preset system (minimal/standard/professional/enterprise/research)
- [ ] Implement module selection with dependency resolution
- [ ] Implement settings.json merge algorithm (append hooks, don't overwrite)
- [ ] Implement template variable substitution
- [ ] Create validate_installation.py post-install health check
- [ ] Support remote install via curl | bash


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `install.sh` | Main installer CLI script | 300 |
| `scripts/install_module.py` | Python module installer helper | 150 |
| `scripts/merge_settings.py` | Settings.json merge algorithm | 100 |
| `scripts/detect_stack.py` | Project stack auto-detection | 60 |
| `scripts/resolve_deps.py` | Module dependency DAG resolver | 80 |
| `scripts/validate_installation.py` | Post-install health check | 80 |
| `presets/minimal.txt` | Core only | 5 |
| `presets/standard.txt` | Core + essential hooks + meta skills | 10 |
| `presets/professional.txt` | Standard + quality + security + agents | 15 |
| `presets/enterprise.txt` | Professional + team + hypervisor | 18 |
| `presets/research.txt` | Standard + research + planning skills | 12 |


## Testing

- **Test directory**: `tests/phase_08/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_installer.py`
  - `test_merge_settings.py`
  - `test_detect_stack.py`
  - `test_resolve_deps.py`
  - `test_validate_installation.py`


## Acceptance Criteria

- [ ] install.sh --preset minimal --target /tmp/test works E2E
- [ ] install.sh --dry-run shows plan without writing files
- [ ] Stack detection identifies Python, Rust, JS, TS, Go
- [ ] Settings merge appends hooks without overwriting user config
- [ ] Dependency resolver detects cycles and reports errors
- [ ] validate_installation.py reports all checks green
- [ ] 90%+ coverage per script file


## Tools Required

- Bash, Write, Edit


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_08.py
```
Checkpoint saved to: `checkpoints/phase_08.toon`
