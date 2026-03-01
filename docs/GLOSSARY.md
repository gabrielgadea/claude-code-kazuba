# Glossario — claude-code-kazuba

Referencia de termos usados neste projeto, organizados por contexto.

---

## Framework Open-Source

### Kazuba / claude-code-kazuba
O projeto open-source em si. Framework modular de hooks, skills, agents e commands para
Claude Code. Nao tem relacao com nenhum produto comercial ou entidade regulatoria.

- **Repositorio**: https://github.com/gabrielgadea/claude-code-kazuba
- **Licenca**: MIT
- **Uso**: Qualquer pessoa pode usar, modificar e distribuir

### CILA (Complexity Intelligence Layer Architecture)
Taxonomia de complexidade de tarefas, de L0 a L6:

| Nivel | Nome | Exemplos |
|-------|------|----------|
| L0 | Trivial | Formatar string, renomear variavel |
| L1 | Simple | Funcao isolada, teste unitario |
| L2 | Moderate | Classe com logica, integracao simples |
| L3 | Complex | Feature multi-arquivo, refactoring |
| L4 | Advanced | Mudanca arquitetural, sistema distribuido |
| L5 | Expert | Design de linguagem, otimizacao de compilador |
| L6 | Research | Problema aberto, sem solucao conhecida |

Usado pelo `cila_router` hook para calibrar a profundidade de resposta do Claude Code.

### TOON Format
Formato de checkpoint binario: `[4 bytes magic] [4 bytes version] [msgpack payload]`.
Usado para persistir estado entre sessoes e recovery apos compactacao de contexto.

- Extension: `.toon`
- Biblioteca: `msgpack`
- Magic bytes: `TOON` (0x544F4F4E)

### RLM (Reinforcement Learning Memory)
Modulo de aprendizado por reforco para Claude Code. Composto por:
- **QTable**: Q-values persistentes por estado/acao (JSON)
- **WorkingMemory**: LRU-bounded episodic memory com busca por tag
- **SessionManager**: lifecycle de sessoes + checkpoints TOON
- **RewardCalculator**: reward composto por metricas de performance
- **RLMFacade**: API unificada para integracao com hooks

### Preset
Bundle predefinido de modulos. Nomes: `minimal`, `standard`, `research`, `professional`, `enterprise`.
Definidos em `presets/nome.txt` — um modulo por linha.

### Module / Modulo
Unidade instalavel em `modules/`. Cada modulo tem:
- `MODULE.md`: manifest YAML com nome, descricao, dependencias
- Diretorios opcionais: `hooks/`, `skills/`, `agents/`, `commands/`, `config/`, `contexts/`
- `settings.hooks.json`: fragment de hook registration (merge no settings.json do projeto)

### Hook (Claude Code)
Script executado em resposta a eventos do Claude Code (ex: `PreToolUse`, `UserPromptSubmit`).
Comunica com o Claude via JSON no stdout. Exit 2 = bloqueia a acao.

### Fail-Open
Principio de design: se um hook falhar internamente (excecao Python), ele retorna exit 0
(nao bloqueante). Nunca deve travar o Claude Code por erro interno.

---

## Terminologia do Time (Interna)

> Estes termos sao usados internamente no time de desenvolvimento e nao tem relacao
> com o framework open-source em si.

### Kazuba King / Openclaw
Bot Telegram do time (`@gabrielgadea_bot`). Resposta rapida, multi-channel.
Nao confundir com o framework claude-code-kazuba.

### KAZUBA (regulatorio)
Sigla usada internamente para identificar o projeto no contexto de processos administrativos
e regulatorios do time. Sem relacao com o framework open-source.

### claude_code / @kazuba_claude_bot
O orchestrator do time — instancia do Claude Code que planeja, coordena e delega tarefas
para outros agentes. Diferente do usuario Gabriel Gadea.

### Inter-Agent Relay
Sistema interno de comunicacao entre agentes via Telegram (relay.py).
Nao e parte do framework open-source claude-code-kazuba.

---

## Siglas Tecnicas

| Sigla | Expansao | Contexto |
|-------|----------|----------|
| CILA | Complexity Intelligence Layer Architecture | Hook de roteamento |
| RLM | Reinforcement Learning Memory | Modulo de aprendizado |
| TOON | Formato de checkpoint (magic bytes) | Persistencia de estado |
| PRP | Product Requirements Prompt | Template de especificacao |
| RCA | Root Cause Analysis | Comando `/debug-RCA` |
| SIAC | System Intelligence and Automation Controller | Hook v0.2.0 |
| PTC | Prompt-Task-Complexity | Hook advisor v0.2.0 |
| TDD | Test-Driven Development | Principio de qualidade |
| OWASP | Open Web Application Security Project | Referencia de seguranca |

---

*Ultima atualizacao: v0.2.0*
