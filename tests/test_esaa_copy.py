"""Verify all 18 ESAA files exist and are valid Python."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODULE_ROOT = (
    Path(__file__).resolve().parent.parent / "claude_code_kazuba" / "data" / "modules" / "aco-esaa"
)

EXPECTED_FILES = [
    "event_store.py",
    "async_event_store.py",
    "event_buffer.py",
    "sqlite_backend.py",
    "hash_chain.py",
    "cognitive_event.py",
    "cqrs_agent_store.py",
    "cqrs_read_model.py",
    "generator_node_saga.py",
    "saga_orchestrator_v2.py",
    "rl_buffer.py",
    "cila_router.py",
    "ghost_projector.py",
    "time_travel.py",
    "query_cache.py",
    "agent_dataloader.py",
    "upcaster.py",
    "saga_orchestrator.py",
]


class TestEsaaFilesExist:
    """Verify all 18 ESAA files are present."""

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_file_exists(self, filename: str) -> None:
        path = MODULE_ROOT / filename
        assert path.exists(), f"Missing ESAA file: {filename}"

    def test_exactly_18_python_files(self) -> None:
        """Verify we have exactly 18 source files (excluding __init__.py)."""
        py_files = [f.name for f in MODULE_ROOT.glob("*.py") if f.name != "__init__.py"]
        assert len(py_files) == 18, f"Expected 18 ESAA files, found {len(py_files)}: {sorted(py_files)}"


class TestEsaaFilesCompile:
    """Verify each ESAA file is syntactically valid Python."""

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_compiles(self, filename: str) -> None:
        path = MODULE_ROOT / filename
        source = path.read_text()
        try:
            ast.parse(source, filename=filename)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {filename}: {e}")


class TestEsaaNoAnttLeakage:
    """Verify 'antt' keyword is not in code (only comments are acceptable)."""

    def test_no_antt_in_cila_router_code(self) -> None:
        path = MODULE_ROOT / "cila_router.py"
        source = path.read_text()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Strip inline comments before checking
            code_part = stripped.split("#")[0] if "#" in stripped else stripped
            assert "antt" not in code_part.lower(), f"'antt' found in code (not comment): {line!r}"
