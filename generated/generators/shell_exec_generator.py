from typing import Dict, Any
from pathlib import Path
from meta.generator_engine import GeneratorSpec, GeneratorEngine, TriadOutput

class ShellExecGenerator:
    """
    Subagente: GeneratorDesigner (N1)
    Gera scripts que invocam shell (Ex: Run Tests), contendo Quarentena estrita.
    """
    
    def __init__(self, engine: GeneratorEngine):
        self.engine = engine
        
    def create_shell_job(self, command: str, timeout_ms: int = 5000) -> TriadOutput:
        spec = GeneratorSpec(
            generator_id=f"SHELL_EXEC_{abs(hash(command))}",
            description=f"Executa job isolado: {command}",
            generator_type="validator",
            inputs={"command": command, "timeout": timeout_ms},
            constraints=[f"Max execution time {timeout_ms}ms", "No root/sudo allowed"],
            preconditions=["Needs Bash"],
            postconditions=["Exit code 0"],
            invariants=["Isolamento de ambiente (Docker/Sandbox)"]
        )
        
        context_data = {
            "operation": "ShellExec",
            "cmd": command,
            "timeout_ms": timeout_ms
        }
        
        triad = self.engine.run_generator(spec, context_data)
        return triad

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    engine = GeneratorEngine(
        template_dir=base_dir / "meta" / "template_library", 
        output_dir=base_dir / "generated_scripts"
    )
    generator = ShellExecGenerator(engine)
    print("ShellExecGenerator Initialized")
