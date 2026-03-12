"""Verify ANTTTaskType -> TaskType rename is complete and functional."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_ROOT = (
    Path(__file__).resolve().parent.parent
    / "claude_code_kazuba"
    / "data"
    / "modules"
    / "intelligence-rl"
)


def _load_models():
    models_path = MODULE_ROOT / "core" / "models.py"
    assert models_path.exists(), f"models.py not found at {models_path}"
    spec = importlib.util.spec_from_file_location("rl_models", models_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestTaskTypeRename:
    def test_antt_task_type_not_present_in_source(self):
        for py_file in MODULE_ROOT.rglob("*.py"):
            content = py_file.read_text()
            assert "ANTTTaskType" not in content, (
                f"ANTTTaskType still present in {py_file.relative_to(MODULE_ROOT)}"
            )

    def test_task_type_enum_exists(self):
        try:
            mod = _load_models()
            assert hasattr(mod, "TaskType"), "TaskType not found in models"
            assert not hasattr(mod, "ANTTTaskType"), "ANTTTaskType should not exist"
        except ImportError as e:
            pytest.skip(f"Import error (external deps missing): {e}")

    def test_task_type_has_expected_values(self):
        try:
            mod = _load_models()
            task_type = mod.TaskType
            assert "complete_analysis" in [v.value for v in task_type]
            assert "preliminary" in [v.value for v in task_type]
            assert "unknown" in [v.value for v in task_type]
        except ImportError as e:
            pytest.skip(f"Import error (external deps missing): {e}")

    def test_no_antt_task_type_in_td_learning(self):
        td_path = MODULE_ROOT / "rl" / "td_learning.py"
        if td_path.exists():
            content = td_path.read_text()
            assert "ANTTTaskType" not in content

    def test_no_antt_task_type_in_state(self):
        state_path = MODULE_ROOT / "rl" / "state.py"
        if state_path.exists():
            content = state_path.read_text()
            assert "ANTTTaskType" not in content

    def test_module_structure_exists(self):
        assert (MODULE_ROOT / "core" / "models.py").exists()
        assert (MODULE_ROOT / "rl" / "td_learning.py").exists()
        assert (MODULE_ROOT / "rl" / "reward.py").exists()
        assert (MODULE_ROOT / "rl" / "action.py").exists()
        assert (MODULE_ROOT / "rl" / "policy.py").exists()
        assert (MODULE_ROOT / "rl" / "state.py").exists()
        assert (MODULE_ROOT / "memory" / "working.py").exists()
        assert (MODULE_ROOT / "memory" / "short_term.py").exists()
        assert (MODULE_ROOT / "MODULE.md").exists()
        assert (MODULE_ROOT / "settings.hooks.json").exists()
