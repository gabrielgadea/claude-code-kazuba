"""Verify cila_router.py parametric keyword configuration."""
from __future__ import annotations

import ast
from pathlib import Path

MODULE_DIR = (
    Path(__file__).resolve().parent.parent / "claude_code_kazuba" / "data" / "modules" / "aco-esaa"
)
CILA_ROUTER_PATH = MODULE_DIR / "cila_router.py"


def _read_and_parse_cila_router() -> ast.Module:
    """Parse cila_router.py without executing it (safe for internal imports)."""
    return ast.parse(CILA_ROUTER_PATH.read_text(), filename="cila_router.py")


def _strip_inline_comment(line: str) -> str:
    """Return the code portion of a line, stripping any inline # comment."""
    return line.split("#")[0] if "#" in line else line


class TestDefaultCilaKeywordsAst:
    """Verify DEFAULT_CILA_KEYWORDS structure via AST (no execution needed)."""

    def test_default_keywords_exists_as_assignment(self) -> None:
        tree = _read_and_parse_cila_router()
        # Check both ast.Assign and ast.AnnAssign (annotated assignment)
        names: list[str] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                names.append(node.targets[0].id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.append(node.target.id)
        assert "DEFAULT_CILA_KEYWORDS" in names

    def test_all_levels_0_through_6_present(self) -> None:
        """DEFAULT_CILA_KEYWORDS must have keys 0-6."""
        source = CILA_ROUTER_PATH.read_text()
        for level in range(7):
            assert f"{level}:" in source or f"{level} :" in source, (
                f"Level {level} not found in DEFAULT_CILA_KEYWORDS"
            )

    def test_antt_keyword_not_in_code(self) -> None:
        """'antt' must not appear as a string literal in non-comment code."""
        source = CILA_ROUTER_PATH.read_text()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_part = _strip_inline_comment(stripped)
            assert '"antt"' not in code_part and "'antt'" not in code_part, (
                f"'antt' found as string literal in code: {line!r}"
            )

    def test_l4_keywords_present(self) -> None:
        """L4 must have 'agent', 'loop', 'cycle'."""
        source = CILA_ROUTER_PATH.read_text()
        assert '"agent"' in source or "'agent'" in source
        assert '"loop"' in source or "'loop'" in source
        assert '"cycle"' in source or "'cycle'" in source

    def test_l3_has_pipeline_and_process(self) -> None:
        """L3 must retain 'pipeline' and 'process'."""
        source = CILA_ROUTER_PATH.read_text()
        assert '"pipeline"' in source or "'pipeline'" in source
        assert '"process"' in source or "'process'" in source

    def test_build_cila_router_function_exists(self) -> None:
        """build_cila_router must be defined as a function."""
        tree = _read_and_parse_cila_router()
        func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        assert "build_cila_router" in func_names

    def test_cila_router_config_class_exists(self) -> None:
        """_CILARouterConfig must be defined."""
        tree = _read_and_parse_cila_router()
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "_CILARouterConfig" in class_names

    def test_classify_prompt_method_in_config(self) -> None:
        """_CILARouterConfig must have classify_prompt method."""
        source = CILA_ROUTER_PATH.read_text()
        assert "def classify_prompt" in source

    def test_antt_pipeline_check_removed_from_techniques(self) -> None:
        """antt_pipeline_check must not appear in _LEVEL_TECHNIQUE."""
        source = CILA_ROUTER_PATH.read_text()
        assert "antt_pipeline_check" not in source

    def test_pipeline_check_in_techniques(self) -> None:
        """pipeline_check (without antt prefix) must be in _LEVEL_TECHNIQUE."""
        source = CILA_ROUTER_PATH.read_text()
        assert "pipeline_check" in source
