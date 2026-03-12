import sys
from pathlib import Path
import json

base_dir = Path(__file__).parent.parent / "generated"
sys.path.append(str(base_dir))

from n2_mcts_orchestrator import MCTSOrchestrator
from meta.event_store import EventStore
from meta.esaa_projector import ESAAProjector

def run_esaa_live_demo():
    print("==========================================================")
    print("   ESAA NEURO-ARCHITECTURE DEMO (KAZUBA + CLAUDE CODE)    ")
    print("==========================================================\n")

    print("[1. CÓRTEX PRÉ-FRONTAL] Claude Code emite intenções (MCTS DAG)...")
    # This dag simulates 2 parallel sub-tasks sent by Claude
    dag = [
        {"generator": "ast_patch", "params": {"target_node": "cila_router.timeout", "patch_logic": "timeout_ms = 10000", "complexity": "l1"}},
        {"generator": "shell_exec", "params": {"command": "echo 'ESAA Peripheral Nerve executing!'", "timeout_ms": 10000}}
    ]

    orch = MCTSOrchestrator()
    print("\n[2. CEREBELO & MEDULA] Expandindo N1 Generators, passando por QualityGates e rodando N0 Executors...")
    # This step executes the Pydantic generation, AST validation, and shadow directory isolated runs.
    orch.orchestrate_parallel_DAG(dag)
    
    # Read the event store
    print("\n[3. SISTEMA LÍMBICO] Lendo o EventStore (activity.jsonl) para capturar o aprendizado (Reward/Trauma)...")
    events = orch.event_store.query_history()
    print(f"   -> Encontrados {len(events)} eventos na memória consolidada (Event_Seq Monotone).")
    
    print("\n[4. TRONCO ENCEFÁLICO] Projetando determinismo absoluto e computando SHA-256 (roadmap.json)...")
    projected = ESAAProjector.project_events(events)
    
    print("\n----------------- ROADMAP.JSON SNAPSHOT -----------------")
    print(json.dumps(projected, indent=2))
    print("---------------------------------------------------------")
    
    computed_hash = ESAAProjector.compute_sha256(projected)
    print(f"\n[5. VERIFICADOR FÍSICO (esaa verify)] Assinatura Criptográfica: {computed_hash}")
    
    # Verify 
    roadmap_mock = {"meta": {"run": {"projection_hash_sha256": computed_hash}}}
    result = ESAAProjector.esaa_verify(events, roadmap_mock)
    
    if result['verify_status'] == 'ok':
        print("\n✅ VALIDAÇÃO METAFÓRICA E FÍSICA ESAA COMPLETA E PERFEITA!")
    else:
        print("\n❌ FALHA NA VALIDAÇÃO!")

if __name__ == "__main__":
    run_esaa_live_demo()
