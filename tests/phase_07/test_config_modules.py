"""Phase 7 Tests: Comprehensive validation of config, contexts, and team-orchestrator.

Tests cover:
- config-hypervisor: all 3 YAML files exist and parse correctly
- contexts: all 4 context files exist with frontmatter
- team-orchestrator: config files, templates, and Pydantic models
- MODULE.md files are present for all Phase 7 modules
- YAML files parse without errors via yaml.safe_load
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def modules_dir(project_root: Path) -> Path:
    return project_root / "modules"


def _extract_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


# ---------------------------------------------------------------------------
# Config-Hypervisor Tests
# ---------------------------------------------------------------------------

HYPERVISOR_YAMLS = [
    "hypervisor.yaml",
    "agent_triggers.yaml",
    "event_mesh.yaml",
]


class TestConfigHypervisor:
    """Validate config-hypervisor has all 3 YAML files and they parse correctly."""

    @pytest.mark.parametrize("filename", HYPERVISOR_YAMLS)
    def test_yaml_file_exists(self, modules_dir: Path, filename: str) -> None:
        path = modules_dir / "config-hypervisor" / "config" / filename
        assert path.is_file(), f"config-hypervisor/config/{filename} missing"

    @pytest.mark.parametrize("filename", HYPERVISOR_YAMLS)
    def test_yaml_parses_without_error(self, modules_dir: Path, filename: str) -> None:
        path = modules_dir / "config-hypervisor" / "config" / filename
        content = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"{filename} is not valid YAML: {e}")
        assert data is not None, f"{filename} parsed as empty"
        assert isinstance(data, dict), f"{filename} root should be a mapping"

    @pytest.mark.parametrize("filename", HYPERVISOR_YAMLS)
    def test_yaml_minimum_lines(self, modules_dir: Path, filename: str) -> None:
        path = modules_dir / "config-hypervisor" / "config" / filename
        lines = _line_count(path)
        assert lines >= 50, f"{filename} has {lines} lines, expected >= 50"

    def test_hypervisor_has_required_sections(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "hypervisor.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for section in ("context_management", "thinking", "circuit_breakers", "quality", "sla"):
            assert section in data, f"hypervisor.yaml missing section '{section}'"

    def test_agent_triggers_has_triggers_list(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "agent_triggers.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "triggers" in data, "agent_triggers.yaml missing 'triggers' key"
        assert isinstance(data["triggers"], list)
        assert len(data["triggers"]) >= 5

    def test_event_mesh_has_categories(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "event_mesh.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "categories" in data, "event_mesh.yaml missing 'categories' key"
        assert len(data["categories"]) >= 7


# ---------------------------------------------------------------------------
# Contexts Module Tests
# ---------------------------------------------------------------------------

CONTEXT_FILES = ["dev", "review", "research", "audit"]


class TestContextsModule:
    """Validate all context markdown files exist with frontmatter."""

    def test_module_md_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "contexts" / "MODULE.md"
        assert path.is_file(), "contexts/MODULE.md missing"

    def test_module_md_has_frontmatter(self, modules_dir: Path) -> None:
        path = modules_dir / "contexts" / "MODULE.md"
        fm = _extract_frontmatter(path)
        assert fm is not None
        assert fm.get("name") == "contexts"

    @pytest.mark.parametrize("ctx", CONTEXT_FILES)
    def test_context_file_exists(self, modules_dir: Path, ctx: str) -> None:
        path = modules_dir / "contexts" / "contexts" / f"{ctx}.md"
        assert path.is_file(), f"contexts/contexts/{ctx}.md missing"

    @pytest.mark.parametrize("ctx", CONTEXT_FILES)
    def test_context_has_frontmatter(self, modules_dir: Path, ctx: str) -> None:
        path = modules_dir / "contexts" / "contexts" / f"{ctx}.md"
        fm = _extract_frontmatter(path)
        assert fm is not None, f"{ctx}.md missing YAML frontmatter"
        assert "name" in fm, f"{ctx}.md frontmatter missing 'name'"

    @pytest.mark.parametrize("ctx", CONTEXT_FILES)
    def test_context_minimum_lines(self, modules_dir: Path, ctx: str) -> None:
        path = modules_dir / "contexts" / "contexts" / f"{ctx}.md"
        lines = _line_count(path)
        assert lines >= 30, f"{ctx}.md has {lines} lines, expected >= 30"


# ---------------------------------------------------------------------------
# Team-Orchestrator Tests
# ---------------------------------------------------------------------------

ORCHESTRATOR_CONFIGS = ["agents.yaml", "routing_rules.yaml", "sla.yaml"]
ORCHESTRATOR_TEMPLATES = ["task-delegation.md", "status-report.md"]


class TestTeamOrchestrator:
    """Validate team-orchestrator config, templates, and models."""

    def test_module_md_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "MODULE.md"
        assert path.is_file()

    def test_module_md_has_frontmatter(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "MODULE.md"
        fm = _extract_frontmatter(path)
        assert fm is not None
        assert fm.get("name") == "team-orchestrator"

    @pytest.mark.parametrize("filename", ORCHESTRATOR_CONFIGS)
    def test_config_yaml_exists(self, modules_dir: Path, filename: str) -> None:
        path = modules_dir / "team-orchestrator" / "config" / filename
        assert path.is_file(), f"team-orchestrator/config/{filename} missing"

    @pytest.mark.parametrize("filename", ORCHESTRATOR_CONFIGS)
    def test_config_yaml_parses(self, modules_dir: Path, filename: str) -> None:
        path = modules_dir / "team-orchestrator" / "config" / filename
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            pytest.fail(f"{filename} is not valid YAML: {e}")
        assert data is not None, f"{filename} parsed as empty"

    @pytest.mark.parametrize("tmpl", ORCHESTRATOR_TEMPLATES)
    def test_template_exists(self, modules_dir: Path, tmpl: str) -> None:
        path = modules_dir / "team-orchestrator" / "templates" / tmpl
        assert path.is_file(), f"team-orchestrator/templates/{tmpl} missing"

    @pytest.mark.parametrize("tmpl", ORCHESTRATOR_TEMPLATES)
    def test_template_minimum_lines(self, modules_dir: Path, tmpl: str) -> None:
        path = modules_dir / "team-orchestrator" / "templates" / tmpl
        lines = _line_count(path)
        assert lines >= 20, f"{tmpl} has {lines} lines, expected >= 20"

    def test_models_py_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "src" / "models.py"
        assert path.is_file(), "team-orchestrator/src/models.py missing"

    def test_models_py_minimum_lines(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "src" / "models.py"
        lines = _line_count(path)
        assert lines >= 150, f"models.py has {lines} lines, expected >= 150"

    def test_models_py_has_future_annotations(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "src" / "models.py"
        content = path.read_text(encoding="utf-8")
        assert "from __future__ import annotations" in content


# ---------------------------------------------------------------------------
# Phase 7 MODULE.md Presence Tests
# ---------------------------------------------------------------------------

PHASE7_MODULES = ["config-hypervisor", "contexts", "team-orchestrator"]


class TestPhase7ModuleMdPresence:
    """Ensure all Phase 7 modules have MODULE.md with frontmatter."""

    @pytest.mark.parametrize("module_name", PHASE7_MODULES)
    def test_module_md_present(self, modules_dir: Path, module_name: str) -> None:
        path = modules_dir / module_name / "MODULE.md"
        assert path.is_file(), f"{module_name}/MODULE.md missing"

    @pytest.mark.parametrize("module_name", PHASE7_MODULES)
    def test_module_md_has_name_and_description(self, modules_dir: Path, module_name: str) -> None:
        path = modules_dir / module_name / "MODULE.md"
        fm = _extract_frontmatter(path)
        assert fm is not None, f"{module_name}/MODULE.md has no frontmatter"
        assert "name" in fm
        assert "description" in fm
