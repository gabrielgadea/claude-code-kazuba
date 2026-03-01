# Modules Catalog

Complete catalog of all claude-code-kazuba modules with descriptions, dependencies,
and preset inclusion.

## Module Summary

| Module | Category | Dependencies | Presets |
|--------|----------|-------------|---------|
| core | Foundation | none | minimal, standard, research, professional, enterprise |
| hooks-essential | Hooks | core | standard, research, professional, enterprise |
| hooks-quality | Hooks | core, hooks-essential | professional, enterprise |
| hooks-routing | Hooks | core, hooks-essential | professional, enterprise |
| skills-dev | Skills | none | professional, enterprise |
| skills-meta | Skills | none | standard, research, professional, enterprise |
| skills-planning | Skills | none | standard, research, professional, enterprise |
| skills-research | Skills | none | research, enterprise |
| agents-dev | Agents | none | professional, enterprise |
| commands-dev | Commands | none | professional, enterprise |
| commands-prp | Commands | none | enterprise |
| contexts | Contexts | none | standard, research, professional, enterprise |
| config-hypervisor | Config | none | enterprise |
| team-orchestrator | Orchestration | config-hypervisor | enterprise |
| rlm | Learning Memory | none | enterprise |

## Detailed Descriptions

### core

**Category**: Foundation
**Dependencies**: none
**Presets**: minimal, standard, research, professional, enterprise

The core module is the foundation of every installation. It provides base templates
and universal rules that all other modules build upon.

**Provides**:
- **Templates**: CLAUDE.md, settings.json, settings.local.json, .gitignore
- **Rules**: code-style, security, testing, git-workflow

---

### hooks-essential

**Category**: Hooks
**Dependencies**: core
**Presets**: standard, research, professional, enterprise
**Hook events**: UserPromptSubmit, SessionStart, PreCompact

Essential hook infrastructure for Claude Code sessions: prompt enhancement,
session status monitoring, and context preservation during compaction.

**Provides**:
- `prompt_enhancer.py` — Classifies intent (8 categories) and injects cognitive techniques
- `status_monitor.sh` — Reports session info, git branch, pending TODOs
- `auto_compact.sh` — Saves context checkpoint before compaction
- `session_state_manager.py` — Persists session state across compactions [v0.2.0]
- `post_compact_reinjector.py` — Re-injects critical context after compaction [v0.2.0]

---

### hooks-quality

**Category**: Hooks
**Dependencies**: core, hooks-essential
**Presets**: professional, enterprise
**Hook events**: PreToolUse

Quality and security gate hooks. Prevents bad code, exposed secrets, PII leaks,
and dangerous shell commands from entering the codebase.

**Provides**:
- `quality_gate.py` — File size limits, debug code detection, docstring checks
- `secrets_scanner.py` — API keys, AWS keys, GitHub tokens, OpenAI keys detection
- `pii_scanner.py` — CPF, CNPJ (BR), SSN (US), email, phone (EU) detection
- `bash_safety.py` — Blocks rm -rf /, chmod 777, curl|bash, fork bombs
- `siac_orchestrator.py` — Quality gates with circuit breaker integration [v0.2.0]
- `validate_hooks_health.py` — Periodic health check for all registered hooks [v0.2.0]

---

### hooks-routing

**Category**: Hooks
**Dependencies**: core, hooks-essential
**Presets**: professional, enterprise
**Hook events**: UserPromptSubmit, PreToolUse, PostToolUse

Routing, knowledge management, and compliance tracking. CILA classification
routes prompts by complexity (L0-L6).

**Provides**:
- `cila_router.py` — CILA L0-L6 complexity classification and routing
- `knowledge_manager.py` — 3-tier knowledge injection (cache, project, external)
- `compliance_tracker.py` — Tool usage tracking and audit logging
- `strategy_enforcer.py` — Enforces core governance strategy [v0.2.0]
- `auto_permission_resolver.py` — CILA-aware automatic permission resolution [v0.2.0]
- `ptc_advisor.py` — PTC program advisor with CILA L0-L6 classification [v0.2.0]

---

### skills-dev

**Category**: Skills
**Dependencies**: none
**Presets**: professional, enterprise

Development workflow skills for verification, problem solving, and evaluation.

**Provides**:
- `verification-loop` — 6-phase pre-PR verification (build, typecheck, lint, test, security, diff)
- `supreme-problem-solver` — Last-resort escalation solver with H0/H1/H2 horizons
- `eval-harness` — Evaluation-driven development with measurable before/after

---

### skills-meta

**Category**: Skills
**Dependencies**: none
**Presets**: standard, research, professional, enterprise

