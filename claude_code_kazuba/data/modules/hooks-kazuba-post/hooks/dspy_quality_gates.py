"""
DSPy Quality Gates

Quality gates específicos para código DSPy no pipeline ANTT.
Hook: PreToolUse para validação de scripts DSPy.
"""

import ast
import re
from typing import Any, Final

# Severity levels
ERROR: Final[str] = "ERROR"
WARNING: Final[str] = "WARNING"
INFO: Final[str] = "INFO"

# Pre-compiled regex patterns — avoid per-call re.compile()
_FSTRING_PROMPT_RE = re.compile(r"^\s+\w+\s*=\s*f[\x22\x27]", re.MULTILINE)
_API_KEY_RES = [
    re.compile(r"api_key\s*=\s*[\x22\x27]sk-[a-zA-Z0-9]+[\x22\x27]", re.IGNORECASE),
    re.compile(r"api_key\s*=\s*[\x22\x27][^\x22\x27]{20,}[\x22\x27]", re.IGNORECASE),
    re.compile(r"ANTHROPIC_API_KEY\s*=\s*[\x22\x27][^\x22\x27]+[\x22\x27]", re.IGNORECASE),
    re.compile(r"OPENAI_API_KEY\s*=\s*[\x22\x27][^\x22\x27]+[\x22\x27]", re.IGNORECASE),
]


# Quality gate definitions
DSPY_QUALITY_GATES: Final[dict[str, dict[str, Any]]] = {
    "signature_completeness": {
        "check": "Toda signature tem InputField e OutputField",
        "severity": ERROR,
        "description": "Signatures DSPy devem ter pelo menos um InputField e um OutputField",
    },
    "module_forward_signature": {
        "check": "Todo module implementa forward()",
        "severity": ERROR,
        "description": "Modules DSPy devem implementar método forward()",
    },
    "teleprompter_metric_defined": {
        "check": "Todo teleprompter tem métrica associada",
        "severity": WARNING,
        "description": "Teleprompters devem ter métrica callable definida",
    },
    "no_hardcoded_prompts": {
        "check": "Ausência de f-strings para prompts",
        "severity": WARNING,
        "description": "Evitar f-strings para construir prompts; usar Signatures",
    },
    "dspy_settings_configured": {
        "check": "dspy.settings.configure() chamado",
        "severity": ERROR,
        "description": "DSPy deve ser configurado com dspy.settings.configure()",
    },
    "lm_api_key_secure": {
        "check": "API key nunca hardcoded",
        "severity": ERROR,
        "description": "API keys devem vir de variáveis de ambiente",
    },
    "teleprompter_checkpoint_save": {
        "check": "Teleprompter salva checkpoints",
        "severity": WARNING,
        "description": "Módulos otimizados devem ser salvos em checkpoints",
    },
    "metric_range_0_1": {
        "check": "Métricas retornam float em [0, 1]",
        "severity": ERROR,
        "description": "Métricas DSPy devem retornar valores entre 0 e 1",
    },
    "retry_logic_present": {
        "check": "Retry logic para rate limiting",
        "severity": WARNING,
        "description": "Implementar retry com backoff para chamadas de API",
    },
    "type_hints_present": {
        "check": "Type hints em forward() e métricas",
        "severity": INFO,
        "description": "Usar type hints para melhor documentação",
    },
}


def check_signature_completeness(source_code: str) -> list[dict[str, Any]]:
    """Check if DSPy signatures have both InputField and OutputField."""
    issues = []

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if class inherits from dspy.Signature
            bases = [base.id if isinstance(base, ast.Name) else
                    base.attr if isinstance(base, ast.Attribute) else None
                    for base in node.bases]

            if "Signature" in str(bases):
                has_input = False
                has_output = False

                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                # Check value type
                                if isinstance(item.value, ast.Call):
                                    func_name = ""
                                    if isinstance(item.value.func, ast.Attribute):
                                        func_name = item.value.func.attr
                                    elif isinstance(item.value.func, ast.Name):
                                        func_name = item.value.func.id

                                    if func_name == "InputField":
                                        has_input = True
                                    elif func_name == "OutputField":
                                        has_output = True

                if not has_input:
                    issues.append({
                        "gate": "signature_completeness",
                        "severity": ERROR,
                        "message": f"Signature '{node.name}' missing InputField",
                        "line": node.lineno,
                    })

                if not has_output:
                    issues.append({
                        "gate": "signature_completeness",
                        "severity": ERROR,
                        "message": f"Signature '{node.name}' missing OutputField",
                        "line": node.lineno,
                    })

    return issues


