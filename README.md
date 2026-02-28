# Claude Code Kazuba

[![CI](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-723%20passed-brightgreen.svg)](#test-suite)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](#test-suite)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Framework de excelencia para Claude Code** — transforma o Claude Code de um assistente generico
em um sistema de engenharia de software completo com quality gates automaticos, seguranca proativa,
roteamento inteligente de complexidade, e orquestracao multi-agente.

> *"Nao e sobre configurar o Claude Code. E sobre tornar impossivel escrever codigo inseguro,
> entregar sem testes, ou perder contexto no meio do trabalho."*

## O Problema

O Claude Code sem configuracao e poderoso, mas **fragil**:
- Nenhuma protecao contra commitar secrets ou PII
- Sem validacao de qualidade antes de escrever arquivos
- Comandos bash perigosos passam sem alerta
- Sem memoria entre sessoes, sem checkpoints, sem contexto persistente
- Cada projeto comeca do zero — sem reuso de configuracoes testadas

## A Solucao

Kazuba e um sistema modular de **14 modulos** que se instala em qualquer projeto com um unico comando.
Cada modulo resolve um problema real, testado com 723 testes e 97% de coverage:

```bash
./install.sh --preset professional --target /path/to/your/project
```

Em 5 segundos, seu projeto tem:
- **10 hooks automaticos** que interceptam cada acao do Claude Code
- **11 skills** com workflows estruturados (debugging, planning, verification)
- **3 agents especializados** (code review, security audit, meta-orchestrator)
- **6 slash commands** prontos para uso (`/debug-RCA`, `/verify`, `/smart-commit`)
- **4 contextos** que mudam o comportamento conforme a tarefa (dev, review, research, audit)
- **Templates Jinja2** que se adaptam ao stack do projeto automaticamente

## Por Que Kazuba

### Seguranca como Default, Nao como Opcao

```
[PreToolUse] secrets_scanner: BLOCKED — AWS access key detected in config.py
[PreToolUse] bash_safety: BLOCKED — rm -rf / attempted
[PreToolUse] pii_scanner: WARNING — CPF pattern found in user_data.py
[PreToolUse] quality_gate: WARNING — debug print() found in production code
```

4 hooks de seguranca rodam **antes de cada escrita de arquivo** e **antes de cada comando bash**.
Secrets nunca chegam ao git. PII nunca entra no codigo. Comandos destrutivos sao bloqueados.

### Inteligencia na Entrada — Prompt Enhancement + CILA Routing

Cada prompt que voce escreve e automaticamente:
1. **Classificado** em 8 categorias (code, debug, test, refactor, plan, analysis, creative, general)
2. **Enriquecido** com tecnicas cognitivas (chain-of-thought, structured output, constitutional constraints)
3. **Roteado** por complexidade CILA (L0-L6) para calibrar profundidade de resposta

```
[UserPromptSubmit] prompt_enhancer: intent=debug, techniques=[chain_of_thought, few_shot_reasoning, self_validation]
[UserPromptSubmit] cila_router: complexity=L3 (multi-step), routing=detailed_analysis
```

### Modularidade Real — Use So o que Precisa

| Preset | Modulos | Ideal para |
|--------|---------|-----------|
| **minimal** | 1 | Templates e regras basicas |
| **standard** | 5 | Desenvolvimento diario com prompt enhancement |
| **research** | 6 | Projetos academicos com skills de pesquisa |
| **professional** | 10 | Engenharia completa com quality gates e agents |
| **enterprise** | 14 | Orquestracao multi-agente com hypervisor e compliance |

Cada modulo declara dependencias, o installer resolve automaticamente via topological sort.
Nao tem `npm install` que instala o universo — voce escolhe exatamente o que precisa.

### Meta-Code-First — Planos sao Dados, Nao Documentos

O framework foi construido com seu proprio principio: **plans are data, not documents**.
Um script Python de 515 linhas gerou programaticamente todas as 11 fases do plano de construcao,
24 arquivos, 3.463 linhas — com frontmatter YAML, cross-references, validation scripts, e checkpoints.

Este pattern esta disponivel como skill para seus proprios projetos:
```
modules/skills-planning/skills/code-first-planner/SKILL.md
```

## Arquitetura

```
claude-code-kazuba/
├── lib/                    # 7 modulos compartilhados (hook_base, patterns, performance, ...)
├── core/                   # Templates Jinja2 + rules universais (sempre instalado)
├── modules/                # 13 modulos opcionais organizados por categoria
│   ├── hooks-essential/    #   Prompt enhancer, status monitor, auto compact
│   ├── hooks-quality/      #   Secrets, PII, bash safety, quality gate
│   ├── hooks-routing/      #   CILA router, knowledge manager, compliance
│   ├── skills-*/           #   Dev, meta, planning, research (11 skills)
│   ├── agents-dev/         #   Code reviewer, security auditor, meta-orchestrator
│   ├── commands-*/         #   6 slash commands (debug-RCA, verify, smart-commit, ...)
│   ├── config-hypervisor/  #   Central automation config (triggers, events, SLA)
│   ├── contexts/           #   Mode switching (dev, review, research, audit)
│   └── team-orchestrator/  #   Multi-agent coordination (routing, SLA, templates)
├── presets/                # 5 presets (minimal → enterprise)
├── scripts/                # Installer CLI (detect stack, resolve deps, merge settings)
├── install.sh              # One-command installer
└── tests/                  # 723 testes (phase_00 → phase_10 + integration)
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

## Hooks em Detalhe

| Hook | Evento | Modulo | O que faz |
|------|--------|--------|-----------|
| **Prompt Enhancer** | UserPromptSubmit | hooks-essential | Classifica intent (8 categorias) + injeta tecnicas cognitivas |
| **Status Monitor** | SessionStart | hooks-essential | Reports env info (Python, git branch, TODOs pendentes) |
| **Auto Compact** | PreCompact | hooks-essential | Salva checkpoint antes de compactacao de contexto |
| **Quality Gate** | PreToolUse (Write/Edit) | hooks-quality | Limites de tamanho, debug code, docstrings |
| **Secrets Scanner** | PreToolUse (Write/Edit) | hooks-quality | Bloqueia API keys, tokens, credenciais (whitelist para tests) |
| **PII Scanner** | PreToolUse (Write/Edit) | hooks-quality | CPF, CNPJ, SSN, email, telefone (BR/US/EU, warn-only) |
| **Bash Safety** | PreToolUse (Bash) | hooks-quality | rm -rf, chmod 777, curl\|bash, fork bombs |
| **CILA Router** | UserPromptSubmit | hooks-routing | Classificacao L0-L6 com cache (120s TTL) |
| **Knowledge Manager** | PreToolUse | hooks-routing | 3-tier: cache local → docs do projeto → busca externa |
| **Compliance Tracker** | PostToolUse | hooks-routing | Audit logging JSONL + compliance scoring |

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

## Quick Start

```bash
# 1. Clone
git clone https://github.com/gabrielgadea/claude-code-kazuba.git
cd claude-code-kazuba

# 2. Escolha um preset
cat presets/standard.txt        # Ver modulos incluidos
cat presets/professional.txt    # Mais completo

# 3. Instale no seu projeto
./install.sh --preset standard --target /path/to/your/project

# 4. (Opcional) Dry-run para ver o plano sem instalar
./install.sh --preset enterprise --target /path/to/your/project --dry-run
```

O installer:
1. **Detecta** o stack do projeto (Python, Rust, JS, TS, Go, Java)
2. **Resolve** dependencias entre modulos (topological sort)
3. **Renderiza** templates Jinja2 com variaveis do projeto
4. **Instala** hooks, skills, agents, commands em `.claude/`
5. **Merge** settings.json sem sobrescrever configuracoes existentes
6. **Valida** a instalacao com health check automatico

## Documentacao

| Documento | Descricao |
|-----------|-----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design completo, estrutura, algoritmos, decisoes |
| [HOOKS_REFERENCE.md](docs/HOOKS_REFERENCE.md) | Todos os 18 eventos de hook com JSON schemas |
| [MODULES_CATALOG.md](docs/MODULES_CATALOG.md) | Catalogo completo com dependencias e presets |
| [CREATING_MODULES.md](docs/CREATING_MODULES.md) | Guia para criar modulos customizados |
| [MIGRATION.md](docs/MIGRATION.md) | Migracao para usuarios com `.claude/` existente |

## Test Suite

```
============================= 723 passed in 1.34s ==============================
```

| Metrica | Valor |
|---------|-------|
| Testes | 723 |
| Coverage (lib/) | 97% |
| Coverage target | 90% per file |
| Lint (ruff) | 0 errors |
| Format (ruff) | 0 reformats |
| Types (pyright strict) | 0 errors |
| CI | GitHub Actions (lint + typecheck + test) |

Testes organizados por fase de desenvolvimento (phase_00 → phase_10) + integration tests
para cada preset.

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

## Roadmap

- [ ] **Rust Acceleration Layer** — Hooks em Rust via PyO3/maturin para performance critica
- [ ] **RLM (Reinforced Learning Memory)** — Sistema de aprendizado com semantic recall entre sessoes
- [ ] **Agent Triggers Avancados** — Dispatch automatico baseado em complexidade/dominio/falhas
- [ ] **Recovery Triggers** — Escalacao automatica em cadeia de falhas
- [ ] **GPU Acceleration** — Embeddings e similarity via CUDA/Metal
- [ ] **Core Governance** — CODE-FIRST enforcement com zero-hallucination protocol

## Contribuindo

1. Fork o repositorio
2. Crie uma branch (`git checkout -b feature/my-module`)
3. Escreva testes primeiro (TDD)
4. Implemente as mudancas
5. Rode o quality gate: `ruff check && ruff format --check && pyright lib/ && pytest tests/`
6. Abra um Pull Request

Veja [CREATING_MODULES.md](docs/CREATING_MODULES.md) para o guia completo de criacao de modulos.

## Licenca

MIT License. Veja [pyproject.toml](pyproject.toml) para detalhes.

---

**Construido com o proprio principio meta-code-first — o framework que se auto-hospeda.**
