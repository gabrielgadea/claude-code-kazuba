"""Verify intelligence-dspy module files exist, parse correctly, and are clean."""
from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = (
    Path(__file__).resolve().parent.parent
    / "claude_code_kazuba"
    / "data"
    / "modules"
    / "intelligence-dspy"
)

EXPECTED_SIGNATURES = [
    "cognitive_architectures.py",
    "perception.py",
]

EXPECTED_MODULES = [
    "perception_module.py",
    "tantivy_retriever.py",
    "serena_cache.py",
    "gitnexus_cache.py",
]

EXCLUDED_FILES = ["gate_bridge.py"]


class TestDspyModules:
    def test_module_root_exists(self):
        assert MODULE_ROOT.exists(), f"Module root not found: {MODULE_ROOT}"

    def test_expected_signature_files_exist(self):
        sig_dir = MODULE_ROOT / "signatures"
        for fname in EXPECTED_SIGNATURES:
            path = sig_dir / fname
            assert path.exists(), f"Missing signature file: {fname}"

    def test_expected_module_files_exist(self):
        mod_dir = MODULE_ROOT / "modules"
        for fname in EXPECTED_MODULES:
            path = mod_dir / fname
            assert path.exists(), f"Missing module file: {fname}"

    def test_gate_bridge_excluded(self):
        for fname in EXCLUDED_FILES:
            path = MODULE_ROOT / "modules" / fname
            assert not path.exists(), f"Excluded file present: {fname}"

    def test_all_files_parse_without_syntax_errors(self):
        errors = []
        for py_file in MODULE_ROOT.rglob("*.py"):
            content = py_file.read_text()
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"{py_file.name}: {e}")
        assert not errors, "Syntax errors found:\n" + "\n".join(errors)

    def test_no_pipeline_process_analysis_imports(self):
        """Ensure no ANTT-specific pipeline imports leaked in."""
        bad_imports = []
        for py_file in MODULE_ROOT.rglob("*.py"):
            content = py_file.read_text()
            if "scripts.process_analysis" in content:
                bad_imports.append(py_file.name)
        assert not bad_imports, (
            f"ANTT pipeline imports found in: {bad_imports}"
        )

    def test_module_md_exists(self):
        assert (MODULE_ROOT / "MODULE.md").exists()

    def test_settings_hooks_json_exists(self):
        assert (MODULE_ROOT / "settings.hooks.json").exists()

    def test_init_files_exist(self):
        assert (MODULE_ROOT / "signatures" / "__init__.py").exists()
        assert (MODULE_ROOT / "modules" / "__init__.py").exists()

    def test_perception_module_not_antt_specific(self):
        pmod = MODULE_ROOT / "modules" / "perception_module.py"
        if pmod.exists():
            content = pmod.read_text()
            assert "for ANTT regulatory analysis" not in content, (
                "ANTT-specific docstring not cleaned from perception_module.py"
            )