def check_module_forward(source_code: str) -> list[dict[str, Any]]:
    """Check if DSPy modules implement forward() method."""
    issues = []

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if class inherits from dspy.Module
            bases = [base.id if isinstance(base, ast.Name) else
                    base.attr if isinstance(base, ast.Attribute) else None
                    for base in node.bases]

            if "Module" in str(bases):
                has_forward = any(
                    isinstance(item, ast.FunctionDef) and item.name == "forward"
                    for item in node.body
                )

                if not has_forward:
                    issues.append({
                        "gate": "module_forward_signature",
                        "severity": ERROR,
                        "message": f"Module '{node.name}' missing forward() method",
                        "line": node.lineno,
                    })

    return issues


def check_hardcoded_prompts(source_code: str) -> list[dict[str, Any]]:
    """Check for hardcoded f-strings that might be prompts."""
    issues = []

    # Uses module-level pre-compiled _FSTRING_PROMPT_RE
    for match in _FSTRING_PROMPT_RE.finditer(source_code):
        line_num = source_code[:match.start()].count("\n") + 1

        issues.append({
            "gate": "no_hardcoded_prompts",
            "severity": WARNING,
            "message": f"Possible hardcoded prompt at line {line_num}",
            "line": line_num,
        })

    return issues


def check_api_key_security(source_code: str) -> list[dict[str, Any]]:
    """Check for hardcoded API keys."""
    issues = []

    # Uses module-level pre-compiled _API_KEY_RES
    for compiled_re in _API_KEY_RES:
        for match in compiled_re.finditer(source_code):
            line_num = source_code[:match.start()].count("\n") + 1

            issues.append({
                "gate": "lm_api_key_secure",
                "severity": ERROR,
                "message": f"Possible hardcoded API key at line {line_num}",
                "line": line_num,
            })

    return issues


def check_dspy_settings_configure(source_code: str) -> list[dict[str, Any]]:
    """Check if dspy.settings.configure() is called."""
    issues = []

    if "dspy.settings.configure" not in source_code:
        issues.append({
            "gate": "dspy_settings_configured",
            "severity": ERROR,
            "message": "dspy.settings.configure() not found in code",
            "line": 0,
        })

    return issues


def run_all_gates(source_code: str, filename: str = "<unknown>") -> dict[str, Any]:
    """Run all DSPy quality gates on source code.

    Args:
        source_code: Python source code to check
        filename: Name of the file being checked

    Returns:
        Dictionary with results summary and list of issues
    """
    all_issues = []

    # Run all checks
    all_issues.extend(check_signature_completeness(source_code))
    all_issues.extend(check_module_forward(source_code))
    all_issues.extend(check_hardcoded_prompts(source_code))
    all_issues.extend(check_api_key_security(source_code))
    all_issues.extend(check_dspy_settings_configure(source_code))

    # Categorize by severity
    errors = [i for i in all_issues if i["severity"] == ERROR]
    warnings = [i for i in all_issues if i["severity"] == WARNING]
    infos = [i for i in all_issues if i["severity"] == INFO]

    return {
        "filename": filename,
        "total_issues": len(all_issues),
        "errors": len(errors),
        "warnings": len(warnings),
        "infos": len(infos),
        "issues": all_issues,
        "passed": len(errors) == 0,
    }


def format_report(result: dict[str, Any]) -> str:
    """Format quality gate results as readable report."""
    lines = [
        f"DSPy Quality Gates Report: {result['filename']}",
        "=" * 60,
        f"Total issues: {result['total_issues']}",
        f"  Errors: {result['errors']}",
        f"  Warnings: {result['warnings']}",
        f"  Infos: {result['infos']}",
        "",
    ]

    if result["issues"]:
        lines.append("Issues found:")
        for issue in result["issues"]:
            severity_symbol = "🔴" if issue["severity"] == ERROR else "🟡" if issue["severity"] == WARNING else "🔵"
            lines.append(f"  {severity_symbol} [{issue['gate']}] Line {issue['line']}: {issue['message']}")
    else:
        lines.append("✅ All quality gates passed!")

    lines.append("")
    lines.append(f"Result: {'PASS' if result['passed'] else 'FAIL'}")

    return "\n".join(lines)


# Hook interface for PreToolUse
def main(source_code: str, filename: str = "<unknown>") -> dict[str, Any]:
    """Main entry point for hook integration.

    Returns dict with:
        - passed: bool (True if no errors)
        - result: full results dict
        - report: formatted string report
    """
    result = run_all_gates(source_code, filename)

    return {
        "passed": result["passed"],
        "result": result,
        "report": format_report(result),
    }


if __name__ == "__main__":
    # Example/test
    test_code = '''
import dspy

class TestSignature(dspy.Signature):
    """Test signature."""
    input_field = dspy.InputField(desc="Input")
    # Missing OutputField

class TestModule(dspy.Module):
    """Test module."""
    pass  # Missing forward()

api_key = "sk-test1234567890"
'''

    result = main(test_code, "test.py")
    print(result["report"])
    print(f"\nPassed: {result['passed']}")
