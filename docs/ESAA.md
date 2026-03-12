# ESAA — Event Sourcing for Autonomous Agents

## Visão Geral

**ESAA** é uma arquitetura de event sourcing projetada para agentes autônomos. Transforma cada operação do Claude Code em eventos imutáveis, permitindo reconstrução completa do estado do projeto a qualquer momento através de projeções determinísticas.

```
┌─────────────────────────────────────────────────────────────────┐
│                     ESAA Architecture                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │  Tool Call   │───▶│ ESAA Bridge  │───▶│    Event     │      │
│   │  (PreToolUse)│    │   (Hook)     │    │  Envelope    │      │
│   └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                  │               │
│                              ┌───────────────────▼───────────┐  │
│                              │      Activity Log             │  │
│                              │      (JSON Lines)             │  │
│                              └───────────────────┬───────────┘  │
│                                                  │               │
│   ┌──────────────┐    ┌──────────────┐    ┌─────▼──────┐        │
│   │   Replay     │◀───│  Projector   │◀───│  RawEvents │        │
│   │   Engine     │    │  (Rust/Py)   │    │            │        │
│   └──────────────┘    └──────────────┘    └────────────┘        │
│                                                  │               │
│                              ┌───────────────────▼───────────┐  │
│                              │    Projected State            │  │
│                              │  (TOON checkpoint equivalent) │  │
│                              └───────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Conceitos Fundamentais

### Event Sourcing

Em vez de salvar o estado atual, salvamos **todos os eventos** que levaram a esse estado. O estado atual é uma projeção dos eventos.

```python
# Estado tradicional (TOON)
checkpoint = {
    "phase_id": 5,
    "title": "Implement ESAA",
    "files": ["esaa_types.py", "projector.py"]
}

# ESAA: stream de eventos
events = [
    {"event_id": "EV-00000001", "command": {"operation_type": "FILE_WRITE", ...}},
    {"event_id": "EV-00000002", "command": {"operation_type": "FILE_EDIT", ...}},
    {"event_id": "EV-00000003", "command": {"operation_type": "BASH", ...}},
]

# Estado = projection(events)
```

### Vantagens sobre TOON

| Aspecto | TOON | ESAA |
|---------|------|------|
| Imutabilidade | Arquivo substituído | Eventos append-only |
| Audit trail | Não | Completo |
| Replay parcial | Não | Sim (qualquer ponto) |
| Branching | Não | Sim (event forks) |
| Verificação | Hash do arquivo | Hash criptográfico por evento |
| Compressão temporal | Não | Sim (intervalos configuráveis) |

---

## Modelos de Dados

### ESAAEventEnvelope

Cada evento é um envelope contendo comando, estado cognitivo e metadados criptográficos.

```python
class ESAAEventEnvelope(BaseModel):
    """
    Event envelope with cryptographic verification.

    Attributes:
        event_id: Unique identifier (format: EV-XXXXXXXX)
        timestamp: UTC timestamp of event creation
        command: The operation payload
        cryptographic_hash: SHA-256 hash for integrity
        schema_version: ESAA schema version
    """
    model_config = ConfigDict(frozen=True, strict=True)

    event_id: str = Field(pattern=r"^EV-\d{8}$")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    command: CommandPayload
    cryptographic_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: Literal["0.4.0"] = "0.4.0"
```

### CommandPayload

O comando encapsula a operação, o nó afetado e o estado cognitivo do agente.

```python
class CommandPayload(BaseModel):
    """
    Command payload with cognitive context.

    Attributes:
        operation_type: FILE_WRITE, FILE_EDIT, BASH, etc.
        target_node: File path or resource affected
        delta_payload: Serialized operation data
        cognitive_state: Agent's cognitive context
    """
    model_config = ConfigDict(frozen=True)

    operation_type: OperationType
    target_node: str | None = None
    delta_payload: str = ""
    cognitive_state: CognitiveTrace
