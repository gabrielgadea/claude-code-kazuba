---
paths: "**"
priority: 98
---

# PLAN-AS-CODE: Specs São Sujeitas à Auditoria de Código

> Priority: 98 — Acima de ACO-CORE (P95), abaixo de CODE-FIRST (P100)
> Scope: TODA escrita de plano, spec, contrato ou `_EXECUTE_SOURCE`

## O Anti-Padrão

Escrever especificações, planos ou contratos via inferência LLM — sem verificar o código
referenciado — produz bugs detectáveis APENAS na execução. Isso viola CODE-FIRST e desperdiça
ciclos de swarm.

**Prova empírica (2026-03-05)**: 7 bugs em um único plano, todos causados por inferência:
- `dspy.Assert`/`dspy.Suggest` → removidos em DSPy 3.x (`hasattr(dspy, 'Assert')` = False)
- `result.message` → campo não existe em `QualityGateResult` (campos reais: `alerts`, `verdict`)
- `check_quality_gate(output=...)` → parâmetro não existe na assinatura real
- `ConfidenceLevelLiteral["HIGH"]` → case errado (real: `"high"`, `"medium"`, `"low"`)
- `_store_path` / `_load_knowledge()` → não existem em `ProcessAccumulator`
- `_EXECUTE_SOURCE` em gen_code_kb_indexer → não usa esse padrão (é N₀, não N₁)

**Cada bug foi detectado apenas lendo o arquivo real. Nenhum exigiu execução.**

---

## AUDITORIA OBRIGATÓRIA ANTES DE ESCREVER QUALQUER SPEC

Antes de escrever qualquer seção de plano, `_EXECUTE_SOURCE`, ou contrato que referencie:

| Elemento | Ferramenta obrigatória |
|----------|----------------------|
| Assinatura de função/método | `python scripts/discover.py "nome_func"` + Read do arquivo |
| Campo/atributo de classe | `mcp__gitnexus__query` OU `Grep "field_name"` no arquivo real |
| API de biblioteca externa | `mcp__context7__query-docs` + verificação de versão instalada |
| Estrutura de dados (dict, list, shape) | `Read` direto do source (nunca inferir pelo nome do tipo) |
| Path de arquivo | `Glob` ou `ls` — nunca assumir existência |
| Valores de Enum/Literal | `Read` do arquivo de definição — case e spelling importam |

---

## Protocolo de Auditoria (comandos exatos)

```bash
# 1. Símbolo/função existe com assinatura correta?
python scripts/discover.py "function_name"
# → Se encontrado: Read do arquivo para verificar params e tipos

# 2. Campo/atributo existe na classe?
# GitNexus (semântico):
mcp__gitnexus__query: MATCH (s:Symbol {name: 'ClassName'})-[:HAS_MEMBER]->(m) RETURN m.name, m.type
# Ou Grep direto:
Grep pattern: "field_name\s*[:=]" path: "arquivo_da_classe.py"

# 3. API de biblioteca externa está atualizada?
mcp__context7__resolve-library-id: "dspy"
mcp__context7__query-docs: query="removed deprecated API version"
# Verificar versão instalada:
python -c "import importlib.metadata; print(importlib.metadata.version('dspy'))"

# 4. Shape real de uma estrutura de dados?
# Serena (simbólico):
mcp__plugin_serena_serena__find_symbol: name_path="ClassName/__init__" include_body=True
# Ou Read direto do arquivo fonte

# 5. Valores reais de um Enum/Literal?
Grep pattern: "HIGH\s*=\s*|MEDIUM\s*=\s*|LOW\s*=\s*" glob: "*.py"
Read: arquivo de definição do Enum
```

---

## VIOLATIONS

- **VIOLATION** = escrever `func(param=X)` em spec sem executar `discover.py "func"`
- **VIOLATION** = especificar `obj.field` sem Grep/Read verificando que o campo existe
- **VIOLATION** = referenciar API de terceiro sem Context7 check da versão instalada
- **VIOLATION** = escrever `_EXECUTE_SOURCE` com estruturas de dados inferidas por nome
- **VIOLATION** = declarar spec completa sem ao menos 1 verificação por referência externa não-trivial
- **VIOLATION** = copiar padrão de um arquivo "canônico" sem ler esse arquivo primeiro

## O Teste Binário

Antes de finalizar qualquer bloco de spec, perguntar:
**"Li o source real de cada símbolo não-trivial que referenciei?"**

Se a resposta for NÃO → DISCOVER → READ → ENTÃO escrever.

---

## Ferramentas por Ordem de Preferência

1. **Tantivy DISCOVER** (`python scripts/discover.py`) — para qualquer símbolo do projeto
2. **GitNexus query** (`mcp__gitnexus__query`) — para relações entre símbolos
3. **Serena find_symbol** (`mcp__plugin_serena_serena__find_symbol`) — para corpo de métodos
4. **Grep** — busca textual quando nome exato é conhecido
5. **Context7** — para APIs de bibliotecas externas (dspy, pydantic, etc.)
6. **Read direto** — quando path é conhecido e precisa ver a estrutura completa
