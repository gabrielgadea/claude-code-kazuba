import sys
import json
from enum import Enum
from dataclasses import dataclass
from typing import Any, List
import ast

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.dangerous_calls = []
        
    def visit_Call(self, node):
        if hasattr(node, 'func'):
            if isinstance(node.func, ast.Name):
                if node.func.id in ['open', 'eval', 'exec', 'system']:
                    self.dangerous_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ['system', 'popen', 'call']:
                    self.dangerous_calls.append(node.func.attr)
        self.generic_visit(node)

class ValidationStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

@dataclass
class ValidationResult:
    phase: str
    check_name: str
    status: ValidationStatus
    expected: Any
    actual: Any
    message: str
    remediation: str | None = None

class QualityGates:
    """
    Subagente: Validator N1
    Gates obrigatórios por onde todo script N0 passa antes de ser habilitado 
    para disparo pelo ACO. É a camada 1 do Protocolo de Validação.
    """

    @staticmethod
    def run_meta_validation(generator_id: str, execute_script: str, validate_script: str, rollback_script: str) -> List[ValidationResult]:
        results = []
        
        # 1. Triad Complete Check
        has_triad = bool(execute_script and validate_script and rollback_script)
        results.append(ValidationResult(
            phase="meta-validation",
            check_name="triad_completeness",
            status=ValidationStatus.PASS if has_triad else ValidationStatus.FAIL,
            expected=True,
            actual=has_triad,
            message="O gerador produziu a tríade completa (execute, validate, rollback)?"
        ))
        
        # 2. Type-Safe / Magic Numbers Check
        # Exemplo simples, em produção usaríamos um AST Parser aqui.
        magic_numbers_found = " 42 " in execute_script or " 0" in execute_script
        results.append(ValidationResult(
            phase="meta-validation",
            check_name="magic_numbers_check",
            status=ValidationStatus.PASS if not magic_numbers_found else ValidationStatus.WARN,
            expected=False,
            actual=magic_numbers_found,
            message="Zero magic numbers: Toda constante tem nome e documentação."
        ))

        # 3. MCTS Parallel Safety Check / AST Security Verification
        is_safe = True
        ast_message = "O gerador deveria usar mutações FFI/ESAA, não funções perigosas."
        
        try:
            tree = ast.parse(execute_script)
            visitor = SecurityVisitor()
            visitor.visit(tree)
            
            if visitor.dangerous_calls:
                is_safe = False
                ast_message = f"Chamadas AST perigosas detectadas: {visitor.dangerous_calls}. Use funções providas pelo contexto MCTS."
        except SyntaxError as e:
            is_safe = False
            ast_message = f"Injeção inválida - SyntaxError detectado: {str(e)}"

        results.append(ValidationResult(
            phase="meta-validation",
            check_name="mcts_parallel_safety_ast",
            status=ValidationStatus.PASS if is_safe else ValidationStatus.FAIL,
            expected=True,
            actual=is_safe,
            message=ast_message
        ))

        return results

    @staticmethod
    def is_gate_passed(results: List[ValidationResult]) -> bool:
        """Só passa se não houver um único FAIL."""
        return all(r.status != ValidationStatus.FAIL for r in results)

if __name__ == "__main__":
    # Test runner for meta-validation
    print("Quality Gates OK - Initialized")
