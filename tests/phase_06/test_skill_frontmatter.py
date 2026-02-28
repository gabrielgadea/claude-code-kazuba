"""Phase 6 Tests: Validate SKILL.md frontmatter, agent frontmatter, and MODULE.md files."""

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
    """Extract YAML frontmatter from a markdown file (--- delimited)."""
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


class TestSkillFrontmatter:
    """Validate all SKILL.md files have valid YAML frontmatter with required fields."""

    def _find_skill_files(self, modules_dir: Path) -> list[Path]:
        return sorted(modules_dir.rglob("SKILL.md"))

    def test_skill_files_exist(self, modules_dir: Path) -> None:
        skills = self._find_skill_files(modules_dir)
        assert len(skills) >= 10, f"Expected >= 10 SKILL.md files, found {len(skills)}"

    @pytest.mark.parametrize(
        "skill_name",
        [
            "hook-master",
            "skill-master",
            "skill-writer",
            "verification-loop",
            "supreme-problem-solver",
            "eval-harness",
            "plan-amplifier",
            "plan-execution",
            "code-first-planner",
            "academic-research-writer",
            "literature-review",
        ],
    )
    def test_skill_has_valid_frontmatter(self, modules_dir: Path, skill_name: str) -> None:
        matches = list(modules_dir.rglob(f"{skill_name}/SKILL.md"))
        assert len(matches) == 1, (
            f"Expected exactly 1 SKILL.md for {skill_name}, found {len(matches)}"
        )

        fm = _extract_frontmatter(matches[0])
        assert fm is not None, f"{skill_name}/SKILL.md has no valid YAML frontmatter"
        assert "name" in fm, f"{skill_name}/SKILL.md frontmatter missing 'name'"
        assert "description" in fm, f"{skill_name}/SKILL.md frontmatter missing 'description'"
        assert fm["name"] == skill_name, (
            f"{skill_name}/SKILL.md name mismatch: expected '{skill_name}', got '{fm['name']}'"
        )

    def test_all_skills_have_frontmatter(self, modules_dir: Path) -> None:
        skills = self._find_skill_files(modules_dir)
        for skill_path in skills:
            fm = _extract_frontmatter(skill_path)
            assert fm is not None, f"{skill_path} has no valid YAML frontmatter"
            assert "name" in fm, f"{skill_path} frontmatter missing 'name'"
            assert "description" in fm, f"{skill_path} frontmatter missing 'description'"


class TestAgentFrontmatter:
    """Validate all agent .md files have valid YAML frontmatter."""

    def _find_agent_files(self, modules_dir: Path) -> list[Path]:
        agents_dirs = list(modules_dir.rglob("agents/"))
        agent_files: list[Path] = []
        for agents_dir in agents_dirs:
            if agents_dir.is_dir():
                agent_files.extend(sorted(agents_dir.glob("*.md")))
        return agent_files

    def test_agent_files_exist(self, modules_dir: Path) -> None:
        agents = self._find_agent_files(modules_dir)
        assert len(agents) >= 3, f"Expected >= 3 agent files, found {len(agents)}"

    @pytest.mark.parametrize(
        "agent_name",
        ["code-reviewer", "security-auditor", "meta-orchestrator"],
    )
    def test_agent_has_valid_frontmatter(self, modules_dir: Path, agent_name: str) -> None:
        matches = list(modules_dir.rglob(f"agents/{agent_name}.md"))
        assert len(matches) == 1, f"Expected exactly 1 {agent_name}.md, found {len(matches)}"

        fm = _extract_frontmatter(matches[0])
        assert fm is not None, f"{agent_name}.md has no valid YAML frontmatter"
        assert "name" in fm, f"{agent_name}.md frontmatter missing 'name'"
        assert "description" in fm, f"{agent_name}.md frontmatter missing 'description'"
        assert "tools" in fm, f"{agent_name}.md frontmatter missing 'tools'"
        assert isinstance(fm["tools"], list), f"{agent_name}.md 'tools' must be a list"
        assert len(fm["tools"]) >= 1, f"{agent_name}.md must have at least 1 tool"

    def test_all_agents_have_frontmatter(self, modules_dir: Path) -> None:
        agents = self._find_agent_files(modules_dir)
        for agent_path in agents:
            fm = _extract_frontmatter(agent_path)
            assert fm is not None, f"{agent_path} has no valid YAML frontmatter"
            assert "name" in fm, f"{agent_path} frontmatter missing 'name'"
            assert "description" in fm, f"{agent_path} frontmatter missing 'description'"
            assert "tools" in fm, f"{agent_path} frontmatter missing 'tools'"


class TestModuleManifests:
    """Validate all MODULE.md files exist and are not empty."""

    REQUIRED_MODULES = [
        "skills-meta",
        "skills-dev",
        "skills-planning",
        "skills-research",
        "agents-dev",
        "commands-dev",
        "commands-prp",
        "config-hypervisor",
        "contexts",
        "team-orchestrator",
    ]

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_module_md_exists_and_not_empty(self, modules_dir: Path, module_name: str) -> None:
        module_md = modules_dir / module_name / "MODULE.md"
        assert module_md.is_file(), f"MODULE.md missing for module {module_name}"
        content = module_md.read_text(encoding="utf-8")
        assert len(content.strip()) > 50, (
            f"MODULE.md for {module_name} is too short ({len(content.strip())} chars)"
        )

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_module_md_has_frontmatter(self, modules_dir: Path, module_name: str) -> None:
        module_md = modules_dir / module_name / "MODULE.md"
        fm = _extract_frontmatter(module_md)
        assert fm is not None, f"MODULE.md for {module_name} has no valid YAML frontmatter"
        assert "name" in fm, f"MODULE.md for {module_name} missing 'name'"
        assert "description" in fm, f"MODULE.md for {module_name} missing 'description'"


class TestCommandFiles:
    """Validate all command .md files have valid frontmatter."""

    EXPECTED_COMMANDS = [
        "debug-RCA",
        "smart-commit",
        "orchestrate",
        "verify",
        "prp-base-create",
        "prp-base-execute",
    ]

    @pytest.mark.parametrize("command_name", EXPECTED_COMMANDS)
    def test_command_has_valid_frontmatter(self, modules_dir: Path, command_name: str) -> None:
        matches = list(modules_dir.rglob(f"commands/{command_name}.md"))
        assert len(matches) == 1, f"Expected exactly 1 {command_name}.md, found {len(matches)}"

        fm = _extract_frontmatter(matches[0])
        assert fm is not None, f"{command_name}.md has no valid YAML frontmatter"
        assert "name" in fm, f"{command_name}.md frontmatter missing 'name'"
        assert "description" in fm, f"{command_name}.md frontmatter missing 'description'"
