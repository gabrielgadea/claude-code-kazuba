import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from meta.generator_engine import GeneratorEngine
from meta.quality_gates import QualityGates
from meta.event_store import EventStore
from generators.ast_patch_generator import AstPatchGenerator
from generators.shell_exec_generator import ShellExecGenerator
from n0_executor import N0Executor

class MCTSOrchestrator:
    """
    Motor N2: Roda como MCTS (Monte Carlo Tree Search), despachando N0 Executors 
    em concorrência e armazenando no `EventStore` para Reinforcement Learning (RLM).
    """

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.engine = GeneratorEngine(
            template_dir=self.base_dir / "meta" / "template_library", 
            output_dir=self.base_dir / "generated_scripts"
        )
        self.event_store = EventStore(self.base_dir / "database")
        self.generators = {
            "ast_patch": AstPatchGenerator(self.engine),
            "shell_exec": ShellExecGenerator(self.engine)
        }

    def _execute_branch(self, generator_id: str, validation_reports: list) -> Dict[str, Any]:
        """A função alvo da Thread Pool para paralelismo MCTS."""
        if not QualityGates.is_gate_passed(validation_reports):
            self.event_store.append_event(
                action="output.rejected", 
                task_id=generator_id, 
                payload={
                    "reason": "MCTS_PRUNED QualityGate Failed",
                    "validation_reports": [r.message for r in validation_reports]
                }
            )
            return {"generator_id": generator_id, "status": "blocked_by_gate"}
            
        target_dir = self.engine.output_dir / generator_id
        n0_runner = N0Executor(target_dir)
        n0_result = n0_runner.execute_triad()
        
        # Leve a trilha pra base imutável via Vocabulário ESAA estrito
        action = "verify.ok" if n0_result['status'] == 'success' else "verify.fail"
        self.event_store.append_event(
            action=action, 
            task_id=generator_id,
            payload={"n0_result": n0_result}
        )
        
        return {"generator_id": generator_id, "n0_result": n0_result}

    def orchestrate_parallel_DAG(self, intentions: List[Dict[str, Any]]) -> bool:
        """
        Recebe um grafo lógico de intensões do Claude Code e expande-o materialmente 
        disparando geradores + executores em threads pools.
        """
        print(f"[ACO N2 MCTS] Iniciando Expansão MCTS Paralela para {len(intentions)} intenções.")
        
        pending_futures = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            for task in intentions:
                gen_name = task["generator"]
                params = task["params"]
                
                print(f"[ACO N2 MCTS] Thread Pool scheduling {gen_name}")
                if gen_name == "ast_patch":
                    triad = self.generators["ast_patch"].create_ast_patch_generator(**params)
                elif gen_name == "shell_exec":
                    triad = self.generators["shell_exec"].create_shell_job(**params)
                else:
                    continue

                # Roda Quality Gate Camada 1 síncrona para decidir se dropa ou envia pra Thread
                val_reports = QualityGates.run_meta_validation(
                    triad.execution_hash,
                    triad.execute_script,
                    triad.validate_script,
                    triad.rollback_script
                )
                
                # Despacha o galho MCTS (A Fase N0 de isolamento e execução)
                future = executor.submit(self._execute_branch, triad.execute_script.split('GENERATOR_ID = "')[1].split('"')[0], val_reports)
                pending_futures.append(future)
                
            # Coleta de Rollouts
            for future in as_completed(pending_futures):
                res = future.result()
                print(f"[ACO N2 MCTS] Rollout completado. Resultado do nó: {res['status'] if 'status' in res else res['n0_result']['status']}")

        print("[ACO N2 MCTS] Monte Carlo Tree Search esgotada. Verifique o activity.jsonl para auditoria RLM.")
        return True

if __name__ == "__main__":
    dag = [
        {"generator": "ast_patch", "params": {"target_node": "cila_router.timeout", "patch_logic": "timeout_ms = 10000", "complexity": "l1"}},
        {"generator": "shell_exec", "params": {"command": "pytest tests/integration", "timeout_ms": 10000}}
    ]

    orch = MCTSOrchestrator()
    orch.orchestrate_parallel_DAG(dag)
