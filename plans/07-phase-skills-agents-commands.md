      ---
      plan: claude-code-kazuba
      version: "2.0"
      phase: 6
      title: "Skills + Agents + Commands"
      effort: "L"
      estimated_tokens: 15000
      depends_on: [0]
      parallel_group: "content"
      context_budget: "1 context window (~180k tokens)"
      validation_script: "validation/validate_phase_06.py"
      checkpoint: "checkpoints/phase_06.toon"
      status: "pending"
      cross_refs:
        - {file: "00-phase-bootstrap-&-scaffolding.md", relation: "depends_on"}
- {file: "08-phase-installer-cli.md", relation: "blocks"}
      ---

# Phase 6: Skills + Agents + Commands

**Effort**: L | **Tokens**: ~15,000 | **Context**: 1 context window (~180k tokens)

**Dependencies**: Phase 0

**Parallel with**: Phase 7 (Config + Contexts + Team Orchestrator)


## Description

Extract and generalize reusable skills, agent definitions, and slash commands from all 4 source configurations.


## Objectives

- [ ] Extract meta-skills: hook-master, skill-master, skill-writer
- [ ] Extract dev skills: verification-loop, supreme-problem-solver, eval-harness
- [ ] Extract planning skills: plan-amplifier, plan-execution
- [ ] Extract research skills: academic-research-writer, literature-review, scientific-writing
- [ ] Create dev agents: code-reviewer, performance-analyzer, security-auditor, meta-orchestrator
- [ ] Extract commands: debug-RCA, smart-commit, orchestrate, verify
- [ ] Extract PRP system with shared YAML patterns


## Files to Create

| Path | Description | Min Lines |
|------|-------------|-----------|
| `modules/skills-meta/MODULE.md` | Module manifest | 20 |
| `modules/skills-meta/skills/hook-master/SKILL.md` | Meta-skill for hooks | 200 |
| `modules/skills-meta/skills/skill-master/SKILL.md` | Meta-skill for skills | 200 |
| `modules/skills-meta/skills/skill-writer/SKILL.md` | Guide for skill creation | 100 |
| `modules/skills-dev/MODULE.md` | Module manifest | 20 |
| `modules/skills-dev/skills/verification-loop/SKILL.md` | 6-phase pre-PR | 100 |
| `modules/skills-dev/skills/supreme-problem-solver/SKILL.md` | H0/H1/H2 escalation | 120 |
| `modules/skills-dev/skills/eval-harness/SKILL.md` | Eval-driven dev | 80 |
| `modules/skills-planning/MODULE.md` | Module manifest | 20 |
| `modules/skills-planning/skills/plan-amplifier/SKILL.md` | 8-dim amplification | 150 |
| `modules/skills-planning/skills/plan-execution/SKILL.md` | Checkpoint execution | 120 |
| `modules/skills-research/MODULE.md` | Module manifest | 20 |
| `modules/skills-research/skills/academic-research-writer/SKILL.md` | Academic writing | 100 |
| `modules/skills-research/skills/literature-review/SKILL.md` | Literature review | 80 |
| `modules/agents-dev/MODULE.md` | Module manifest | 20 |
| `modules/agents-dev/agents/code-reviewer.md` | Code review agent | 60 |
| `modules/agents-dev/agents/security-auditor.md` | Security audit agent | 60 |
| `modules/agents-dev/agents/meta-orchestrator.md` | Meta-orchestrator agent | 80 |
| `modules/commands-dev/MODULE.md` | Module manifest | 20 |
| `modules/commands-dev/commands/debug-RCA.md` | Structured RCA | 60 |
| `modules/commands-dev/commands/smart-commit.md` | Intelligent commits | 40 |
| `modules/commands-dev/commands/orchestrate.md` | Multi-agent orchestration | 60 |
| `modules/commands-dev/commands/verify.md` | Pre-PR verification | 40 |
| `modules/commands-prp/MODULE.md` | Module manifest | 20 |
| `modules/commands-prp/commands/prp-base-create.md` | PRP creation | 60 |
| `modules/commands-prp/commands/prp-base-execute.md` | PRP execution | 60 |
| `modules/commands-prp/commands/shared/quality-patterns.yml` | Quality YAML | 30 |
| `modules/commands-prp/commands/shared/security-patterns.yml` | Security YAML | 30 |


## Source Files (extract from)

- `kazuba-cargo/.claude/skills/hook-master/SKILL.md`
- `kazuba-cargo/.claude/skills/skill-master/SKILL.md`
- `kazuba-cargo/.claude/skills/supreme-problem-solver/SKILL.md`
- `kazuba-cargo/.claude/skills/verification-loop/SKILL.md`
- `kazuba-cargo/.claude/skills/eval-harness/SKILL.md`
- `~/.claude/skills/plan-amplifier/SKILL.md`
- `~/.claude/skills/plan-execution/SKILL.md`
- `~/.claude/skills/academic-research-writer/SKILL.md`
- `kazuba-cargo/.claude/agents/claude-code-meta-orchestrator.md`
- `transferegov/.claude/commands/development/debug-RCA.md`
- `transferegov/.claude/commands/development/smart-commit.md`
- `transferegov/.claude/commands/PRPs/prp-base-create.md`


## Testing

- **Test directory**: `tests/phase_06/`
- **Min coverage per file**: 90%
- **Test files**:
  - `test_skill_frontmatter.py`
  - `test_agent_frontmatter.py`
  - `test_command_structure.py`


## Acceptance Criteria

- [ ] All SKILL.md files have valid YAML frontmatter
- [ ] All agent .md files have valid frontmatter with required fields
- [ ] All commands follow Claude Code command format
- [ ] Shared YAML patterns are valid YAML
- [ ] No domain-specific (ANTT/TIR) content in generalized files


## Tools Required

- Write, Edit, Bash, Agent(general-purpose)


## Checkpoint

After completing this phase, run:
```bash
python plans/validation/validate_phase_06.py
```
Checkpoint saved to: `checkpoints/phase_06.toon`
