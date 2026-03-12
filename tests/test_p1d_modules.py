"""Verify P1D modules exist and are valid."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

KAZUBA_ROOT = Path(__file__).resolve().parent.parent

PRESETS_DIR = KAZUBA_ROOT / "claude_code_kazuba" / "data" / "presets"


def module_dir(name: str) -> Path:
    return KAZUBA_ROOT / "claude_code_kazuba" / "data" / "modules" / name


class TestAcoGeneratorsModule:
    def test_module_dir_exists(self) -> None:
        assert module_dir("aco-generators").exists()

    def test_module_md_exists(self) -> None:
        assert (module_dir("aco-generators") / "MODULE.md").exists()

    def test_library_py_exists(self) -> None:
        assert (module_dir("aco-generators") / "aco" / "generators" / "library.py").exists()

    def test_learning_py_exists(self) -> None:
        assert (module_dir("aco-generators") / "aco" / "generators" / "learning.py").exists()

    def test_starter_generators_exist(self) -> None:
        gen_dir = module_dir("aco-generators") / "aco" / "generators"
        for name in ("gen_rust_module.py", "gen_test_suite.py", "gen_api_endpoint.py"):
            assert (gen_dir / name).exists(), f"Missing starter: {name}"

    def test_starters_have_triad(self) -> None:
        gen_dir = module_dir("aco-generators") / "aco" / "generators"
        for name in ("gen_rust_module.py", "gen_test_suite.py", "gen_api_endpoint.py"):
            source = (gen_dir / name).read_text()
            for fn in ("execute_script", "validate_script", "rollback_script"):
                assert f"def {fn}" in source, f"{name} missing {fn}"

    def test_starters_compile(self) -> None:
        gen_dir = module_dir("aco-generators") / "aco" / "generators"
        for name in ("gen_rust_module.py", "gen_test_suite.py", "gen_api_endpoint.py"):
            source = (gen_dir / name).read_text()
            ast.parse(source, filename=name)


class TestAcoOrchestratorModule:
    def test_module_dir_exists(self) -> None:
        assert module_dir("aco-orchestrator").exists()

    def test_module_md_exists(self) -> None:
        assert (module_dir("aco-orchestrator") / "MODULE.md").exists()

    def test_deps_txt_exists(self) -> None:
        assert (module_dir("aco-orchestrator") / "deps.txt").exists()

    def test_deps_txt_content(self) -> None:
        deps = (module_dir("aco-orchestrator") / "deps.txt").read_text().strip().splitlines()
        assert "aco-esaa" in deps
        assert "aco-generators" in deps

    def test_orchestrator_py_exists(self) -> None:
        assert (module_dir("aco-orchestrator") / "aco" / "orchestrator.py").exists()

    def test_goal_tracker_py_exists(self) -> None:
        assert (module_dir("aco-orchestrator") / "aco" / "goal_tracker.py").exists()

    def test_rust_bridge_py_exists(self) -> None:
        assert (module_dir("aco-orchestrator") / "aco" / "rust_bridge.py").exists()


class TestAcoRustCoreModule:
    def test_module_dir_exists(self) -> None:
        assert module_dir("aco-rust-core").exists()

    def test_module_md_exists(self) -> None:
        assert (module_dir("aco-rust-core") / "MODULE.md").exists()

    def test_deps_txt_exists(self) -> None:
        assert (module_dir("aco-rust-core") / "deps.txt").exists()

    def test_cargo_toml_exists(self) -> None:
        assert (module_dir("aco-rust-core") / "rust-core" / "Cargo.toml").exists()

    def test_rust_aco_files_exist(self) -> None:
        src_aco = module_dir("aco-rust-core") / "rust-core" / "src" / "aco"
        for name in ("esaa.rs", "models.rs", "graph.rs", "tracker.rs", "mod.rs"):
            assert (src_aco / name).exists(), f"Missing Rust file: {name}"


class TestPresets:
    def test_lexcore_txt_exists(self) -> None:
        assert (PRESETS_DIR / "lexcore.txt").exists()

    def test_full_stack_txt_exists(self) -> None:
        assert (PRESETS_DIR / "full-stack.txt").exists()

    def test_lexcore_toml_exists(self) -> None:
        assert (PRESETS_DIR / "lexcore.toml").exists()

    def test_lexcore_toml_parses(self) -> None:
        config = tomllib.loads((PRESETS_DIR / "lexcore.toml").read_text())
        assert "meta" in config
        assert "cila_router" in config

    def test_lexcore_toml_has_domain_keywords(self) -> None:
        config = tomllib.loads((PRESETS_DIR / "lexcore.toml").read_text())
        domain_kw = config["cila_router"]["domain_keywords"]
        # TOML table keys are always strings, so "3" not 3
        assert "3" in domain_kw
        assert "lexcore" in domain_kw["3"]

    def test_lexcore_txt_has_aco_modules(self) -> None:
        modules = [
            line.strip()
            for line in (PRESETS_DIR / "lexcore.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        for m in ("aco-esaa", "aco-generators", "aco-orchestrator", "aco-rust-core"):
            assert m in modules, f"Missing in lexcore.txt: {m}"

    def test_full_stack_txt_has_aco_modules(self) -> None:
        modules = [
            line.strip()
            for line in (PRESETS_DIR / "full-stack.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        for m in ("aco-esaa", "aco-generators", "aco-orchestrator", "aco-rust-core"):
            assert m in modules, f"Missing in full-stack.txt: {m}"


class TestCliExtensions:
    def test_cli_has_lexcore_preset(self) -> None:
        cli_source = (KAZUBA_ROOT / "claude_code_kazuba" / "cli.py").read_text()
        assert "lexcore" in cli_source

    def test_cli_has_full_stack_preset(self) -> None:
        cli_source = (KAZUBA_ROOT / "claude_code_kazuba" / "cli.py").read_text()
        assert "full-stack" in cli_source

    def test_cli_has_build_rust_command(self) -> None:
        cli_source = (KAZUBA_ROOT / "claude_code_kazuba" / "cli.py").read_text()
        assert "build-rust" in cli_source
        assert "cmd_build_rust" in cli_source

    def test_cli_has_toml_sidecar_reading(self) -> None:
        cli_source = (KAZUBA_ROOT / "claude_code_kazuba" / "cli.py").read_text()
        assert "tomllib" in cli_source
        assert "cila_router_config" in cli_source


class TestInstallerExtensions:
    def test_installer_has_rust_core_content_dir(self) -> None:
        source = (KAZUBA_ROOT / "claude_code_kazuba" / "installer" / "install_module.py").read_text()
        assert "rust-core" in source

    def test_installer_has_cila_router_injection(self) -> None:
        source = (KAZUBA_ROOT / "claude_code_kazuba" / "installer" / "install_module.py").read_text()
        assert "cila_router_config" in source
        assert "DOMAIN_KEYWORDS" in source
