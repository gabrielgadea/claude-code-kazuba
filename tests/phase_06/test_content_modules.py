"""Phase 6 Tests: Comprehensive validation of all content module files.

Tests cover:
- MODULE.md existence and YAML frontmatter for every module
- SKILL.md existence, frontmatter, and minimum line counts
- Agent definition file existence and structure
- Command definition file existence and structure
- Minimum content length enforcement (no stubs)
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


def _line_count(path: Path) -> int:
    """Return the number of lines in a file."""
    return len(path.read_text(encoding="utf-8").splitlines())


# ---------------------------------------------------------------------------
# MODULE.md Tests
# ---------------------------------------------------------------------------

ALL_MODULES = [
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


class TestModuleMdFiles:
    """Validate MODULE.md exists in every module with proper frontmatter."""

    @pytest.mark.parametrize("module_name", ALL_MODULES)
    def test_module_md_exists(self, modules_dir: Path, module_name: str) -> None:
        module_md = modules_dir / module_name / "MODULE.md"
        assert module_md.is_file(), f"MODULE.md missing for module {module_name}"

    @pytest.mark.parametrize("module_name", ALL_MODULES)
    def test_module_md_has_yaml_frontmatter(self, modules_dir: Path, module_name: str) -> None:
        module_md = modules_dir / module_name / "MODULE.md"
        fm = _extract_frontmatter(module_md)
        assert fm is not None, f"MODULE.md for {module_name} has no YAML frontmatter"

    @pytest.mark.parametrize("module_name", ALL_MODULES)
    def test_module_md_frontmatter_has_required_fields(
        self, modules_dir: Path, module_name: str
    ) -> None:
        module_md = modules_dir / module_name / "MODULE.md"
        fm = _extract_frontmatter(module_md)
        assert fm is not None
        for field in ("name", "description", "version"):
            assert field in fm, f"MODULE.md for {module_name} missing required field '{field}'"
        assert fm["name"] == module_name, (
            f"MODULE.md name mismatch: expected '{module_name}', got '{fm['name']}'"
        )

    @pytest.mark.parametrize("module_name", ALL_MODULES)
    def test_module_md_minimum_lines(self, modules_dir: Path, module_name: str) -> None:
        module_md = modules_dir / module_name / "MODULE.md"
        lines = _line_count(module_md)
        assert lines >= 20, f"MODULE.md for {module_name} has {lines} lines, expected >= 20"


# ---------------------------------------------------------------------------
# SKILL.md Tests
# ---------------------------------------------------------------------------

ALL_SKILLS = [
    ("skills-meta", "hook-master", 200),
    ("skills-meta", "skill-master", 200),
    ("skills-meta", "skill-writer", 80),
    ("skills-dev", "verification-loop", 100),
    ("skills-dev", "supreme-problem-solver", 100),
    ("skills-dev", "eval-harness", 80),
    ("skills-planning", "plan-amplifier", 150),
    ("skills-planning", "plan-execution", 120),
    ("skills-planning", "code-first-planner", 100),
    ("skills-research", "academic-research-writer", 100),
    ("skills-research", "literature-review", 80),
]


class TestSkillFiles:
    """Validate all SKILL.md files exist with proper content."""

    @pytest.mark.parametrize(
        "module,skill,_min_lines",
        ALL_SKILLS,
        ids=[s[1] for s in ALL_SKILLS],
    )
    def test_skill_file_exists(
        self, modules_dir: Path, module: str, skill: str, _min_lines: int
    ) -> None:
        path = modules_dir / module / "skills" / skill / "SKILL.md"
        assert path.is_file(), f"SKILL.md missing: {module}/skills/{skill}/SKILL.md"

    @pytest.mark.parametrize(
        "module,skill,_min_lines",
        ALL_SKILLS,
        ids=[s[1] for s in ALL_SKILLS],
    )
    def test_skill_has_yaml_frontmatter(
        self, modules_dir: Path, module: str, skill: str, _min_lines: int
    ) -> None:
        path = modules_dir / module / "skills" / skill / "SKILL.md"
        fm = _extract_frontmatter(path)
        assert fm is not None, f"{skill}/SKILL.md has no YAML frontmatter"
        assert "name" in fm, f"{skill}/SKILL.md frontmatter missing 'name'"
        assert "description" in fm, f"{skill}/SKILL.md frontmatter missing 'description'"
        assert fm["name"] == skill, (
            f"{skill}/SKILL.md name mismatch: expected '{skill}', got '{fm['name']}'"
        )

    @pytest.mark.parametrize(
        "module,skill,min_lines",
        ALL_SKILLS,
        ids=[s[1] for s in ALL_SKILLS],
    )
    def test_skill_minimum_lines(
        self, modules_dir: Path, module: str, skill: str, min_lines: int
    ) -> None:
        path = modules_dir / module / "skills" / skill / "SKILL.md"
        lines = _line_count(path)
        assert lines >= min_lines, f"{skill}/SKILL.md has {lines} lines, expected >= {min_lines}"

    def test_total_skill_count(self, modules_dir: Path) -> None:
        """Ensure we have at least 10 distinct skills across all modules."""
        skills = sorted(modules_dir.rglob("SKILL.md"))
        assert len(skills) >= 10, f"Expected >= 10 SKILL.md files, found {len(skills)}"


# ---------------------------------------------------------------------------
# Agent Definition Tests
# ---------------------------------------------------------------------------

ALL_AGENTS = [
    ("agents-dev", "code-reviewer", 60),
    ("agents-dev", "security-auditor", 60),
    ("agents-dev", "meta-orchestrator", 80),
]


class TestAgentFiles:
    """Validate all agent definition files exist with proper structure."""

    @pytest.mark.parametrize(
        "module,agent,_min_lines",
        ALL_AGENTS,
        ids=[a[1] for a in ALL_AGENTS],
    )
    def test_agent_file_exists(
        self, modules_dir: Path, module: str, agent: str, _min_lines: int
    ) -> None:
        path = modules_dir / module / "agents" / f"{agent}.md"
        assert path.is_file(), f"Agent file missing: {module}/agents/{agent}.md"

    @pytest.mark.parametrize(
        "module,agent,_min_lines",
        ALL_AGENTS,
        ids=[a[1] for a in ALL_AGENTS],
    )
    def test_agent_has_frontmatter_with_tools(
        self, modules_dir: Path, module: str, agent: str, _min_lines: int
    ) -> None:
        path = modules_dir / module / "agents" / f"{agent}.md"
        fm = _extract_frontmatter(path)
        assert fm is not None, f"{agent}.md has no YAML frontmatter"
        assert "name" in fm, f"{agent}.md frontmatter missing 'name'"
        assert "description" in fm, f"{agent}.md frontmatter missing 'description'"
        assert "tools" in fm, f"{agent}.md frontmatter missing 'tools'"
        assert isinstance(fm["tools"], list), f"{agent}.md 'tools' must be a list"
        assert len(fm["tools"]) >= 1, f"{agent}.md must list at least 1 tool"

    @pytest.mark.parametrize(
        "module,agent,min_lines",
        ALL_AGENTS,
        ids=[a[1] for a in ALL_AGENTS],
    )
    def test_agent_minimum_lines(
        self, modules_dir: Path, module: str, agent: str, min_lines: int
    ) -> None:
        path = modules_dir / module / "agents" / f"{agent}.md"
        lines = _line_count(path)
        assert lines >= min_lines, f"{agent}.md has {lines} lines, expected >= {min_lines}"


# ---------------------------------------------------------------------------
# Command Definition Tests
# ---------------------------------------------------------------------------

ALL_COMMANDS = [
    ("commands-dev", "debug-RCA", 60),
    ("commands-dev", "smart-commit", 40),
    ("commands-dev", "orchestrate", 60),
    ("commands-dev", "verify", 40),
    ("commands-prp", "prp-base-create", 60),
    ("commands-prp", "prp-base-execute", 60),
]


class TestCommandFiles:
    """Validate all command definition files exist with proper structure."""

    @pytest.mark.parametrize(
        "module,command,_min_lines",
        ALL_COMMANDS,
        ids=[c[1] for c in ALL_COMMANDS],
    )
    def test_command_file_exists(
        self, modules_dir: Path, module: str, command: str, _min_lines: int
    ) -> None:
        path = modules_dir / module / "commands" / f"{command}.md"
        assert path.is_file(), f"Command file missing: {module}/commands/{command}.md"

    @pytest.mark.parametrize(
        "module,command,_min_lines",
        ALL_COMMANDS,
        ids=[c[1] for c in ALL_COMMANDS],
    )
    def test_command_has_frontmatter(
        self, modules_dir: Path, module: str, command: str, _min_lines: int
    ) -> None:
        path = modules_dir / module / "commands" / f"{command}.md"
        fm = _extract_frontmatter(path)
        assert fm is not None, f"{command}.md has no YAML frontmatter"
        assert "name" in fm, f"{command}.md frontmatter missing 'name'"
        assert "description" in fm, f"{command}.md frontmatter missing 'description'"

    @pytest.mark.parametrize(
        "module,command,min_lines",
        ALL_COMMANDS,
        ids=[c[1] for c in ALL_COMMANDS],
    )
    def test_command_minimum_lines(
        self, modules_dir: Path, module: str, command: str, min_lines: int
    ) -> None:
        path = modules_dir / module / "commands" / f"{command}.md"
        lines = _line_count(path)
        assert lines >= min_lines, f"{command}.md has {lines} lines, expected >= {min_lines}"

    def test_total_command_count(self, modules_dir: Path) -> None:
        """Ensure at least 6 command files exist across all modules."""
        commands: list[Path] = []
        for commands_dir in modules_dir.rglob("commands/"):
            if commands_dir.is_dir():
                commands.extend(p for p in commands_dir.glob("*.md") if p.name != "MODULE.md")
        assert len(commands) >= 6, f"Expected >= 6 command files, found {len(commands)}"
