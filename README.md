# Claude Code Kazuba

[![CI](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1567%20passed-brightgreen.svg)](#test-suite)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](#test-suite)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Claude Code sem configuracao comete erros que voce so descobre no code review.**
Kazuba instala 15 modulos em 5 segundos — hooks que bloqueiam secrets, validam qualidade e
persistem contexto automaticamente, sem nenhuma configuracao manual.

```
[PreToolUse] secrets_scanner: BLOCKED — AWS access key detected in config.py
[PreToolUse] bash_safety:     BLOCKED — rm -rf / attempted
[PreToolUse] pii_scanner:     WARNING — CPF pattern found in user_data.py
[UserPromptSubmit] cila_router: complexity=L3 → routing=detailed_analysis
```

---

## Quick Start

```bash
# Instalar em qualquer projeto existente
git clone https://github.com/gabrielgadea/claude-code-kazuba.git
cd claude-code-kazuba
./install.sh --preset standard --target /path/to/your/project

# Ou via curl (remote install)
curl -sL https://raw.githubusercontent.com/gabrielgadea/claude-code-kazuba/main/install.sh \
  | bash -s -- --preset standard --target /path/to/your/project

# Ver o que sera instalado sem escrever nada
./install.sh --preset professional --target /path/to/your/project --dry-run
```

Em 5 segundos, seu projeto Claude Code tem:

| O que voce ganha | Como |
|-----------------|------|
| Nenhum secret vai para o git | Hooks bloqueiam antes de escrever |
| Qualidade checada em cada arquivo | Quality gate pre-escrita |
| Contexto persistente entre sessoes | Checkpoints automaticos |
| Prompts enriquecidos automaticamente | Classificacao + tecnicas cognitivas |
| Stack-aware (Python, Rust, TS, Go...) | Deteccao automatica + templates Jinja2 |

---

## Presets

| Preset | Modulos | Ideal para |
|--------|---------|-----------|
| **minimal** | 1 | Templates e regras basicas |
| **standard** | 5 | Desenvolvimento diario + prompt enhancement |
| **research** | 6 | Projetos academicos com skills de pesquisa |
| **professional** | 10 | Engenharia completa com quality gates e agents |
| **enterprise** | 14 | Orquestracao multi-agente + hypervisor + compliance |

Cada modulo declara dependencias; o installer resolve via topological sort. Sem `npm install` que
instala o universo — voce escolhe exatamente o que precisa.

---

## Por Que Kazuba

### Seguranca Como Default

4 hooks rodam **antes de cada escrita de arquivo** e **antes de cada comando bash**:

```
[PreToolUse] secrets_scanner: BLOCKED — AWS access key detected in config.py
[PreToolUse] bash_safety:     BLOCKED — rm -rf / attempted
[PreToolUse] pii_scanner:     WARNING — CPF pattern found in user_data.py
[PreToolUse] quality_gate:    WARNING — debug print() found in production code
```

Secrets nunca chegam ao git. PII nunca entra no codigo. Comandos destrutivos sao bloqueados.

### Prompt Enhancement + Roteamento CILA

Cada prompt e automaticamente:
1. **Classificado** em 8 categorias (code, debug, test, refactor, plan, analysis, creative, general)
2. **Enriquecido** com tecnicas cognitivas (chain-of-thought, structured output, constitutional constraints)
3. **Roteado** por complexidade CILA (L0-L6) para calibrar profundidade de resposta

```
[UserPromptSubmit] prompt_enhancer: intent=debug → chain_of_thought + few_shot + self_validation
[UserPromptSubmit] cila_router: complexity=L3 (multi-step) → routing=detailed_analysis
```

### Modularidade Real

Cada modulo em `modules/` tem:
- `MODULE.md` — manifest com nome, descricao, dependencias
- `hooks/`, `skills/`, `agents/`, `commands/`, `config/`, `contexts/`
- `settings.hooks.json` — fragment de hook registration (merge automatico)

### Meta-Code-First — O Framework Se Auto-Hospeda

Construido com seu proprio principio: **plans are data, not documents**.
Um script Python de 515 linhas gerou programaticamente todas as 23 fases do plano,
24 arquivos, 3.463 linhas — com frontmatter YAML, cross-references e checkpoints msgpack.

```
modules/skills-planning/skills/code-first-planner/SKILL.md
```

---

## Exemplos Praticos

Veja `examples/` para projetos-demo com antes/depois:

- [`examples/python-api/`](examples/python-api/) — FastAPI: hooks interceptando commit de credencial
- [`examples/rust-cli/`](examples/rust-cli/) — CLI Rust: bash safety em acao
- [`examples/typescript-web/`](examples/typescript-web/) — Next.js: quality gate + PII scanner

---

## Arquitetura

```
claude-code-kazuba/
├── lib/                    # 8 modulos compartilhados (hook_base, patterns, config, rlm, ...)
├── core/                   # Templates Jinja2 + rules universais (sempre instalado)
├── modules/                # 15 modulos opcionais organizados por categoria
│   ├── hooks-essential/    #   Prompt enhancer, status monitor, auto compact
│   ├── hooks-quality/      #   Secrets, PII, bash safety, quality gate
│   ├── hooks-routing/      #   CILA router, knowledge manager, compliance
│   ├── skills-*/           #   Dev, meta, planning, research (11 skills)
│   ├── agents-dev/         #   Code reviewer, security auditor, meta-orchestrator
│   ├── commands-*/         #   6 slash commands (debug-RCA, verify, smart-commit, ...)
│   ├── config-hypervisor/  #   Central automation config (triggers, events, SLA)
│   ├── contexts/           #   Mode switching (dev, review, research, audit)
│   ├── team-orchestrator/  #   Multi-agent coordination (routing, SLA, templates)
│   └── rlm/                #   RLM Learning Memory (Q-Table, WorkingMemory, RewardCalc)
├── presets/                # 5 presets (minimal → enterprise)
├── examples/               # Projetos-demo com antes/depois (Python, Rust, TypeScript)
├── scripts/                # Installer CLI (detect stack, resolve deps, merge settings)
├── install.sh              # One-command installer
└── tests/                  # 1567 testes (phase_00 → phase_22 + integration_v2)
```

### Principios de Design

| Principio | Implementacao |
|-----------|--------------|
| **Fail-Open** | Hooks nunca crasham o Claude Code — erro interno = exit 0 |
| **Zero Config** | `./install.sh --preset standard` e tudo que voce precisa |
| **Composable** | Cada modulo e independente com dependencias explicitas |
| **TDD** | 90% coverage per file (nao media), todos os hooks testados |
| **Type-Safe** | Pydantic v2 para configs, pyright strict para lib/ |
| **Checkpoint** | TOON format (msgpack + header) para recovery de estado |
| **Stack-Aware** | Detecta Python/Rust/JS/TS/Go/Java e adapta templates |

---

## Hooks em Detalhe

| Hook | Evento | Modulo | O que faz |
|------|--------|--------|-----------|
| **Prompt Enhancer** | UserPromptSubmit | hooks-essential | Classifica intent (8 categorias) + injeta tecnicas cognitivas |
| **Status Monitor** | SessionStart | hooks-essential | Reports env info (Python, git branch, TODOs pendentes) |
| **Auto Compact** | PreCompact | hooks-essential | Salva checkpoint antes de compactacao de contexto |
| **Session State Manager** | SessionStart/Stop | hooks-essential | Persistencia de estado entre sessoes (v0.2.0) |
| **Post Compact Reinjector** | PreCompact | hooks-essential | Reinjecao de contexto critico pos-compactacao (v0.2.0) |
| **Quality Gate** | PreToolUse (Write/Edit) | hooks-quality | Limites de tamanho, debug code, docstrings |
| **Secrets Scanner** | PreToolUse (Write/Edit) | hooks-quality | Bloqueia API keys, tokens, credenciais (whitelist para tests) |
| **PII Scanner** | PreToolUse (Write/Edit) | hooks-quality | CPF, CNPJ, SSN, email, telefone (BR/US/EU, warn-only) |
| **Bash Safety** | PreToolUse (Bash) | hooks-quality | rm -rf, chmod 777, curl\|bash, fork bombs |
| **SIAC Orchestrator** | PreToolUse | hooks-quality | Quality gates com circuit breaker (v0.2.0) |
| **Validate Hooks Health** | Heartbeat | hooks-quality | Health check periodico de todos os hooks (v0.2.0) |
| **CILA Router** | UserPromptSubmit | hooks-routing | Classificacao L0-L6 com cache (120s TTL) |
| **Knowledge Manager** | PreToolUse | hooks-routing | 3-tier: cache local → docs do projeto → busca externa |
| **Compliance Tracker** | PostToolUse | hooks-routing | Audit logging JSONL + compliance scoring |
| **Auto Permission Resolver** | PreToolUse | hooks-routing | Resolucao automatica de permissoes CILA-aware (v0.2.0) |
| **PTC Advisor** | UserPromptSubmit | hooks-routing | Advisor de complexidade CILA L0-L6 (v0.2.0) |

---

## Skills, Agents e Commands

### Skills (11 workflows estruturados)

| Skill | Modulo | Descricao |
|-------|--------|-----------|
| Code-First Planner | skills-planning | Gera planos via Python (meta-code-first pattern) |
| Plan Amplifier | skills-planning | Amplifica planos em 8 dimensoes com scoring matrix |
| Plan Execution | skills-planning | Execucao em 6 fases com checkpoints e recovery |
| Verification Loop | skills-dev | Verificacao pre-PR em 6 fases (build, type, lint, test, sec, diff) |
| Supreme Problem Solver | skills-dev | Escalacao H0/H1/H2 com decision matrix |
| Eval Harness | skills-dev | Eval-driven development com scoring formula |
| Skill Master | skills-meta | Criar skills com estrutura correta |
| Skill Writer | skills-meta | 10-step skill creation workflow |
| Hook Master | skills-meta | Criar e debugar hooks do Claude Code |
| Academic Research Writer | skills-research | Pesquisa academica com citacoes IEEE |
| Literature Review | skills-research | Revisao sistematica com gap analysis |

### Agents (3 especialistas)

| Agent | Modelo | Foco |
|-------|--------|------|
| **Code Reviewer** | Sonnet | Correcao, seguranca, performance, estilo (4 dimensoes) |
| **Security Auditor** | Sonnet | OWASP Top 10, secrets, PII, CVSS ratings |
| **Meta Orchestrator** | Opus | Decide: HOOK vs SKILL vs AGENT vs MCP vs SETTINGS |

### Commands (6 slash commands)

| Comando | Descricao |
|---------|-----------|
| `/debug-RCA` | Root Cause Analysis em 6 passos (capture, hypothesize, evidence, root cause, fix, prevent) |
| `/smart-commit` | Analisa diff, classifica tipo, gera mensagem conventional commits |
| `/orchestrate` | Orquestracao multi-agente (4 modos: feature, bugfix, refactor, security) |
| `/verify` | Verificacao pre-PR invocando verification-loop skill |
| `/prp-base-create` | Criar Product Requirements Prompt (pesquisa + geracao + ultrathink) |
| `/prp-base-execute` | Executar PRP (load + plan + implement + verify) |

---

## Test Suite

```
============================= 1567 passed in 3.01s =============================
```

| Metrica | Valor |
|---------|-------|
| Testes | 1567 (723 v0.1.0 + 844 v0.2.0) |
| Coverage (lib/) | 97% |
| Coverage target | 90% per file |
| Lint (ruff) | 0 errors |
| Format (ruff) | 0 reformats |
| Types (pyright strict) | 0 errors |
| CI | GitHub Actions (lint + typecheck + test) |

Testes organizados por fase (phase_00 → phase_22) + integration tests por preset
e `integration_v2/` para os novos componentes v0.2.0.

---

## Documentacao

| Documento | Descricao |
|-----------|-----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design completo, estrutura, algoritmos, decisoes |
| [HOOKS_REFERENCE.md](docs/HOOKS_REFERENCE.md) | Todos os 18 eventos de hook com JSON schemas |
| [MODULES_CATALOG.md](docs/MODULES_CATALOG.md) | Catalogo completo com dependencias e presets |
| [CREATING_MODULES.md](docs/CREATING_MODULES.md) | Guia para criar modulos customizados |
| [MIGRATION.md](docs/MIGRATION.md) | Migracao para usuarios com `.claude/` existente |
| [GLOSSARY.md](docs/GLOSSARY.md) | Terminologia: Kazuba, CILA, TOON, RLM, presets |

---

## Desenvolvimento

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Quality gate completo
pytest tests/ --cov=lib --cov-report=term-missing
ruff check lib/ scripts/ tests/
ruff format --check lib/ scripts/ tests/
pyright lib/
```

---

## O que ha de novo na v0.2.0

- [x] **Shared Infrastructure** — CircuitBreaker, TraceManager, HookLogger, EventBus
- [x] **Rust Acceleration Layer** — Stub + bridge PyO3 para hooks performance-criticos
- [x] **Core Governance + CILA Formal** — Taxonomia CILA L0-L6, StrategyEnforcer, governance rules
- [x] **Agent Triggers + Recovery** — Dispatch declarativo e escalacao automatica
- [x] **Hypervisor Executable** — Hypervisor, HypervisorV2, HypervisorBridge
- [x] **Advanced Hooks Batch 1** — SessionStateManager, PostCompactReinjector, ValidateHooksHealth
- [x] **Advanced Hooks Batch 2** — SiacOrchestrator, AutoPermissionResolver, PtcAdvisor
- [x] **RLM Learning Memory** — QTable, WorkingMemory, SessionManager, RewardCalculator, facade
- [x] **Integration + Migration** — E2E tests, migrate_v01_v02.py, MIGRATION.md
- [x] **Benchmark Suite** — benchmark_hooks.py CLI + self_host_config.py
- [ ] **GPU Acceleration** — Embeddings e similarity via CUDA/Metal (roadmap v0.3.0)

## Roadmap

- [ ] **GPU Acceleration** — Embeddings e similarity via CUDA/Metal
- [ ] **Multi-tenant Isolation** — Isolamento de contexto por workspace
- [ ] **Web Dashboard** — Visualizacao de metricas de hooks em tempo real

---

## Contribuindo

1. Fork o repositorio
2. Crie uma branch (`git checkout -b feature/my-module`)
3. Escreva testes primeiro (TDD, 90% coverage por arquivo)
4. Implemente as mudancas
5. Rode o quality gate: `ruff check && ruff format --check && pyright lib/ && pytest tests/`
6. Abra um Pull Request

Veja [CREATING_MODULES.md](docs/CREATING_MODULES.md) para o guia completo.

---

## Licenca

MIT License. Veja [pyproject.toml](pyproject.toml) para detalhes.

---

*Construido com o proprio principio meta-code-first — o framework que se auto-hospeda.*
