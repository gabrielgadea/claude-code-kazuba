import subprocess
from dataclasses import dataclass
from typing import Any
from pathlib import Path
import json

@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: str
    phase: str

class N0Executor:
    """
    Subagente: CodeGen (N0 Layer)
    Recebe um diretório de scripts da tríade N0 validada pelo N1.
    Executa a tríade. O ACO exige:
      1. Execute_script
      2. Se OK -> Validate_script
      3. Se ERROR -> Rollback_script
    """
    
    def __init__(self, task_dir: Path):
        self.task_dir = task_dir
        
    def _run_script(self, script_name: str) -> ExecutionResult:
        script_path = self.task_dir / script_name
        if not script_path.exists():
            return ExecutionResult(False, "", f"Script {script_name} not found.", script_name)
            
        try:
            result = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
                check=False
            )
            success = result.returncode == 0
            return ExecutionResult(success, result.stdout, result.stderr, script_name)
        except Exception as e:
            return ExecutionResult(False, "", str(e), script_name)

    def execute_triad(self) -> dict[str, Any]:
        """Aplica a governança do ACO: Validação e Rollback imbuídos na execução."""
        print(f"\n[CodeGen N0] Iniciando triad na pasta: {self.task_dir.name}")
        
        # 1. EXECUTE PHASE
        print("[CodeGen N0] Rodando execute.py...")
        exec_res = self._run_script("execute.py")
        
        if not exec_res.success:
            print(f"[CodeGen N0] ERRO FASE EXECUTE: {exec_res.error}")
            return self._trigger_rollback("execute.py_failed", exec_res)
            
        print("[CodeGen N0] Execute rodado com sucesso.")
        
        # 2. VALIDATE PHASE
        print("[CodeGen N0] Rodando validate.py...")
        val_res = self._run_script("validate.py")
        
        if not val_res.success:
            print(f"[CodeGen N0] ERRO FASE VALIDATE (Invariants quebradas): {val_res.error}")
            return self._trigger_rollback("validate.py_failed", val_res)
            
        print(f"[CodeGen N0] Validate passou. Tarefa {self.task_dir.name} materializada no mundo físico.")
        return {
            "status": "success",
            "execute_output": exec_res.output.strip(),
            "validate_output": val_res.output.strip()
        }

    def _trigger_rollback(self, failure_point: str, result: ExecutionResult) -> dict[str, Any]:
        print("[CodeGen N0] >>> INICIANDO SAGA ROLLBACK <<<")
        roll_res = self._run_script("rollback.py")
        
        if roll_res.success:
            print(f"[CodeGen N0] Rollback Concluído. Feedback RLM emitido.")
            return {
                "status": "failed_but_rolled_back",
                "failure_point": failure_point,
                "error_details": result.error.strip(),
                "rollback_output": roll_res.output.strip()
            }
        else:
            print(f"[CodeGen N0] [ALARM] CORRUPÇÃO TOTAL. Rollback também falhou: {roll_res.error}")
            return {
                "status": "critical_corruption",
                "failure_point": failure_point,
                "rollback_error": roll_res.error.strip()
            }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 n0_executor.py <task_dir_path>")
        sys.exit(1)
        
    target = Path(sys.argv[1])
    executor = N0Executor(target)
    result = executor.execute_triad()
    print("\n--- FINAL RESULT ---")
    print(json.dumps(result, indent=2))
