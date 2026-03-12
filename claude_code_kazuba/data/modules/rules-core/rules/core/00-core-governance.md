---
priority: 100
---

# Core Governance Rules

## CODE-FIRST UNIVERSAL (MANDATORY — PRIORITY 100)

O principio CODE-FIRST se aplica a TODA interacao, nao apenas ao pipeline PROJECT.
Agente principal e TODOS os sub-agents (Task tool) DEVEM seguir este ciclo.

### Definicao

- **LLM = preditor estocastico**. Codigo = executor deterministico.
- O output de um script e SEMPRE mais confiavel que qualquer inferencia do LLM.
- Toda tarefa deve produzir, executar e avaliar codigo — nao apenas narrativa.

### Ciclo CODE-FIRST (6 Passos)

Para QUALQUER tarefa recebida, seguir este ciclo:

#### PASSO 1 — DISCOVER (Buscar na codebase inteira)

Antes de fazer qualquer coisa, buscar se ja existe codigo para a tarefa **em toda a codebase**:

```
# 1. OBRIGATORIO — Tantivy-powered DISCOVER CLI (3-tier fallback, nunca falha)
python scripts/discover.py "keyword_da_tarefa"
python scripts/discover.py "keyword" --module scripts --limit 10
python scripts/discover.py "keyword" --json  # output estruturado

# 2. OBRIGATORIO — GitNexus (grafo de 144k simbolos e 232k relacionamentos)
mcp__gitnexus__context   # visao geral do repo + freshness do indice
mcp__gitnexus__query     # Cypher: relacoes entre modulos, quem usa o que
mcp__gitnexus__impact    # blast radius antes de qualquer mudanca

# 3. OBRIGATORIO — Serena (leitura simbolica precisa, zero-hallucination)
mcp__plugin_serena_serena__find_symbol              # localizar simbolo com corpo real
mcp__plugin_serena_serena__get_symbols_overview     # overview sem ler arquivo inteiro
mcp__plugin_serena_serena__find_referencing_symbols # quem usa este simbolo?

# 4. Fallback manual — apenas quando os tres sistemas acima nao encontram resultado
Grep: "keyword_da_tarefa" em toda a codebase (sem filtro de path)
Glob: packages/**/*.py · scripts/**/*.py · backend/app/**/*.py
Glob: .claude/hooks/**/*.py · packages/**/*.rs · frontend/src/**/*.{ts,tsx}
```

**Mapa da Codebase** — onde cada tipo de codigo vive:

| Area | Path | Conteudo |
|------|------|----------|
| **Kazuba Agents** | `packages/kazuba-agents/` | 13 agentes especializados (Centauri→Praetor), Pln3 APEX engine |
| **Kazuba Core** | `packages/kazuba-core/` | Modelos de dominio, validators, contratos |
| **Kazuba RAG** | `packages/kazuba-rag/` | Hybrid RAG (Qdrant+BM25+Reranker), retriever, indexer |
| **Kazuba Converters** | `packages/kazuba-converters/` | OCR cascade (Docling+Tesseract), markdown conversion |
| **Kazuba Enrichment** | `packages/kazuba-enrichment/` | NER, entity linking, classificacao documental |
| **Kazuba Shared** | `packages/kazuba-shared/` | Logging, config, metrics compartilhados |
| **Kazuba SEI Core** | `packages/kazuba-sei-core/` | Parsing de processos SEI |
| **Rust Core** | `packages/kazuba-rust-core/` | LegalPatternMatcher, BM25Index, RRF, Deep-RAG (2080 files) |
| **Rust Converters** | `packages/kazuba-converters-rs/` | NLP pipeline Rust, quality reports (140 files) |
| **Rust Bridge** | `packages/kazuba-rust-bridge/` | PyO3 bindings |
| **Scripts** | `scripts/` | Utilitarios, pipeline_runner, fases F1-F16, RAG, quality |
| **Backend** | `backend/app/` | FastAPI, routers, services, workflows |
| **Frontend** | `frontend/src/` | React 19, componentes, hooks, stores |
| **Hooks** | `.claude/hooks/` | Quality gates, validation, knowledge, lifecycle |

Se encontrou codigo relevante → ir para PASSO 3 (Execute).
Se NAO encontrou → ir para PASSO 2 (Create).

**Objetivo incremental**: Com o tempo, cada DISCOVER bem-sucedido constroi um mapa mental de "onde vive o que" na codebase. Esse conhecimento se acumula nos scripts persistidos (Passo 6) e nas memorias do projeto, criando um indice de relacionamentos que acelera buscas futuras.

#### PASSO 2 — CREATE (Gerar o melhor codigo possivel)

Se nao existe script, CRIAR antes de analisar manualmente. Tres consultas OBRIGATORIAS antes de escrever qualquer linha:

