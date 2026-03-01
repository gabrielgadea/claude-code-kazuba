# Claude Code Kazuba

[![CI](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielgadea/claude-code-kazuba/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1567%20passed-brightgreen.svg)](#test-suite)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](#test-suite)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Claude Code sem governanca comete erros que voce so descobre no code review.**
Kazuba instala 15 modulos em 5 segundos — hooks que bloqueiam secrets, validam qualidade e
persistem contexto automaticamente. Sem configuracao manual. Sem latencia perceptivel.

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

| O que voce ganha | Como |
|-----------------|------|
| Nenhum secret vai para o git | Hooks bloqueiam antes de escrever |
| Qualidade checada em cada arquivo | Quality gate pre-escrita |
| Contexto persistente entre sessoes | Checkpoints automaticos |
| Prompts enriquecidos automaticamente | Classificacao + tecnicas cognitivas |
| Stack-aware (Python, Rust, TS, Go...) | Deteccao automatica + templates Jinja2 |

---

## O Trade-Off que Motivou a Arquitetura

Claude Code executa hooks em cada interacao. Cada prompt classificado. Cada comando bash validado.
Cada arquivo escaneado por segredos. Em Python puro, cada hook adiciona 50-200ms de latencia — e
quando voce empilha 16 hooks, o desenvolvedor **sente** a friccao. A governanca vira peso morto.

Mas remover hooks significa aceitar codigo inseguro em producao. O trade-off parecia inevitavel:
**seguranca ou velocidade. Escolha um.**

Kazuba escolheu os dois. E a forma como fez isso revela duas decisoes arquiteturais que
separam este framework de qualquer configuracao manual de hooks.

---

## Pilar 1 — Rust Acceleration Layer

### 7.137 linhas. 12 modulos. 151 testes nativos. Nao e stub.

A camada Rust em `rust/kazuba-hooks/` e uma implementacao completa com fallback graceful
para Python. Se Rust nao esta compilado, Python assume — a API e identica, o chamador nunca
sabe qual backend respondeu.

**A decisao algoritmica que importa — Two-Phase Detection:**

```
Fase 1: Aho-Corasick pre-filter → scan unico O(n)
         Procura keywords rapidos: "api_key", "sk-", "ghp_", "-----BEGIN"
         Se NENHUM keyword → return [] (zero-cost exit)

Fase 2: RegexSet confirmation → so executa se Fase 1 detectou algo
         9 padroes precisos confirmam o match
```

A maioria dos arquivos nao contem segredos. A Fase 1 elimina 95%+ dos arquivos em tempo linear,
sem jamais invocar o motor de regex. Em um projeto com 500 arquivos, ~475 sao descartados por
Aho-Corasick (nanosegundos) em vez de testados por 9 regexes cada.

O mesmo padrao two-phase se repete em `bash_safety.rs`, `skill_match.rs` e `knowledge.rs`.

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
<summary><strong>O que o Rust traz alem de velocidade</strong></summary>

1. **Property Testing com Proptest** — `bash_safety.rs` e `recovery.rs` usam proptest para gerar
   inputs aleatorios e verificar que o validator nunca crashe. Fuzzing em tempo de compilacao.

2. **Rayon para Similarity Search** — `learning.rs` usa `par_iter()` para busca paralela em
   embeddings. Cada core do CPU processando fatias diferentes do vetor de memoria.

3. **Zero-allocation hot path** — Aho-Corasick em Rust opera sem alocacao de heap no caminho
   principal. Cada match e uma referencia a memoria pre-alocada.

4. **Fallback Graceful** — `lib/rust_bridge.py` implementa o contrato `@fail_open`:
   ```python
   # Tenta Rust. Se falhar, usa Python. API identica.
   try:
       result = _rust_check_secrets(content, file_path) if self._use_rust else _python_check_secrets(content)
   except Exception:
       result = _python_check_secrets(content)  # fallback silencioso
   ```
   O resultado carrega `backend: "rust" | "python"` para observabilidade.
   Benchmark mode coleta timing em nanosegundos para comparacao real.

5. **151 testes nativos + Criterion benchmarks** — secrets detection, code quality, bash safety,
   e no-match fast path. Cada modulo com cobertura propria.

</details>

---

## Pilar 2 — Meta-Code-First

### O plano de desenvolvimento E codigo. Nao e documento.

O `CLAUDE.md` do Kazuba define: *"Plans are data, not documents."* E aplica o principio a si
mesmo — um script Python de 3.676 linhas gera programaticamente todas as 24 fases do plano,
com frontmatter YAML, cross-references validadas, e scripts de validacao por fase.

```bash
python scripts/generate_plan.py --output-dir plans/ --validate
# → 24 arquivos markdown + 24 scripts de validacao + orquestrador
```

**5 camadas de geracao/validacao:**

```
generate_plan.py (Python)
    → gera validate_phase_XX.py (Python que valida codigo)
        → que roda pytest (que valida implementacao)
            → que testa hooks (que validam codigo do usuario)
                → que usam Rust (que valida padroes em O(n))
```

A diferenca entre um plano markdown e um plano code-first:

| Plano Manual | Plano Code-First (Kazuba) |
|---|---|
| Cada autor formata diferente | Frontmatter YAML por template — zero divergencia |
| Revisao humana, subjetiva | `--validate` verifica existencia, cross-refs, schemas |
| Editar 24 arquivos, cacar refs | Editar dados Python, regenerar idempotentemente |
| `git diff` em markdown e ruido | `git diff` em Python mostra mudanca semantica |

<details>
<summary><strong>Claude Code como orchestrator de codigo</strong></summary>

No contexto do Kazuba, Claude Code nao e apenas um editor que recebe instrucoes. Ele opera
como um **orquestrador** de um plano compilavel:

1. **Le** `generate_plan.py` para entender a fase atual
2. **Executa** o gerador para criar/atualizar o plano
3. **Implementa** os arquivos definidos em `files_to_create`
4. **Roda** `validate_phase_XX.py` para verificar completude
5. **Itera** se validacao falhar

Cada fase define `AgentSpec` para subagentes paralelos:

```python
agents=[
    AgentSpec(name="rust-impl", subagent_type="implementor", model="sonnet", isolation="worktree"),
    AgentSpec(name="test-writer", subagent_type="tester", model="sonnet", isolation="worktree"),
]
```

Worktree isolation + parallel execution = cada agente trabalha em branch propria, merge
coordenado pelo orquestrador. O plano e executavel, a implementacao e validavel, e a
validacao e gerada automaticamente.

</details>

---

## Presets

| Preset | Modulos | Ideal para |
|--------|---------|-----------|
| **minimal** | 1 | Templates e regras basicas |
| **standard** | 5 | Desenvolvimento diario + prompt enhancement |
| **research** | 6 | Projetos academicos com skills de pesquisa |
| **professional** | 10 | Engenharia completa com quality gates e agents |
| **enterprise** | 14 | Orquestracao multi-agente + hypervisor + compliance |

Cada modulo declara dependencias; o installer resolve via topological sort.

---

## Exemplos Praticos

Projetos-demo com antes/depois em `examples/`:

- [`python-api/`](examples/python-api/) — FastAPI: `secrets_scanner` bloqueia `postgresql://admin:Secret123@prod.db`
- [`rust-cli/`](examples/rust-cli/) — CLI Rust: `bash_safety` bloqueia `chmod 777` e `rm -rf` com wildcard
- [`typescript-web/`](examples/typescript-web/) — Next.js: `pii_scanner` detecta email/CPF em `console.log()` de API routes

---

## Seguranca, Prompts e Roteamento

### Seguranca Como Default

4 hooks rodam **antes** de cada escrita de arquivo e **antes** de cada comando bash:

```
[PreToolUse] secrets_scanner: BLOCKED — postgresql://admin:pass@host in config.py
[PreToolUse] bash_safety:     BLOCKED — rm -rf with wildcard
[PreToolUse] pii_scanner:     WARNING — CPF pattern in user_data.py
[PreToolUse] quality_gate:    WARNING — debug print() in production code
```

Secrets nunca chegam ao git. PII nunca entra no codigo. Comandos destrutivos sao bloqueados.

### Prompt Enhancement + CILA Routing

Cada prompt e automaticamente classificado em 8 categorias, enriquecido com tecnicas cognitivas
(chain-of-thought, structured output, constitutional constraints), e roteado por complexidade
CILA (L0-L6) para calibrar profundidade de resposta.

---

## Arquitetura

```
claude-code-kazuba/
├── rust/kazuba-hooks/     # Aceleracao Rust: 7.137 linhas, 12 modulos, 25 PyO3 bindings
├── lib/                   # 8 modulos compartilhados (hook_base, patterns, config, rlm, ...)
├── core/                  # Templates Jinja2 + rules universais (sempre instalado)
├── modules/               # 15 modulos opcionais organizados por categoria
│   ├── hooks-essential/   #   Prompt enhancer, status monitor, auto compact
│   ├── hooks-quality/     #   Secrets, PII, bash safety, quality gate, SIAC
│   ├── hooks-routing/     #   CILA router, knowledge manager, compliance
│   ├── skills-*/          #   Dev, meta, planning, research (11 skills)
│   ├── agents-dev/        #   Code reviewer, security auditor, meta-orchestrator
│   ├── commands-*/        #   6 slash commands (debug-RCA, verify, smart-commit, ...)
│   └── ...                #   hypervisor, contexts, team-orchestrator, rlm
├── scripts/               # generate_plan.py (3.676 linhas) + installer CLI
├── presets/               # 5 presets (minimal → enterprise)
├── examples/              # Projetos-demo (Python, Rust, TypeScript)
├── install.sh             # One-command installer
└── tests/                 # 1567 testes (phase_00 → phase_22 + integration_v2)
```

| Principio | Implementacao |
|-----------|--------------|
| **Fail-Open** | Hooks nunca crasham o Claude Code — erro interno = exit 0 |
| **Zero Config** | `./install.sh --preset standard` e tudo que voce precisa |
| **Composable** | Cada modulo e independente com dependencias explicitas |
| **TDD** | 90% coverage per file (nao media), todos os hooks testados |
| **Type-Safe** | Pydantic v2 para configs, pyright strict para lib/ |
| **Checkpoint** | TOON format (msgpack + header) para recovery de estado |

<details>
<summary><strong>Hooks completos (16 hooks em 3 modulos)</strong></summary>

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

Detalhes completos em [MODULES_CATALOG.md](docs/MODULES_CATALOG.md).

</details>

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
| Types (pyright strict) | 0 errors |
| Testes nativos Rust | 151 |
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
- [x] **Rust Acceleration Layer** — 7.137 linhas, 12 modulos, 25 PyO3 bindings, two-phase Aho-Corasick detection
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

*Construido com o proprio principio meta-code-first: o plano e codigo, a validacao e gerada,
e a governanca nao custa latencia.*