```

### CognitiveTrace

Rastreamento do estado cognitivo do agente no momento da operação.

```python
class CognitiveTrace(BaseModel):
    """
    Cognitive state snapshot at event creation.

    Attributes:
        q_value: Estimated action value (-1.0 to 1.0)
        intention: Semantic description of intent
        risk_assessment: LOW, MEDIUM, HIGH, CRITICAL
        cila_context: Complexity level L0-L6
        agent_id: Identifier of the acting agent
    """
    model_config = ConfigDict(frozen=True)

    q_value: float = Field(ge=-1.0, le=1.0, default=0.0)
    intention: str = ""
    risk_assessment: RiskLevel = RiskLevel.LOW
    cila_context: CilaLevel = CilaLevel.L3
    agent_id: str = "kazuba"
```

---

## CILA Integration

ESAA integra-se profundamente com a taxonomia CILA (Complexity Intelligence Layer Architecture).

### Inferência Automática de CILA

O hook `esaa_bridge.py` infere o nível CILA automaticamente:

```python
def infer_cila_level(tool_name: str, tool_input: dict) -> CilaLevel:
    """Infer CILA level from tool usage patterns."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")

        # L6: Research/irreversible operations
        if any(d in command for d in DANGEROUS_PATTERNS):
            return CilaLevel.L6

        # L5: Expert-level build/optimization
        if "cargo build --release" in command or "maturin develop" in command:
            return CilaLevel.L5

        # L4: Advanced testing/validation
        if "pytest --cov" in command and "--cov-report" in command:
            return CilaLevel.L4

        # L2: Routine validation
        if "pytest" in command or "ruff check" in command:
            return CilaLevel.L2

    return CilaLevel.L3  # Default: Complex
```

### Impacto no Risk Assessment

| CILA Level | Risk Level Default | Verificação SHA-256 |
|------------|-------------------|---------------------|
| L0-L1 | LOW | Opcional |
| L2-L3 | MEDIUM | Recomendado |
| L4-L5 | HIGH | Obrigatório |
| L6 | CRITICAL | Obrigatório + auditoria |

---

## CLI ESAA

Comandos disponíveis via `kazuba esaa`:

### `esaa init`

Inicializa a estrutura ESAA em um projeto.

```bash
kazuba esaa init [--root /path/to/project]
```

Cria:
```
.esaa/
├── activity.jsonl          # Log de eventos (append-only)
├── schemas/
│   ├── activity.json       # JSON Schema para eventos
│   └── project.json        # JSON Schema para estado
└── roadmap.json            # Metadados do projeto ESAA
```

### `esaa submit`

Submete um evento manualmente ao log.

```bash
kazuba esaa submit \
    --operation FILE_WRITE \
    --target src/main.py \
    --delta '{"content": "..."}' \
    --cila L3 \
    --risk MEDIUM \
    --intention "Initial implementation"
```

### `esaa verify`

Verifica integridade criptográfica de todos os eventos.

```bash
kazuba esaa verify [--root /path/to/project] [--fix]
```

Verificações:
- Formato dos event IDs (EV-XXXXXXXX)
- SHA-256 hashes (recomputa e compara)
- Schema version consistency
- Timestamp ordering

### `esaa replay`

Reproduz eventos e projeta estado.

```bash
kazuba esaa replay \
    [--from 10] [--to 50] \
    [--output-format json|toon|table]
```

Modos de output:
- `json`: Estado projetado completo
- `toon`: Checkpoint no formato TOON
- `table`: Lista de operações em formato tabular

---

## Hook: esaa_bridge.py

Hook PreToolUse que converte tool calls em eventos ESAA.

### Fluxo de Execução

```
PreToolUse event
    │
    ▼
esaa_bridge.py (esaa_bridge hook)
    │
    ├── 1. Infer CILA level from tool name + input
    │
    ├── 2. Assess risk from CILA + operation type
    │
    ├── 3. Build CommandPayload with cognitive state
    │
    ├── 4. Generate cryptographic hash (SHA-256)
    │
    ├── 5. Write to .esaa/activity.jsonl
    │
    └── 6. Return hook result (always exit 0)
```

### Configuração

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "python .claude/kazuba-hooks/hooks/esaa_bridge.py",
        "description": "ESAA event sourcing bridge"
      }
    ]
  }
}
```

### Fields Extraídos

| Field Fonte | ESAA Destination |
|-------------|------------------|
| `tool_name` | `command.operation_type` (mapeado) |
| `tool_input` | `command.delta_payload` (JSON) |
| `file_path` | `command.target_node` |
| N/A (inferido) | `command.cognitive_state.cila_context` |
| N/A (inferido) | `command.cognitive_state.risk_assessment` |
| `session_id` | `activity.correlation.session_id` |

---

## Rust FFI Acceleration

ESAA inclui uma implementação Rust via PyO3 para projeção de eventos de alta performance.

### Módulos Rust

```rust
// rust/esaa-ffi/src/types.rs
pub struct ESAAEventEnvelope {
    pub event_id: String,
    pub timestamp: DateTime<Utc>,
    pub command: CommandPayload,
    pub cryptographic_hash: String,
    pub schema_version: String,
}

// rust/esaa-ffi/src/projector.rs
pub fn project_events(events: &[RawEventEntry]) -> ProjectedState {
    let mut state = empty_state("kazuba-esaa".to_string());
    for entry in events {
        if let Some(ref activity) = entry.activity_event {
            apply_event(&mut state, activity);
        }
    }
    state
}
```

### Build

```bash
cd rust/esaa-ffi
maturin develop --release
```

### Uso Python

```python
from claude_code_kazuba.rust_bridge import project_events_rust

# Projeção rápida via Rust
state_json = project_events_rust(events_json)
state = ProjectedState.model_validate_json(state_json)
```

---

## RLM Integration

ESAA alimenta o módulo RLM (Reinforcement Learning Memory) com eventos estruturados.

### ingest_esaa_events()

```python
class RLMFacade:
    def ingest_esaa_events(self, events: list[Any]) -> None:
        """
        Extract patterns from ESAA events to update Q-values.

        Maps event properties to RL state/action space:
        - State: {operation}:{risk}:{cila}
        - Action: cognitive.intention
        - Reward: computed from outcome
        """
        for event in events:
            cognitive = event.command.cognitive_state
            reward = RewardCalculator.from_event(event)

            state = f"{event.command.operation_type.value}:"
                   f"{cognitive.risk_assessment.value}:"
                   f"{cognitive.cila_context.value}"
            action = cognitive.intention

            self.record_step(state=state, action=action, reward=reward)
```

### Reward Calculation

```python
class RewardCalculator:
    BASE_SUCCESS = 1.0
    BASE_FAILURE = -1.0

    RISK_MULTIPLIERS = {
        RiskLevel.LOW: 1.0,
        RiskLevel.MEDIUM: 1.5,
        RiskLevel.HIGH: 2.0,
        RiskLevel.CRITICAL: 3.0,
    }

    @classmethod
    def from_event(cls, event: ESAAEventEnvelope) -> float:
        """Compute reward from ESAA event."""
        base = cls.BASE_SUCCESS if event.success else cls.BASE_FAILURE
        multiplier = cls.RISK_MULTIPLIERS[event.cognitive_state.risk_assessment]
        return base * multiplier
```

### Golden Routes

Trajetórias de alta recompensa são extraídas para aprendizado:

```python
def extract_golden_routes(self, min_q_threshold: float = 0.8) -> list[dict]:
    """Extract high-reward trajectories as Golden Routes."""
    golden = []
    session_stats = self._session.stats()

    for ep in session_stats.get("episodes", []):
        if ep.get("total_reward", 0) >= min_q_threshold:
            golden.append({
                "episode_id": ep["episode_id"],
                "avg_reward": ep["average_reward"],
                "steps": ep["step_count"],
            })

    return sorted(golden, key=lambda x: x["avg_reward"], reverse=True)
```

---

## Shadow Mode: Benchmark ESAA

Modo sombra que executa ESAA em paralelo com TOON para validação.

### Executando Benchmarks

```bash
python scripts/benchmark_esaa.py \
    --iterations 1000 \
    --output results.json \
    --tmp-dir /tmp/esaa_benchmark
```

### Métricas Coletadas

```python
@dataclass
class BenchmarkResult:
    iteration: int
    toon_time_ns: int      # Tempo TOON em nanosegundos
    esaa_time_ns: int      # Tempo ESAA em nanosegundos
    overhead_ratio: float  # ESAA / TOON
    hash_match: bool       # Equivalência de estado
```

### Relatório de Saída

```
======================================================================
ESAA vs TOON Benchmark Results
======================================================================

Iterations: 1000
Timestamp: 2026-03-03T12:00:00Z

--- TOON Performance ---
  P50: 0.234 ms
  P95: 0.312 ms
  P99: 0.389 ms

--- ESAA Performance ---
  P50: 0.267 ms
  P95: 0.356 ms
  P99: 0.445 ms

--- Overhead Ratio (ESAA / TOON) ---
  P50: 1.08x
  P95: 1.14x
  P99: 1.19x

--- Validation ---
  All hashes match: True

✅ PASS: Overhead < 20% at P95
======================================================================
```

---

## Mapeamento TOON ↔ ESAA

| TOON Concept | ESAA Equivalent |
|--------------|-----------------|
| Checkpoint file | Stream de eventos |
| Phase ID | Event sequence number |
| Title | Activity description aggregation |
| Timestamp | Event timestamp |
| Results | Projected state fields |
| File list | Indexes.files_modified |
| Verification flag | ActivityEvent.verification_result |

### Exemplo: Conversão

```python
# TOON checkpoint
toon_data = {
    "phase_id": 5,
    "title": "Implement ESAA",
    "files_modified": ["esaa_types.py", "projector.py"],
    "verification_passed": True,
}

# ESAA equivalente (projetado)
esaa_state = ProjectedState(
    meta=MetaState(
        schema_version="0.4.0",
        projection_timestamp=datetime.now(timezone.utc),
        event_count=5,
        deterministic_hash="abc123...",
    ),
    project=ProjectInfo(
        project_id="kazuba-esaa",
        phase="implement_esaa",
        checkpoint_id="CHK-00000005",
    ),
    tasks=TaskList(
        active=[
            Task(
                task_id="TK-0001",
                description="Implement ESAA",
                status=TaskStatus.COMPLETED,
            )
        ]
    ),
    indexes=Indexes(
        files_modified=["esaa_types.py", "projector.py"],
        events_by_phase={"5": ["EV-00000001", "EV-00000002"]},
    ),
)
```

---

## Migração TOON → ESAA

Para projetos existentes com checkpoints TOON:

```python
from claude_code_kazuba.checkpoint import load_toon
from claude_code_kazuba.models.esaa_types import checkpoint_to_events

# 1. Carregar checkpoint TOON
toon_data = load_toon(Path("checkpoints/phase_05.toon"))

# 2. Converter para eventos ESAA
events = checkpoint_to_events(toon_data)

# 3. Salvar em activity.jsonl
for event in events:
    append_to_activity_log(event)

# 4. Verificar integridade
verify_esaa_log()
```

---

## Referência Rápida

### Tipos de Operação

```python
class OperationType(Enum):
    FILE_WRITE = "FILE_WRITE"
    FILE_EDIT = "FILE_EDIT"
    FILE_DELETE = "FILE_DELETE"
    BASH = "BASH"
    READ = "READ"
    GLOB = "GLOB"
    GREP = "GREP"
    AGENT = "AGENT"
    SKILL = "SKILL"
```

### Níveis de Risco

```python
class RiskLevel(Enum):
    LOW = "LOW"           # Operações de leitura, análise
    MEDIUM = "MEDIUM"     # Escrita em arquivos de teste
    HIGH = "HIGH"         # Modificação em código de produção
    CRITICAL = "CRITICAL" # Git push, deleção, deploy
```

### Status de Tarefa

```python
class TaskStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
```

---

## Troubleshooting

### Event ID Duplicado

```bash
# Erro: Event ID EV-00000005 already exists
kazuba esaa verify --fix
```

O modo `--fix` renumera eventos duplicados mantendo ordem temporal.

### Hash Mismatch

```bash
# Erro: Cryptographic hash verification failed
kazuba esaa replay --from 1 --to 10 --output-format json
```

Verifique se o arquivo não foi modificado manualmente. ESAA logs são append-only.

### Schema Version Incompatível

```python
# Upgrade de schema
from claude_code_kazuba.models.esaa_types import migrate_events

old_events = load_events(".esaa/activity.jsonl")
new_events = migrate_events(old_events, from_version="0.3.0", to_version="0.4.0")
save_events(".esaa/activity.jsonl", new_events)
```

---

*Documentação ESAA v0.4.0 — Parte do claude-code-kazuba framework*