Meta-skills for creating and managing hooks, skills, and other Claude Code artifacts.

**Provides**:
- `hook-master` — Create, validate, test, and debug Claude Code hooks
- `skill-master` — Create and manage skills with proper frontmatter and structure
- `skill-writer` — Concise 10-step skill creation workflow

---

### skills-planning

**Category**: Skills
**Dependencies**: none
**Presets**: standard, research, professional, enterprise

Planning skills that transform rough ideas into structured, validated, executable plans.

**Provides**:
- `plan-amplifier` — 8-dimension amplification from Pln1 to Pln-squared
- `plan-execution` — 6-phase execution with checkpoints and recovery
- `code-first-planner` — Generate plans programmatically

---

### skills-research

**Category**: Skills
**Dependencies**: none
**Presets**: research, enterprise

Research skills for academic-quality output with verifiable citations.

**Provides**:
- `academic-research-writer` — Academic writing with IEEE citations and 7-step workflow
- `literature-review` — Systematic literature review with source verification

---

### agents-dev

**Category**: Agents
**Dependencies**: none
**Presets**: professional, enterprise

Development agent definitions with focused roles and specific tool access.

**Provides**:
- `code-reviewer` — Review code for bugs, security, performance, style (sonnet)
- `security-auditor` — OWASP Top 10, secrets, PII, dependency vulnerabilities (sonnet)
- `meta-orchestrator` — Create Claude Code infrastructure (hooks, skills, agents) (opus)

---

### commands-dev

**Category**: Commands
**Dependencies**: none
**Presets**: professional, enterprise

Slash commands for common development workflows.

**Provides**:
- `/debug-RCA` — Structured 6-step Root Cause Analysis
- `/smart-commit` — Intelligent commit with generated message
- `/orchestrate` — Multi-agent orchestration (feature, bugfix, refactor, security)
- `/verify` — Pre-PR verification loop

---

### commands-prp

**Category**: Commands
**Dependencies**: none
**Presets**: enterprise

PRP (Product Requirements Prompt) system for structured product requirements.

**Provides**:
- `/prp-base-create` — Research, generate, ultrathink, output a PRP
- `/prp-base-execute` — Load PRP, plan, implement, verify
- Shared resources: quality-patterns.yml, security-patterns.yml, universal-constants.yml

---

### contexts

**Category**: Contexts
**Dependencies**: none
**Presets**: standard, research, professional, enterprise

Mode-switching contexts that adjust Claude Code behavior for different tasks.

**Provides**:
- `dev` — Fast iteration, relaxed gates, terse responses
- `review` — Strict checks, comprehensive analysis, detailed output
- `research` — Deep exploration, multiple sources, thorough documentation
- `audit` — Compliance focus, evidence-based, full traceability

---

### config-hypervisor

**Category**: Config
**Dependencies**: none
**Presets**: enterprise

Central configuration hub controlling automation behavior, thinking levels,
circuit breakers, and quality gates.

**Provides**:
- `hypervisor.yaml` — Context management, thinking levels, circuit breakers, quality, SLA
- `agent_triggers.yaml` — Declarative agent activation rules
- `event_mesh.yaml` — Event bus categories, priorities, handler routing

---

### team-orchestrator

**Category**: Orchestration
**Dependencies**: config-hypervisor
**Presets**: enterprise

Multi-agent team orchestration with typed models and delegation templates.

**Provides**:
- `config/agents.yaml` — Agent registry with capabilities and SLA
- `config/routing_rules.yaml` — Declarative routing rules
- `config/sla.yaml` — SLA targets and rate limits
- `src/models.py` — Pydantic v2 typed models (TaskRequest, AgentConfig, etc.)
- `templates/task-delegation.md` — Task delegation template
- `templates/status-report.md` — Status report template

---

### rlm

**Category**: Learning Memory
**Dependencies**: none
**Presets**: enterprise
**Version**: v0.2.0

Reinforcement Learning Memory module. Provides semantic recall across sessions using
Q-Table learning, working memory with TTL, and reward-based experience replay.

**Provides**:
- `src/q_table.py` — Q-Table with epsilon-greedy exploration and state hashing
- `src/working_memory.py` — Short-term memory with configurable TTL and priority
- `src/session_manager.py` — Session lifecycle management with TOON checkpoint persistence
- `src/reward_calculator.py` — Multi-factor reward computation (quality, speed, correctness)
- `src/models.py` — Pydantic v2 models (State, Action, Experience, Episode)
- `config/rlm.yaml` — Hyperparameters (learning_rate, discount_factor, epsilon_decay)
- `lib/rlm.py` — Facade integrating all RLM components into a single callable API
