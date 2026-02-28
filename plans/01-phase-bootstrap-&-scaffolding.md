      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 0
      title: "Bootstrap & Scaffolding"
      effort: "S"
      estimated_tokens: 8000
      depends_on: []
      parallel_group: null
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_00.py"
      checkpoint: "checkpoints/phase_00.toon"
      status: "pending"
      cross_refs:
        - {file: "01-phase-shared-library-lib-.md", relation: "blocks"}
- {file: "06-phase-skills-agents-commands.md", relation: "blocks"}
- {file: "07-phase-config-contexts-team-orchestrator.md", relation: "blocks"}
      ---

# Phase 0: Bootstrap & Scaffolding

**Effort**: S | **Tokens**: ~8,000 | **Context**: 1 context window (~180k tokens)


## Description

Initialize the repository with complete project structure, dependency management, git configuration, and foundational files. This phase establishes the skeleton that all subsequent phases build upon.


## Objectives

- [ ] Create complete directory tree for all 20+ modules
- [ ] Initialize git repo with .gitignore and LICENSE (MIT)
- [ ] Create pyproject.toml with all dependencies pinned
- [ ] Create .venv with Python 3.12+
- [ ] Initialize .claude/ config for the project itself (self-hosting)
- [ ] Create CLAUDE.md for the framework project


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `pyproject.toml` | Project metadata, dependencies, tool configs | 40 |
| `.gitignore` | Git ignore patterns | 20 |
| `LICENSE` | MIT License | 20 |
| `README.md` | Project overview, quick start, badges | 50 |
| `lib/__init__.py` | Package init with version | 5 |
| `tests/__init__.py` | Test package init | 1 |
| `tests/conftest.py` | Shared fixtures for all tests | 20 |
| `.claude/CLAUDE.md` | Self-hosting config for framework dev | 30 |
| `.claude/settings.json` | Project settings with hooks stubs | 20 |


## Implementation Strategy

1. Create all directories in single `mkdir -p` command
2. Write pyproject.toml with:
   - `[project]` metadata (name, version, description, requires-python>=3.12)
   - `[project.dependencies]`: pydantic>=2.10, msgpack>=1.1, pyyaml>=6.0, jinja2>=3.1
   - `[project.optional-dependencies.dev]`: pytest>=8.3, pytest-cov>=6.0, ruff>=0.8, pyright>=1.1.390
   - `[tool.ruff]`: line-length=99, target-version="py312"
   - `[tool.pyright]`: pythonVersion="3.12", typeCheckingMode="strict"
   - `[tool.pytest.ini_options]`: testpaths=["tests"], addopts="--strict-markers -v"
3. Write .gitignore (Python + .claude/settings.local.json + .venv + checkpoints/*.toon)
4. git init && git add && git commit -m "feat: bootstrap project structure"


## Testing

- **Test directory**: `tests/phase_00/`
- **Min coverage per file**: 100%
- **Test files**:
  - `test_structure.py`


## Acceptance Criteria

- [ ] All directories exist per layout spec
- [ ] pyproject.toml valid (pip install -e . succeeds)
- [ ] .venv created with Python 3.12+
- [ ] git init with initial commit
- [ ] validate_phase_00.py passes all checks


## Tools Required

- Bash, Write, Edit


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_00.py
```
Checkpoint saved to: `checkpoints/phase_00.toon`
