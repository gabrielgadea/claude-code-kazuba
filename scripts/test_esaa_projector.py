import sys
from pathlib import Path
from pprint import pprint

# Setup paths
base_dir = Path(__file__).parent.parent / "generated"
sys.path.append(str(base_dir))

from meta.event_store import EventStore
from meta.esaa_projector import ESAAProjector
from n2_mcts_orchestrator import MCTSOrchestrator

def run_esaa_test():
    print("--- 1. Inicializando ESAA EventStore ---")
    store = EventStore(base_dir / "database")
    
    # Send an initial task.create
    task_id = "TASK-TEST-001"
    store.append_event("task.create", task_id, {"description": "Validating ESAA Hash Projection"})
    
    print("--- 2. Rodando o MCTS Orchestrator ---")
    orch = MCTSOrchestrator()
    # Mocking an intention that resolves quickly
    dag = [
        {"generator": "shell_exec", "params": {"command": "echo 'ESAA Core Online'", "timeout_ms": 1000}}
    ]
    orch.orchestrate_parallel_DAG(dag)
    
    print("\n--- 3. Lendo o Log Epistêmico e Projetando ---")
    events = store.query_history()
    print(f"Total de eventos lidos: {len(events)}")
    
    projected = ESAAProjector.project_events(events)
    print("\n--- Roadmap Projectado ---")
    pprint(projected)
    
    print("\n--- 4. Computando ESAA Canonical Hash ---")
    computed_hash = ESAAProjector.compute_sha256(projected)
    print(f"HASH SHA-256: {computed_hash}")
    
    # Simulate a roadmap.json state
    roadmap_mock = {
        "meta": {
            "run": {
                "projection_hash_sha256": computed_hash
            }
        }
    }
    
    print("\n--- 5. Executando esaa verify ---")
    result = ESAAProjector.esaa_verify(events, roadmap_mock)
    print(f"Resultado da Verificação: {result['verify_status']}")
    
    if result['verify_status'] == 'ok':
        print("\n✅ ALINHAMENTO CORE ESAA VALIDADO COM SUCESSO!")
    else:
        print("\n❌ FALHA NO ALINHAMENTO ESAA!")

if __name__ == "__main__":
    run_esaa_test()