1. **Tantivy — padrao de codigo existente** (sempre primeiro):
   - `python scripts/discover.py "funcionalidade_similar"` — encontrar modulos analogos
   - Identificar **padroes de import, logging, error handling** usados em modulos vizinhos
   - Referencia por area: PROJECT → `packages/kazuba-agents/` e `packages/kazuba-core/`
   - Pipelines → `packages/kazuba-rag/` e `packages/kazuba-enrichment/`
   - Conversao → `packages/kazuba-converters/` e `packages/kazuba-converters-rs/`
   - Performance-critical → `packages/kazuba-rust-core/` (Rust + PyO3)
   - Hooks → `.claude/hooks/` (padrao PreToolUse/PostToolUse)
   - Endpoints → `backend/app/`

2. **GitNexus — relacoes e dependencias** (antes de decidir onde e como criar):
   - `mcp__gitnexus__query` → quais modulos existentes o novo codigo vai usar/estender?
   - `mcp__gitnexus__impact` → se vou editar X, o que mais sera afetado?
   - Exemplo: `MATCH (s:Symbol)-[:IMPORTS]->(t:Symbol {name:'modulo'}) RETURN s.file, s.name`
   - Garante que o novo codigo nao duplica logica ja existente em outros modulos

3. **Serena — verificacao de assinaturas** (antes de referenciar qualquer simbolo):
   - `mcp__plugin_serena_serena__find_symbol` com `include_body=True` → assinatura real da funcao
   - `mcp__plugin_serena_serena__get_symbols_overview` → campos reais de uma classe
   - NUNCA inferir parametros, campos ou Enum values pelo nome — sempre ler o corpo
   - Obrigatorio para todo simbolo nao-trivial que o novo codigo vai importar ou estender

4. **Context7 — APIs de bibliotecas externas** (quando o codigo usa dependencias de terceiros):
   - `mcp__context7__resolve-library-id` → identificar a biblioteca
   - `mcp__context7__query-docs` → documentacao, exemplos, padroes recomendados da versao instalada
   - Garante APIs corretas e padroes modernos (nao knowledge desatualizado do modelo)

5. **Gerar o script no local adequado**:
   - `scripts/process_analysis/phases/` → fases do pipeline PROJECT (F1-F16)
   - `scripts/` → utilitarios gerais, automacoes, ferramentas one-off
   - `packages/<kazuba-package>/` → se e logica reutilizavel de dominio
   - `.claude/hooks/` → se e automacao de Claude Code (validation, lifecycle)
   - `backend/app/` → se e endpoint ou service

6. **Validar sintaxe**: `ruff check` + `ruff format` antes de qualquer execucao.

O script DEVE:
- Seguir os padroes da codebase (ver `.claude/rules/code-style.md`)
- Reutilizar modulos existentes (`from packages.kazuba_core...`, `from scripts...`) quando possivel
- Ter `if __name__ == "__main__":` para execucao standalone
- Produzir output estruturado (JSON quando possivel) para consumo posterior
- Incluir logging adequado (`import logging`)

#### PASSO 3 — EXECUTE (Executar o codigo)

Rodar o script e capturar o output completo:

```bash
# Executar e capturar
python scripts/<script>.py [args] 2>&1
```

O resultado da execucao e a BASE FACTUAL. A analise do LLM e complementar.

#### PASSO 4 — EVALUATE (Avaliar em duas dimensoes)

Avaliar AMBAS as dimensoes — nao apenas uma:

**4A. Qualidade do codigo gerado** (se criado no Passo 2):
- `ruff check`: 0 erros?
- `pytest`: testes passam? (se existem)
- Complexidade <=10 por funcao?
- Padroes da codebase seguidos?
- Se insuficiente → REFINAR (voltar ao Passo 2 com melhorias)

**4B. Qualidade do output/conteudo**:
- Output e completo para a tarefa solicitada?
- Dados sao verificaveis? (cross-check com fontes quando aplicavel)
- Formato e consumivel? (JSON, markdown, etc.)
- Se insuficiente → REFINAR (ajustar parametros, melhorar logica, re-executar)

#### PASSO 5 — REFINE (Iterar se necessario)

Se qualquer dimensao do Passo 4 for insuficiente:
- Ajustar o codigo com base nos resultados
- Re-executar (Passo 3)
- Re-avaliar (Passo 4)
- Maximo 3 iteracoes antes de reportar ao usuario

#### PASSO 6 — PERSIST (Persistir e indexar para reuso)

Apos sucesso, garantir que o script e seu contexto fiquem disponiveis para reuso futuro:

**6A. Persistir o script**:
- Salvar no local adequado conforme o Mapa da Codebase (Passo 1)
- Se e logica de dominio reutilizavel → integrar em `packages/` como modulo
- Se e utilitario → salvar em `scripts/` com nome descritivo
- Se e fase de pipeline → salvar em `scripts/process_analysis/phases/`

**6B. Indexar o relacionamento** (mapa incremental da codebase):
- Registrar QUAIS modulos existentes o novo script usa (imports, dependencias)
- Registrar QUAL problema ele resolve (descricao funcional)
- Registrar ONDE ele se encaixa no mapa (qual area da codebase)
- Esse registro fica no proprio script (docstring) E no contexto da tarefa

