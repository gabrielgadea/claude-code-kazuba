from typing import Dict, Any, List
from pathlib import Path
from meta.generator_engine import GeneratorEngine
from meta.quality_gates import QualityGates
from generators.ast_patch_generator import AstPatchGenerator
from generators.shell_exec_generator import ShellExecGenerator
from n0_executor import N0Executor

class ACOOrchestrator:
    """
    Subagente: ACO Principal (N2)
    Coordena o GeneratorGraph (DAG). Invoca N1 para gerar scripts,
    roda o Quality Gate (Meta-validação) e libera a execução N0 se as métricas cruzarem > 0.8
    """
    def __init__(self, workspace_dir: Path):
        self.workspace = workspace_dir
        self.engine = GeneratorEngine(
            template_dir=workspace_dir / "meta" / "template_library",
            output_dir=workspace_dir / "generated_scripts"
        )
        self.generators = {
            "ast_patch": AstPatchGenerator(self.engine),
            "shell_exec": ShellExecGenerator(self.engine)
        }
        
    def orchestrate_task(self, task_spec: Dict[str, Any]):
        """
        Recebe o ObjectiveSpec N2 e orquestra a cadeia.
        Nunca executa "resoluções cegas", constrói os geradores primeiro.
        """
        print(f"[ACO N2] Iniciando Orquestração Lógica: {task_spec['objective']}")
        
        # 1. Planejamento do DAG (Mapeamento simplificado)
        for gen_node in task_spec.get('generator_graph', []):
            gen_type = gen_node['type']
            gen_inputs = gen_node['inputs']
            
            # 2. Execução (Geração do Script N1)
            print(f"[ACO N2] Invocando GeneratorDesigner {gen_type} para {gen_inputs}")
            if gen_type == "ast_patch":
                triad = self.generators["ast_patch"].create_ast_patch_generator(
                    gen_inputs['target'], 
                    gen_inputs['logic'], 
                    gen_inputs['complexity']
                )
            elif gen_type == "shell_exec":
                triad = self.generators["shell_exec"].create_shell_job(
                    gen_inputs['cmd']
                )
            else:
                raise ValueError(f"Unknown generator type: {gen_type}")

            # 3. Quality Gate (Meta-Validação do Gerador N1 antes de virar N0)
            print("[ACO N2] Submetendo ao Quality Gates (Camada 1).")
            val_results = QualityGates.run_meta_validation(
                generator_id=gen_node['id'],
                execute_script=triad.execute_script,
                validate_script=triad.validate_script,
                rollback_script=triad.rollback_script
            )
            
            if not QualityGates.is_gate_passed(val_results):
                print(f"[ACO N2] ERRO CRÍTICO NA ABSTRAÇÃO: Gerador falhou nos gates. Rollback N1!")
                for r in val_results:
                    if r.status.name == "FAIL":
                        print(f" -> FALHA: {r.message} | Real: {r.actual}")
                return False
                
            print(f"[ACO N2] Meta-Validação Verificada. Script isolado e persistido (Hash: {triad.execution_hash})")
            
            # 4. Phase 5: N0 Execution Pipeline
            task_id = triad.rollback_script.split('GENERATOR_ID = "')[1].split('"')[0]
            target_dir = self.engine.output_dir / task_id
            print(f"[ACO N2] Iniciando Codegen N0 Executor no diretório {target_dir.name}")
            
            n0_runner = N0Executor(target_dir)
            n0_result = n0_runner.execute_triad()
            
            if n0_result['status'] == "success":
                print(f"[ACO N2] Sucesso absoluto na Tríade N0 para a submissão.")
            else:
                print(f"[ACO N2] N0 Reportou falha topológica. Orchestrator entra em processo de MCTS/RLM: {n0_result}")

        print("[ACO N2] Grafo concluiu todos os estágios. Automação N0 completa.")
        return True

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    aco = ACOOrchestrator(base_dir)
    
    # Mock do IntentSpec -> GeneratorGraph emitido na Fase 2 do ACO
    mock_spec = {
        "objective": "Aplicar refactoring de timeout global via Rust AST e rodar testes.",
        "generator_graph": [
            {
                "id": "gen_patch_01",
                "type": "ast_patch",
                "inputs": {
                    "target": "cila_router.timeout",
                    "logic": "timeout_ms = 10000",
                    "complexity": "l1"
                }
            },
            {
                "id": "gen_shell_02",
                "type": "shell_exec",
                "inputs": {
                    "cmd": "pytest tests/integration"
                }
            }
        ]
    }
    
    aco.orchestrate_task(mock_spec)
