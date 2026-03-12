from __future__ import annotations
from typing import Dict, Any, List, Optional
import json
import hashlib
from pathlib import Path
from .esaa_contracts import GeneratorSpec, TriadOutput

class GeneratorEngine:
    """
    Subagente: ACO Generator Engine (N1)
    Responsável por instanciar templates, aplicar o GeneratorSpec e expelir a Tríade N0.
    """
    
    def __init__(self, template_dir: Path, output_dir: Path):
        self.template_dir = template_dir
        self.output_dir = output_dir
        
    def _load_template(self, template_name: str) -> str:
        template_file = self.template_dir / f"{template_name}.py.tmpl"
        if not template_file.exists():
            raise FileNotFoundError(f"Template {template_name} não encontrado no Registry.")
        return template_file.read_text(encoding='utf-8')

    def run_generator(self, spec: GeneratorSpec, context_data: Dict[str, Any]) -> TriadOutput:
        """
        Gera a tríade baseada na especificação stricta.
        Nunca resolve diretamente a intenção, mas parametriza o template executor.
        """
        # Load Templates
        exec_tmpl = self._load_template("executor_template")
        val_tmpl = self._load_template("validator_template")
        roll_tmpl = self._load_template("rollback_template")

        # Injetar os contratos do Spec nas validações
        val_compiled = val_tmpl.replace("{{PRECONDITIONS}}", json.dumps(spec.preconditions))
        val_compiled = val_compiled.replace("{{POSTCONDITIONS}}", json.dumps(spec.postconditions))
        val_compiled = val_compiled.replace("{{INVARIANTS}}", json.dumps(spec.invariants))

        # Compilar Executor Parametrizado
        exec_compiled = exec_tmpl.replace("{{GENERATOR_ID}}", spec.generator_id)
        exec_compiled = exec_compiled.replace("{{PAYLOAD_DATA}}", json.dumps(context_data))
        
        # Compilar Rollback Parametrizado
        roll_compiled = roll_tmpl.replace("{{GENERATOR_ID}}", spec.generator_id)

        # Hash construction since the Pydantic spec prevents mutating it via post_init
        content = exec_compiled + val_compiled + roll_compiled
        calc_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        output = TriadOutput(
            execute_script=exec_compiled,
            validate_script=val_compiled,
            rollback_script=roll_compiled,
            execution_hash=calc_hash
        )
        
        self._persist_triad(spec.generator_id, output)
        return output

    def _persist_triad(self, task_id: str, triad: TriadOutput):
        """Persiste os scripts gerados (N0) para invocação limpa da Swarm CodeGen."""
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        (task_dir / "execute.py").write_text(triad.execute_script)
        (task_dir / "validate.py").write_text(triad.validate_script)
        (task_dir / "rollback.py").write_text(triad.rollback_script)
        
        # Adiciona flag do compliance hash
        (task_dir / ".n1_hash").write_text(triad.execution_hash)