**6C. Knowledge base crescente**:
- Cada tarefa resolvida via code-first ADICIONA um script reutilizavel a codebase
- Na proxima tarefa similar, o Passo 1 (DISCOVER) encontra esse script
- Com o tempo, a codebase se auto-indexa: cada novo script documenta seus relacionamentos com modulos existentes, criando um mapa de dependencias e funcionalidades que acelera DISCOVER futuro
- O objetivo final e que a codebase inteira se torne navegavel por funcionalidade — nao apenas por path

### Resumo do Ciclo

```
DISCOVER (Tantivy + GitNexus + Serena) → existe script?
  ├─ SIM → EXECUTE → EVALUATE → (REFINE?) → PERSIST
  └─ NAO → CREATE (Tantivy + GitNexus + Serena + Context7) → EXECUTE → EVALUATE → (REFINE?) → PERSIST
```

### Regras Complementares

1. **VERIFIQUE antes de AFIRMAR**: `ls` antes de "o arquivo existe". `pytest` antes de "o teste passa". `wc -l` antes de "tem ~300 linhas".
2. **CALCULE antes de ESTIMAR**: Nunca "~85% coverage" — rode `pytest --cov`.
3. **SUB-AGENTS INCLUSOS**: Todo sub-agent spawned via Task tool DEVE seguir o mesmo ciclo de 6 passos.
4. **Trios OBRIGATORIOS** — DISCOVER e CREATE exigem os tres sistemas em sequencia:
   - **Tantivy** (`python scripts/discover.py`) — busca semantica local, 0 tokens, sempre primeiro
   - **GitNexus** (`mcp__gitnexus__*`) — relacoes entre simbolos, blast radius, dependencias
   - **Serena** (`mcp__plugin_serena_serena__*`) — corpo real de simbolos, zero-hallucination
   - **Context7** (`mcp__context7__*`) — APIs externas, bibliotecas de terceiros (CREATE only)

### Violacoes

- **VIOLACAO** = produzir analise narrativa quando um script poderia computar o resultado
- **VIOLACAO** = NAO buscar scripts existentes antes de analisar manualmente (pular Passo 1)
- **VIOLACAO** = pular GitNexus no DISCOVER quando Tantivy nao encontrou resultado suficiente
- **VIOLACAO** = referenciar assinatura de funcao em spec ou codigo sem Serena `find_symbol`
- **VIOLACAO** = inferir campo/atributo/Enum pelo nome sem ler o corpo real via Serena
- **VIOLACAO** = criar codigo que usa modulo existente sem checar relacoes via GitNexus
- **VIOLACAO** = NAO consultar Context7 ao criar codigo que usa biblioteca externa
- **VIOLACAO** = afirmar sem verificar (ex: "o arquivo tem 300 linhas" sem `wc -l`)
- **VIOLACAO** = entregar codigo sem validar (`ruff check`, testes)
- **VIOLACAO** = skill PROJECT sem pipeline_state verificado
- **VIOLACAO** = sub-agent produzindo narrativa quando existe script computacional
- **VIOLACAO** = resolver mesmo problema duas vezes sem persistir script (pular Passo 6)

---

## LOCAL-CACHE-FIRST (MANDATORY)

1. Check `.local-cache/knowledge.json` FIRST (0 tokens)
2. Use Cipher MCP ONLY if local confidence < 0.30
3. VIOLATION = calling `cipher_memory_search` without local check

## HOOKS ARE INVIOLABLE

- NEVER ignore, disable, or bypass hooks
- ALWAYS respect results: allow/warn/block
- FIX 100% of identified problems
- Files: `code_standards_enforcer.py`, `post_quality_gate.py`

## ZERO-HALLUCINATION PROTOCOL

- NEVER invent TCU Acordao numbers
- NEVER fabricate PROJECT Resolution numbers
- NEVER misquote legislation articles
- ALWAYS verify citations in source documents
- Tag confidence: HIGH (>90%), MEDIUM (70-90%), LOW (<70%)

## CHECKPOINT STORAGE (MANDATORY)

- **ÚNICO LOCAL**: `.claude/checkpoints/`
- **FORMATO**: `{descricao}_{YYYYMMDD}.json`
- **ESTRUTURA**: JSON com campos padronizados (ver `checkpoints/README.md`)

**NÃO usar outros locais para checkpoints:**
- ❌ `.serena/memories/` - Apenas contexto Serena MCP
- ❌ Cipher MCP memories - Não persistem localmente
- ❌ `.claude/plans/` - Apenas documentação (.md)

## SUCCESS CRITERIA

- Hooks: ALLOW (not WARN, not BLOCK)
- Quality gate: PASS (all 6 stages)
- Ruff/Pyright: 0 errors, 0 warnings
- Complexity: <=10 per function
