"""Phase 7 Tests: Validate YAML configs, context files, and team-orchestrator."""

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


class TestYamlValidity:
    """Validate all .yaml files are valid YAML."""

    def _find_yaml_files(self, modules_dir: Path) -> list[Path]:
        return sorted(modules_dir.rglob("*.yaml")) + sorted(modules_dir.rglob("*.yml"))

    def test_yaml_files_exist(self, modules_dir: Path) -> None:
        yamls = self._find_yaml_files(modules_dir)
        assert len(yamls) >= 5, f"Expected >= 5 YAML files, found {len(yamls)}"

    def test_all_yaml_files_are_valid(self, modules_dir: Path) -> None:
        yamls = self._find_yaml_files(modules_dir)
        for yaml_path in yamls:
            content = yaml_path.read_text(encoding="utf-8")
            try:
                data = yaml.safe_load(content)
                assert data is not None, f"{yaml_path} parsed as empty/null"
            except yaml.YAMLError as e:
                pytest.fail(f"{yaml_path} is not valid YAML: {e}")


class TestHypervisorConfig:
    """Validate hypervisor.yaml has required sections."""

    REQUIRED_SECTIONS = [
        "context_management",
        "thinking",
        "circuit_breakers",
        "quality",
        "sla",
    ]

    def test_hypervisor_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "hypervisor.yaml"
        assert path.is_file(), "hypervisor.yaml missing"

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_hypervisor_has_section(self, modules_dir: Path, section: str) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "hypervisor.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert section in data, f"hypervisor.yaml missing section '{section}'"

    def test_thinking_has_levels(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "hypervisor.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        levels = data["thinking"]["levels"]
        assert len(levels) == 4, f"Expected 4 thinking levels, got {len(levels)}"
        level_names = {lvl["name"] for lvl in levels}
        assert level_names == {"low", "medium", "high", "critical"}

    def test_circuit_breakers_have_thresholds(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "hypervisor.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        breakers = data["circuit_breakers"]
        assert len(breakers) >= 5, f"Expected >= 5 circuit breakers, got {len(breakers)}"


class TestAgentTriggers:
    """Validate agent_triggers.yaml has sufficient triggers."""

    def test_triggers_file_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "agent_triggers.yaml"
        assert path.is_file(), "agent_triggers.yaml missing"

    def test_has_at_least_5_triggers(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "agent_triggers.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        triggers = data.get("triggers", [])
        assert len(triggers) >= 5, f"Expected >= 5 triggers, got {len(triggers)}"

    def test_triggers_have_required_fields(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "agent_triggers.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        required_fields = {"name", "condition", "agent_type", "priority"}
        for trigger in data["triggers"]:
            missing = required_fields - set(trigger.keys())
            assert not missing, f"Trigger '{trigger.get('name', '?')}' missing fields: {missing}"


class TestEventMesh:
    """Validate event_mesh.yaml structure."""

    def test_event_mesh_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "event_mesh.yaml"
        assert path.is_file(), "event_mesh.yaml missing"

    def test_has_categories(self, modules_dir: Path) -> None:
        path = modules_dir / "config-hypervisor" / "config" / "event_mesh.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "categories" in data, "event_mesh.yaml missing 'categories'"
        assert len(data["categories"]) >= 7, (
            f"Expected >= 7 categories, got {len(data['categories'])}"
        )


class TestContextFiles:
    """Validate all context .md files are not empty."""

    EXPECTED_CONTEXTS = ["dev", "review", "research", "audit"]

    @pytest.mark.parametrize("ctx_name", EXPECTED_CONTEXTS)
    def test_context_exists_and_not_empty(self, modules_dir: Path, ctx_name: str) -> None:
        path = modules_dir / "contexts" / "contexts" / f"{ctx_name}.md"
        assert path.is_file(), f"Context file {ctx_name}.md missing"
        content = path.read_text(encoding="utf-8")
        assert len(content.strip()) > 100, (
            f"Context {ctx_name}.md is too short ({len(content.strip())} chars)"
        )

    @pytest.mark.parametrize("ctx_name", EXPECTED_CONTEXTS)
    def test_context_has_frontmatter(self, modules_dir: Path, ctx_name: str) -> None:
        path = modules_dir / "contexts" / "contexts" / f"{ctx_name}.md"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---"), f"Context {ctx_name}.md missing frontmatter"
        parts = text.split("---", 2)
        assert len(parts) >= 3, f"Context {ctx_name}.md frontmatter not properly delimited"
        fm = yaml.safe_load(parts[1])
        assert fm is not None, f"Context {ctx_name}.md frontmatter is empty"
        assert "name" in fm, f"Context {ctx_name}.md frontmatter missing 'name'"


class TestTeamOrchestrator:
    """Validate team-orchestrator config and templates."""

    def test_agents_yaml_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "config" / "agents.yaml"
        assert path.is_file(), "team-orchestrator agents.yaml missing"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "agents" in data
        assert len(data["agents"]) >= 3

    def test_routing_rules_yaml_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "config" / "routing_rules.yaml"
        assert path.is_file(), "team-orchestrator routing_rules.yaml missing"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "rules" in data
        assert len(data["rules"]) >= 7

    def test_sla_yaml_exists(self, modules_dir: Path) -> None:
        path = modules_dir / "team-orchestrator" / "config" / "sla.yaml"
        assert path.is_file(), "team-orchestrator sla.yaml missing"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "latency_targets" in data
        assert "rate_limits" in data

    def test_templates_exist(self, modules_dir: Path) -> None:
        templates_dir = modules_dir / "team-orchestrator" / "templates"
        assert (templates_dir / "task-delegation.md").is_file()
        assert (templates_dir / "status-report.md").is_file()

    def test_templates_not_empty(self, modules_dir: Path) -> None:
        templates_dir = modules_dir / "team-orchestrator" / "templates"
        for tmpl in ["task-delegation.md", "status-report.md"]:
            content = (templates_dir / tmpl).read_text(encoding="utf-8")
            assert len(content.strip()) > 100, f"Template {tmpl} is too short"


class TestSharedPatterns:
    """Validate shared YAML patterns in commands-prp."""

    SHARED_FILES = [
        "quality-patterns.yml",
        "security-patterns.yml",
        "universal-constants.yml",
    ]

    @pytest.mark.parametrize("filename", SHARED_FILES)
    def test_shared_file_is_valid_yaml(self, modules_dir: Path, filename: str) -> None:
        path = modules_dir / "commands-prp" / "commands" / "shared" / filename
        assert path.is_file(), f"Shared file {filename} missing"
        content = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(content)
            assert data is not None, f"{filename} parsed as empty/null"
        except yaml.YAMLError as e:
            pytest.fail(f"{filename} is not valid YAML: {e}")
