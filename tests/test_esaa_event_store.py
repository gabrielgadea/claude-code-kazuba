"""Verify EventStore basic structure."""
from __future__ import annotations

import ast
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "claude_code_kazuba" / "data" / "modules" / "aco-esaa" / "event_store.py"
)


class TestEventStoreStructure:
    """Verify event_store.py has expected structure."""

    def test_file_exists(self) -> None:
        assert MODULE_PATH.exists()

    def test_compiles(self) -> None:
        source = MODULE_PATH.read_text()
        ast.parse(source, filename="event_store.py")

    def test_has_event_store_class(self) -> None:
        """EventStore class must be defined."""
        source = MODULE_PATH.read_text()
        tree = ast.parse(source)
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "EventStore" in class_names, f"EventStore class not found. Classes: {class_names}"

    def test_has_append_method(self) -> None:
        source = MODULE_PATH.read_text()
        assert "def append" in source

    def test_has_get_stream_method(self) -> None:
        source = MODULE_PATH.read_text()
        assert "def get_stream" in source

    def test_has_replay_capability(self) -> None:
        source = MODULE_PATH.read_text()
        assert "replay" in source.lower()
