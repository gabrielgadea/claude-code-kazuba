# Claude Code Kazuba

[![CI](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1567%20passed-brightgreen.svg)](#test-suite)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](#test-suite)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

O framework "Claude Code Kazuba" transforma Claude Code em um **Meta Code Orchestrator** — uma IA que nao
apenas escreve codigo, mas *governa a si mesma* atraves de tres camadas:
**CLAUDE.md** diz como pensar, **Hooks** impedem erros em tempo real,
e **Rust** faz tudo isso sem latencia perceptivel.

```
[PreToolUse] secrets_scanner: BLOCKED — AWS access key detected in config.py
[PreToolUse] bash_safety:     BLOCKED — rm -rf / attempted
[PreToolUse] pii_scanner:     WARNING — CPF pattern found in user_data.py
[UserPromptSubmit] cila_router: complexity=L3 → routing=detailed_analysis
```

![Kazuba Demo](docs/demo/kazuba-demo.gif)

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

| O que voce ganha | Camada responsavel |
|-----------------|-------------------|
| Nenhum secret vai para o git | Hook `secrets_scanner` (enforcement) |
| Qualidade checada em cada arquivo | Hook `quality_gate` (enforcement) |
| Contexto persistente entre sessoes | Checkpoints TOON (diretiva) |
| Prompts enriquecidos automaticamente | Hook `prompt_enhancer` + CILA (enforcement) |
| Stack-aware (Python, Rust, TS, Go...) | Templates Jinja2 (diretiva) |
| Deteccao de padroes em nanosegundos | Aho-Corasick (aceleracao Rust) |

O que acabou de acontecer por baixo e o resultado de tres camadas arquiteturais
trabalhando em conjunto. Entenda cada uma delas — e por que a ordem importa.

---

## A Tese: Meta Code Orchestrator

Claude Code sem Kazuba e uma ferramenta que escreve codigo. Com Kazuba, e um
**orchestrator que governa a si mesmo** — sabe como pensar, e impedido de errar,
e faz isso sem friccao.

A arquitetura se organiza em tres camadas, cada uma resolvendo uma limitacao
especifica da anterior:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — CLAUDE.md (Diretiva)                         │
│  "Como Claude deve pensar e planejar"                   │
│  Plans as code, Meta-Code-First, CILA taxonomy          │
├─────────────────────────────────────────────────────────┤
│  Layer 2 — Hooks (Enforcement)                          │
│  "O que Claude nao pode fazer"                          │
│  16 hooks: secrets, PII, bash, quality, routing         │
├─────────────────────────────────────────────────────────┤
│  Layer 3 — Rust (Aceleracao)                            │
│  "Fazer tudo isso sem que o dev perceba"                │
│  7.137 linhas, Aho-Corasick, PyO3, fallback graceful   │
└─────────────────────────────────────────────────────────┘
```

A ordem nao e acidental. Diretivas definem o comportamento desejado. Enforcement
garante que o comportamento real corresponde ao desejado. Aceleracao torna o
enforcement invisivel. Remova qualquer camada e o sistema degrada:
sem diretivas, os hooks nao sabem o que proteger; sem hooks, as diretivas
sao sugestoes ignoraveis; sem Rust, o enforcement vira friccao que o
desenvolvedor desliga.

As secoes seguintes examinam cada camada em detalhe.

---

## Layer 1 — CLAUDE.md: A Camada Diretiva

Antes de interceptar erros, Claude precisa saber **como pensar**. O `CLAUDE.md`
instalado pelo Kazuba define regras, principios e templates que orientam cada
decisao do Claude Code — desde a forma de nomear variaveis ate a profundidade de
analise por nivel de complexidade.

Mas o diferencial nao esta nas regras em si. Esta em como elas sao geradas.

### Meta-Code-First: O Plano E Codigo

O `CLAUDE.md` do Kazuba define um principio fundamental: *"Plans are data, not
documents."* E aplica esse principio a si mesmo — o proprio plano de
desenvolvimento do framework e codigo executavel, nao markdown manual.

```bash
python scripts/generate_plan.py --output-dir plans/ --validate
# → 24 arquivos markdown + 24 scripts de validacao + orquestrador
```

Um script Python gera programaticamente todas as 24 fases do
plano (se o plano for extenso assim), com frontmatter YAML padronizado, cross-references validadas e scripts de
validacao por fase. A consequencia direta: mudar o plano significa mudar dados em
Python e regenerar — nao cacar inconsistencias em 24 arquivos markdown.

**5 camadas de geracao/validacao:**

```
generate_plan.py (Python)
    → gera validate_phase_XX.py (Python que valida codigo)
        → que roda pytest (que valida implementacao)
            → que testa hooks (que validam codigo do usuario)
                → que usam Rust (que valida padroes em O(n))
```

O que torna esse pattern poderoso e a recursividade: codigo gera codigo que gera
codigo que valida codigo. Claude Code opera nao como editor, mas como
**orquestrador de um plano compilavel** — le o gerador, executa-o, implementa os
arquivos definidos, roda a validacao, e itera se algo falhar.

| Plano Manual | Plano Code-First (Kazuba) |
|---|---|
| Cada autor formata diferente | Frontmatter YAML por template — zero divergencia |
| Revisao humana, subjetiva | `--validate` verifica existencia, cross-refs, schemas |
| Editar 24 arquivos, cacar refs | Editar dados Python, regenerar idempotentemente |
| `git diff` em markdown e ruido | `git diff` em Python mostra mudanca semantica |

<details>
<summary><strong>Claude Code como orchestrator (detalhes)</strong></summary>

No contexto do Kazuba, o fluxo de trabalho de Claude Code e:

1. **Le** `generate_plan.py` para entender a fase atual
2. **Executa** o gerador para criar/atualizar o plano
3. **Implementa** os arquivos definidos em `files_to_create`
4. **Roda** `validate_phase_XX.py` para verificar completude
5. **Itera** se validacao falhar

Cada fase define `AgentSpec` para subagentes paralelos com worktree isolation.
Cada agente trabalha em branch propria, merge coordenado pelo orquestrador.
A distincao entre "planejar" e "implementar" colapsa — o plano e executavel, a
implementacao e validavel, e a validacao e gerada automaticamente.

</details>

Diretivas, porem, sao intencoes declaradas. Nao importa quao preciso o
`CLAUDE.md` seja — sem um mecanismo de enforcement, diretivas sao sugestoes que
Claude pode ignorar. Por isso a proxima camada existe.

---

## Layer 2 — Hooks: A Camada de Enforcement

Saber o que fazer nao impede erros — **interceptar** impede. Os hooks do Kazuba
operam em eventos do Claude Code (`PreToolUse`, `UserPromptSubmit`, `PostToolUse`)
e tomam decisoes em tempo real: bloquear (exit 2), alertar (exit 0 com warning),
ou enriquecer contexto.

Sao 16 hooks organizados em tres modulos, cada um com uma funcao especifica na
cadeia de governanca:

### Seguranca (hooks-quality)

4 hooks rodam **antes** de cada escrita de arquivo e **antes** de cada comando bash:

```
[PreToolUse] secrets_scanner: BLOCKED — postgresql://admin:pass@host in config.py
[PreToolUse] bash_safety:     BLOCKED — rm -rf with wildcard
[PreToolUse] pii_scanner:     WARNING — CPF pattern in user_data.py
[PreToolUse] quality_gate:    WARNING — debug print() in production code
```

Secrets nunca chegam ao git. PII nunca entra no codigo. Comandos destrutivos sao
bloqueados. O principio subjacente e **fail-open**: se um hook falhar internamente
(excecao Python, timeout), ele retorna exit 0 — nunca trava o Claude Code.

### Roteamento Cognitivo (hooks-routing)

Enforcement nao e apenas bloqueio. Os hooks de routing classificam cada prompt
por complexidade (CILA L0-L6) e intent (8 categorias), injetando tecnicas
cognitivas automaticamente:

```
[UserPromptSubmit] prompt_enhancer: intent=debug → chain_of_thought + few_shot + self_validation
[UserPromptSubmit] cila_router: complexity=L3 (multi-step) → routing=detailed_analysis
```

A implicacao e que Claude Code nao recebe apenas o prompt do usuario — recebe o
prompt enriquecido com a estrategia cognitiva apropriada para aquele tipo de
problema. Um debug L2 dispara chain-of-thought; uma refatoracao L4 dispara
structured output com constitutional constraints.

<details>
<summary><strong>Tabela completa: 16 hooks em 3 modulos</strong></summary>

| Hook | Evento | Modulo | O que faz |
|------|--------|--------|-----------|
| **Prompt Enhancer** | UserPromptSubmit | hooks-essential | Classifica intent (8 categorias) + injeta tecnicas cognitivas |
| **Status Monitor** | SessionStart | hooks-essential | Reports env info (Python, git branch, TODOs pendentes) |
| **Auto Compact** | PreCompact | hooks-essential | Salva checkpoint antes de compactacao de contexto |
| **Session State Manager** | SessionStart/Stop | hooks-essential | Persistencia de estado entre sessoes |
| **Post Compact Reinjector** | PreCompact | hooks-essential | Reinjecao de contexto critico pos-compactacao |
| **Quality Gate** | PreToolUse (Write/Edit) | hooks-quality | Limites de tamanho, debug code, docstrings |
| **Secrets Scanner** | PreToolUse (Write/Edit) | hooks-quality | Bloqueia API keys, tokens, credenciais |
| **PII Scanner** | PreToolUse (Write/Edit) | hooks-quality | CPF, CNPJ, SSN, email, telefone (BR/US/EU) |
| **Bash Safety** | PreToolUse (Bash) | hooks-quality | rm -rf, chmod 777, curl\|bash, fork bombs |
| **SIAC Orchestrator** | PreToolUse | hooks-quality | Quality gates com circuit breaker |
| **Validate Hooks Health** | Heartbeat | hooks-quality | Health check periodico de todos os hooks |
| **CILA Router** | UserPromptSubmit | hooks-routing | Classificacao L0-L6 com cache (120s TTL) |
| **Knowledge Manager** | PreToolUse | hooks-routing | 3-tier: cache local → docs → busca externa |
| **Compliance Tracker** | PostToolUse | hooks-routing | Audit logging JSONL + compliance scoring |
| **Auto Permission Resolver** | PreToolUse | hooks-routing | Resolucao automatica de permissoes CILA-aware |
| **PTC Advisor** | UserPromptSubmit | hooks-routing | Advisor de complexidade CILA L0-L6 |

</details>

<details>
<summary><strong>Skills (11), Agents (3) e Commands (6)</strong></summary>

**Skills:**
Code-First Planner, Plan Amplifier, Plan Execution, Verification Loop, Supreme Problem Solver,
Eval Harness, Skill Master, Skill Writer, Hook Master, Academic Research Writer, Literature Review.

**Agents:**
Code Reviewer (Sonnet — 4 dimensoes), Security Auditor (Sonnet — OWASP Top 10),
Meta Orchestrator (Opus — decide HOOK vs SKILL vs AGENT vs MCP).

**Commands:**
`/debug-RCA`, `/smart-commit`, `/orchestrate`, `/verify`, `/prp-base-create`, `/prp-base-execute`.

Detalhes em [MODULES_CATALOG.md](docs/MODULES_CATALOG.md).

</details>

Ate aqui, o sistema funciona — diretivas orientam, hooks interceptam. Mas ha
uma tensao: cada hook adiciona 50-200ms de latencia em Python puro. Com 16 hooks,
o desenvolvedor sente a friccao. E governanca que o desenvolvedor sente e
**governanca que o desenvolvedor desliga**. A terceira camada resolve isso.

---

## Layer 3 — Rust: A Camada de Aceleracao

### 7.137 linhas. 12 modulos. 151 testes nativos. Nao e stub.

O objetivo da camada Rust nao e apenas "ser mais rapido". E tornar a governanca
**invisivel** — enforcement que opera abaixo do limiar de percepcao do
desenvolvedor, sem jamais comprometer a seguranca.

A implementacao completa em `rust/kazuba-hooks/` oferece fallback graceful para
Python: se Rust nao esta compilado, Python assume. A API e identica; o chamador
nunca sabe qual backend respondeu.

### A Decisao Algoritmica: Two-Phase Detection

O padrao central e a deteccao em duas fases, que transforma O(n×m) em O(n):

```
Fase 1: Aho-Corasick pre-filter → scan unico O(n)
         Procura keywords rapidos: "api_key", "sk-", "ghp_", "-----BEGIN"
         Se NENHUM keyword → return [] (zero-cost exit)

Fase 2: RegexSet confirmation → so executa se Fase 1 detectou algo
         9 padroes precisos confirmam o match
```

A razao por que isso importa: a maioria dos arquivos nao contem segredos.
A Fase 1 elimina 95%+ dos arquivos em tempo linear, sem jamais invocar o motor
de regex. Em um projeto com 500 arquivos, ~475 sao descartados por Aho-Corasick
(nanosegundos) em vez de testados por 9 regexes cada. O mesmo padrao two-phase
se repete em `bash_safety.rs`, `skill_match.rs` e `knowledge.rs`.

| Modulo | Linhas | Funcao | Algoritmo |
|---|---|---|---|
| `rlm_reasoning.rs` | 930 | Chain/Tree/Graph-of-Thought | Validacao estrutural de raciocinio |
| `lib.rs` (bindings) | 892 | 25 funcoes PyO3 exportadas | Ponte Python-Rust completa |
| `learning.rs` | 843 | TD(lambda) + Working Memory | Rayon parallel similarity search |
| `qa.rs` | 843 | Issue categorization + ROI | Aho-Corasick batch matching |
| `knowledge.rs` | 686 | Knowledge engine + patterns | Multi-signal scoring |
| `recovery.rs` | 672 | Error-recovery strategies | 10 strategies com auto-apply |
| `bash_safety.rs` | 571 | Validacao de comandos shell | LazyLock + Aho-Corasick O(n) |
| `subagent.rs` | 562 | Skill injection SubagentStart | Category-weighted injection |
| `code_quality.rs` | 321 | Anti-pattern detection | RegexSet multi-pattern |
| `patterns.rs` | 291 | Utilities compartilhados | Aho-Corasick builders |
| `skill_match.rs` | 280 | Hybrid skill matching | 0.6 semantic + 0.4 Aho-Corasick |
| `secrets.rs` | 192 | Deteccao de credenciais | Two-phase: Aho-Corasick + Regex |

<details>
<summary><strong>Alem de velocidade: o que Rust torna possivel</strong></summary>

1. **Property Testing com Proptest** — `bash_safety.rs` e `recovery.rs` usam proptest para gerar
   inputs aleatorios e verificar que o validator nunca crashe. Fuzzing em tempo de compilacao.

2. **Rayon para Similarity Search** — `learning.rs` usa `par_iter()` para busca paralela em
   embeddings. Cada core do CPU processando fatias diferentes do vetor de memoria.

3. **Zero-allocation hot path** — Aho-Corasick em Rust opera sem alocacao de heap no caminho
   principal. Cada match e uma referencia a memoria pre-alocada.

4. **Fallback Graceful** — `lib/rust_bridge.py` implementa o contrato `@fail_open`:
   ```python
   try:
       result = _rust_check_secrets(content, file_path) if self._use_rust else _python_check_secrets(content)
   except Exception:
       result = _python_check_secrets(content)  # fallback silencioso
   ```
   O resultado carrega `backend: "rust" | "python"` para observabilidade.

5. **151 testes nativos + Criterion benchmarks** — secrets detection, code quality, bash safety,
   e no-match fast path.

</details>

Quando as tres camadas convergem, algo emerge que nenhuma delas produz sozinha.

---

## Convergencia: O Meta-Pattern

As tres camadas nao sao independentes — se amplificam mutuamente. A camada diretiva
define que cada hook deve ter implementacao Python **e** aceleracao Rust opcional.
O gerador code-first produz o skeleton de ambos. Os hooks de enforcement validam
que o fallback funciona. O benchmark mode comprova que Rust e mais rapido.

```
generate_plan.py define Phase(files_to_create=["rust/kazuba-hooks/src/new_module.rs"])
    → Claude Code implementa o modulo Rust
    → PyO3 bindings exportam para Python
    → rust_bridge.py detecta automaticamente
    → validate_phase_XX.py confirma fallback funcional
    → Criterion benchmark registra speedup
```

O resultado e um sistema que **se auto-hospeda**: o framework e construido com as
mesmas ferramentas que oferece. Os hooks que protegem o codigo do usuario protegem
o codigo do framework. O plano que gera as fases de desenvolvimento e validado
pelos mesmos scripts que ele gera. O principio meta-code-first nao e uma
diretriz — e uma propriedade emergente da convergencia das tres camadas.

Portanto, o que o desenvolvedor experimenta na pratica nao sao tres camadas
separadas — e uma unica experiencia: instalar, usar, e ter governanca invisivel.
As secoes seguintes mostram como isso se materializa.

---

## Presets

Cada preset e uma selecao curada de modulos, resolvida por topological sort
com base nas dependencias declaradas:

| Preset | Modulos | Ideal para |
|--------|---------|-----------|
| **minimal** | 1 | Templates e regras basicas |
| **standard** | 5 | Desenvolvimento diario + prompt enhancement |
| **research** | 6 | Projetos academicos com skills de pesquisa |
| **professional** | 10 | Engenharia completa com quality gates e agents |
| **enterprise** | 14 | Orquestracao multi-agente + hypervisor + compliance |

---

## Exemplos Praticos

Para ver as tres camadas em acao, `examples/` contem projetos-demo com cenarios
de antes/depois:

- [`python-api/`](examples/python-api/) — FastAPI: `secrets_scanner` bloqueia `postgresql://admin:Secret123@prod.db`
- [`rust-cli/`](examples/rust-cli/) — CLI Rust: `bash_safety` bloqueia `chmod 777` e `rm -rf` com wildcard
- [`typescript-web/`](examples/typescript-web/) — Next.js: `pii_scanner` detecta email/CPF em `console.log()` de API routes

---

## Arquitetura

```
claude-code-kazuba/
├── rust/kazuba-hooks/     # Layer 3: 7.137 linhas, 12 modulos, 25 PyO3 bindings
├── lib/                   # Shared: 8 modulos (hook_base, patterns, config, rlm, ...)
├── core/                  # Layer 1: Templates Jinja2 + rules universais
├── modules/               # Layer 2: 15 modulos opcionais
│   ├── hooks-essential/   #   Prompt enhancer, status monitor, auto compact
│   ├── hooks-quality/     #   Secrets, PII, bash safety, quality gate, SIAC
│   ├── hooks-routing/     #   CILA router, knowledge manager, compliance
│   ├── skills-*/          #   Dev, meta, planning, research (11 skills)
│   ├── agents-dev/        #   Code reviewer, security auditor, meta-orchestrator
│   ├── commands-*/        #   6 slash commands (debug-RCA, verify, smart-commit, ...)
│   └── ...                #   hypervisor, contexts, team-orchestrator, rlm
├── scripts/               # Meta-Code-First: generate_plan.py (3.676 linhas)
├── presets/                # 5 presets (minimal → enterprise)
├── examples/              # Projetos-demo (Python, Rust, TypeScript)
├── install.sh             # One-command installer
└── tests/                 # 1567 testes (phase_00 → phase_22 + integration_v2)
```

| Principio | Como se manifesta |
|-----------|------------------|
| **Fail-Open** | Hooks nunca crasham o Claude Code — erro interno = exit 0 |
| **Zero Config** | `./install.sh --preset standard` e tudo que voce precisa |
| **Composable** | Cada modulo e independente com dependencias explicitas |
| **TDD** | 90% coverage per file (nao media), todos os hooks testados |
| **Type-Safe** | Pydantic v2 para configs, pyright strict para lib/ |
| **Checkpoint** | TOON format (msgpack + header) para recovery de estado |

---

## Test Suite

A credibilidade de um framework de governanca se mede pela propria disciplina.
O Kazuba aplica a si mesmo o que exige dos projetos que protege:

```
============================= 1567 passed in 3.01s =============================
```

| Metrica | Valor |
|---------|-------|
| Testes Python | 1567 (723 v0.1.0 + 844 v0.2.0) |
| Testes Rust nativos | 151 |
| Coverage (lib/) | 97% |
| Coverage target | 90% per file |
| Lint (ruff) | 0 errors |
| Types (pyright strict) | 0 errors |
| CI | GitHub Actions (lint + typecheck + test) |

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

## v0.2.0

- [x] **Shared Infrastructure** — CircuitBreaker, TraceManager, HookLogger, EventBus
- [x] **Rust Acceleration Layer** — 7.137 linhas, 12 modulos, 25 PyO3 bindings, two-phase Aho-Corasick
- [x] **Core Governance + CILA Formal** — Taxonomia CILA L0-L6, StrategyEnforcer, governance rules
- [x] **Agent Triggers + Recovery** — Dispatch declarativo e escalacao automatica
- [x] **Hypervisor Executable** — Hypervisor, HypervisorV2, HypervisorBridge
- [x] **Advanced Hooks Batch 1** — SessionStateManager, PostCompactReinjector, ValidateHooksHealth
- [x] **Advanced Hooks Batch 2** — SiacOrchestrator, AutoPermissionResolver, PtcAdvisor
- [x] **RLM Learning Memory** — QTable, WorkingMemory, SessionManager, RewardCalculator, facade
- [x] **Meta-Code-First Planner** — 3.676 linhas gerando 24 fases com validacao automatica
- [x] **Integration + Migration** — E2E tests, migrate_v01_v02.py, MIGRATION.md
- [x] **Benchmark Suite** — benchmark_hooks.py CLI + self_host_config.py

### Roadmap

- [ ] **GPU Acceleration** — Embeddings e similarity via CUDA/Metal
- [ ] **Multi-tenant Isolation** — Isolamento de contexto por workspace
- [ ] **Web Dashboard** — Visualizacao de metricas de hooks em tempo real
- [ ] **Criterion Benchmarks Publicados** — Rust vs Python speedup numbers

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

# Rust (opcional — requer rustup + maturin)
cd rust/kazuba-hooks && cargo test && cargo bench
maturin develop --features pyo3-bindings
```

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

*Construido com o proprio principio meta-code-first: o plano e codigo,
a validacao e gerada, e a governanca nao custa latencia.*
