"""Verify GeneratorNode bridge module structure."""
from __future__ import annotations

import ast
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "claude_code_kazuba"
    / "data"
    / "modules"
    / "aco-esaa"
    / "generator_node_saga.py"
)


class TestGeneratorNodeSagaStructure:
    """Verify the bridge module structure."""

    def test_file_exists(self) -> None:
        assert MODULE_PATH.exists()

    def test_compiles(self) -> None:
        source = MODULE_PATH.read_text()
        ast.parse(source, filename="generator_node_saga.py")

    def test_has_saga_step_reference(self) -> None:
        source = MODULE_PATH.read_text()
        assert "SagaStep" in source

    def test_has_generator_node_reference(self) -> None:
        source = MODULE_PATH.read_text()
        assert "GeneratorNode" in source

    def test_has_conversion_functions(self) -> None:
        source = MODULE_PATH.read_text()
        tree = ast.parse(source)
        func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        assert len(func_names) >= 2, f"Expected >= 2 functions, found: {func_names}"

    def test_scripts_aco_models_import_has_fallback(self) -> None:
        """The scripts.aco.models.core import must have try/except fallback."""
        source = MODULE_PATH.read_text()
        assert "ImportError" in source, (
            "generator_node_saga.py must have ImportError fallback for scripts.aco.models.core"
        )
