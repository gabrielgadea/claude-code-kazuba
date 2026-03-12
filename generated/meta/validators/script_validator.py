import sys
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ValidationReport:
    is_valid: bool
    errors: list[str]

class ScriptValidator:
    """
    Camada Transversal: Validador N2
    Opera entre a camada N1 (geração) e N0 (execução).
    Garante que a Tríade criada por um Gerador N1 não quebra as invariantes
    do repositório ESAA-Kazuba antes de ir pro CodeGen N0.
    """
    
    @staticmethod
    def validate_triad_directory(task_dir: Path) -> ValidationReport:
        errors = []
        
        # O Diretório existe?
        if not task_dir.exists() or not task_dir.is_dir():
            return ValidationReport(False, [f"Diretório {task_dir} não encontrado."])
            
        # Contém o arquivo secreto hash do N1? (Comprova que N1 concluiu)
        hash_file = task_dir / ".n1_hash"
        if not hash_file.exists():
            errors.append("Falta a certificação `.n1_hash`. Script N0 forjado ou incompleto.")
            
        # Verificar sintaxe python base dos 3 scripts (Camada mínima antes do teste real)
        import py_compile
        for script in ["execute.py", "validate.py", "rollback.py"]:
            file_path = task_dir / script
            if not file_path.exists():
                errors.append(f"Script obrigatório não foi gerado: {script}")
                continue
                
            try:
                py_compile.compile(str(file_path), doraise=True)
            except Exception as e:
                errors.append(f"Erro de Compilação Sintática em {script}: {str(e)}")
                
        return ValidationReport(len(errors) == 0, errors)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script_validator.py <task_dir_path>")
        sys.exit(1)
        
    target = Path(sys.argv[1])
    report = ScriptValidator.validate_triad_directory(target)
    
    if report.is_valid:
        print("VALID: Scripts Prontos para Execução N0.")
        sys.exit(0)
    else:
        print(f"INVALID: {report.errors}")
        sys.exit(1)
