"""Phase 2 Tests: Core module — templates, rules, and MODULE.md.

Tests cover:
- File existence and minimum line counts
- Jinja2 variable presence in CLAUDE.md.template
- settings.json.template renders to valid JSON
- MODULE.md has required YAML frontmatter
- All 4 rules files exist and contain expected sections
- Templates render correctly via lib/template_engine.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from claude_code_kazuba.template_engine import TemplateEngine


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def core_dir(project_root: Path) -> Path:
    """Return the core/ directory."""
    return project_root / "core"


@pytest.fixture
def rules_dir(core_dir: Path) -> Path:
    """Return the core/rules/ directory."""
    return core_dir / "rules"


@pytest.fixture
def template_engine(core_dir: Path) -> TemplateEngine:
    """Create a TemplateEngine pointing at the core directory."""
    return TemplateEngine(core_dir)


@pytest.fixture
def sample_claude_vars() -> dict[str, object]:
    """Sample variables for rendering CLAUDE.md.template."""
    return {
        "project_name": "test-project",
        "description": "A test project for validation",
        "stack": "Python 3.12 | pytest | ruff",
        "language": "Python",
        "version": "1.0.0",
        "modules": [
            {"name": "core", "version": "0.1.0", "description": "Core module"},
            {"name": "hooks-dev", "version": "1.0.0", "description": "Dev hooks"},
        ],
        "commands": "pytest tests/ -v\nruff check .",
        "rules": "- Follow TDD.\n- Never commit secrets.",
    }


@pytest.fixture
def sample_settings_vars() -> dict[str, object]:
    """Sample variables for rendering settings.json.template."""
    return {
        "permissions_allow": ["Bash(git status)", "Read"],
        "permissions_deny": ["Bash(rm -rf /)"],
        "hooks_pre_tool_use": [],
        "hooks_post_tool_use": [],
        "hooks_user_prompt_submit": [],
        "hooks_stop": [],
        "env_vars": {"PROJECT_ROOT": "/tmp/test"},
    }


# ---------------------------------------------------------------------------
# File existence and minimum line counts
# ---------------------------------------------------------------------------


class TestFileExistence:
    """Verify all core module files exist and meet minimum line counts."""

    FILES_AND_MIN_LINES = [
        ("CLAUDE.md.template", 150),
        ("settings.json.template", 60),
        ("settings.local.json.template", 20),
        (".gitignore.template", 15),
        ("MODULE.md", 30),
        ("rules/code-style.md", 50),
        ("rules/security.md", 60),
        ("rules/testing.md", 40),
        ("rules/git-workflow.md", 40),
    ]

    @pytest.mark.parametrize("file_path,min_lines", FILES_AND_MIN_LINES)
    def test_file_exists(self, core_dir: Path, file_path: str, min_lines: int) -> None:
        full_path = core_dir / file_path
        assert full_path.is_file(), f"File core/{file_path} missing"

    @pytest.mark.parametrize("file_path,min_lines", FILES_AND_MIN_LINES)
    def test_file_meets_min_lines(self, core_dir: Path, file_path: str, min_lines: int) -> None:
        full_path = core_dir / file_path
        lines = len(full_path.read_text().splitlines())
        assert lines >= min_lines, f"core/{file_path}: {lines} lines < {min_lines} required"


# ---------------------------------------------------------------------------
# CLAUDE.md.template — Jinja2 variables and key sections
# ---------------------------------------------------------------------------


class TestClaudeMdTemplate:
    """Verify CLAUDE.md.template has required Jinja2 variables and sections."""

    REQUIRED_VARIABLES = [
        "project_name",
        "stack",
        "description",
        "commands",
        "rules",
        "modules",
    ]

    @pytest.mark.parametrize("var_name", REQUIRED_VARIABLES)
    def test_has_jinja2_variable(self, core_dir: Path, var_name: str) -> None:
        content = (core_dir / "CLAUDE.md.template").read_text()
        # Match {{ var_name }} or {% ... var_name ... %}
        pattern = rf"(\{{\{{\s*{var_name})|(\{{%.*{var_name}.*%\}})"
        assert re.search(pattern, content), (
            f"CLAUDE.md.template missing Jinja2 variable: {var_name}"
        )

    def test_has_crc_cycle(self, core_dir: Path) -> None:
        content = (core_dir / "CLAUDE.md.template").read_text()
        for step in ["EXECUTE", "OBSERVE", "DIAGNOSE", "DECIDE", "ACT", "VALIDATE"]:
            assert step in content, f"CRC cycle missing step: {step}"

    def test_has_circuit_breakers(self, core_dir: Path) -> None:
        content = (core_dir / "CLAUDE.md.template").read_text()
        for breaker in [
            "Context overflow",
            "Loop detection",
            "Scope creep",
            "Hallucination risk",
            "Yak shaving",
        ]:
            assert breaker in content, f"Circuit breaker missing: {breaker}"

    def test_has_validation_gate(self, core_dir: Path) -> None:
        content = (core_dir / "CLAUDE.md.template").read_text()
        for gate in ["Functional", "Robust", "Readable", "Documented", "Secure", "No Regression"]:
            assert gate in content, f"Validation gate missing dimension: {gate}"

    def test_has_refinement_taxonomy(self, core_dir: Path) -> None:
        content = (core_dir / "CLAUDE.md.template").read_text()
        for level in ["L1", "L2", "L3", "L4", "L5"]:
            assert level in content, f"Refinement taxonomy missing level: {level}"

    def test_renders_with_sample_vars(
        self, template_engine: TemplateEngine, sample_claude_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("CLAUDE.md.template", sample_claude_vars)
        assert "test-project" in result
        assert "Python 3.12" in result
        assert "A test project for validation" in result

    def test_renders_with_empty_modules(self, template_engine: TemplateEngine) -> None:
        result = template_engine.render(
            "CLAUDE.md.template",
            {"project_name": "empty", "stack": "Node.js", "modules": []},
        )
        assert "empty" in result
        assert "No optional modules installed" in result

    def test_renders_modules_list(
        self, template_engine: TemplateEngine, sample_claude_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("CLAUDE.md.template", sample_claude_vars)
        assert "core" in result
        assert "hooks-dev" in result


# ---------------------------------------------------------------------------
# settings.json.template — Valid JSON after rendering
# ---------------------------------------------------------------------------


class TestSettingsJsonTemplate:
    """Verify settings.json.template renders to valid JSON."""

    def test_renders_to_valid_json(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_has_schema_key(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert "$schema" in parsed

    def test_has_permissions(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert "permissions" in parsed
        assert "allow" in parsed["permissions"]
        assert "deny" in parsed["permissions"]

    def test_has_hooks_section(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert "hooks" in parsed

    def test_has_env_section(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert "env" in parsed

    def test_permissions_populated(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert "Bash(git status)" in parsed["permissions"]["allow"]
        assert "Read" in parsed["permissions"]["allow"]

    def test_renders_with_defaults(self, template_engine: TemplateEngine) -> None:
        """Rendering with no custom vars should still produce valid JSON."""
        result = template_engine.render("settings.json.template", {})
        parsed = json.loads(result)
        assert "$schema" in parsed
        # Default permissions should be present
        assert len(parsed["permissions"]["allow"]) > 0

    def test_env_vars_populated(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert parsed["env"]["PROJECT_ROOT"] == "/tmp/test"


# ---------------------------------------------------------------------------
# settings.local.json.template
# ---------------------------------------------------------------------------


class TestSettingsLocalTemplate:
    """Verify settings.local.json.template renders correctly."""

    def test_renders_to_valid_json(self, template_engine: TemplateEngine) -> None:
        result = template_engine.render("settings.local.json.template", {})
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_has_schema_key(self, template_engine: TemplateEngine) -> None:
        result = template_engine.render("settings.local.json.template", {})
        parsed = json.loads(result)
        assert "$schema" in parsed

    def test_has_comment_about_gitignored(self, core_dir: Path) -> None:
        content = (core_dir / "settings.local.json.template").read_text()
        assert "gitignore" in content.lower()


# ---------------------------------------------------------------------------
# .gitignore.template
# ---------------------------------------------------------------------------


class TestGitignoreTemplate:
    """Verify .gitignore.template has essential patterns."""

    REQUIRED_PATTERNS = [
        "settings.local.json",
        "__pycache__",
        "*.toon",
        ".env",
        "*.log",
    ]

    @pytest.mark.parametrize("pattern", REQUIRED_PATTERNS)
    def test_has_pattern(self, core_dir: Path, pattern: str) -> None:
        content = (core_dir / ".gitignore.template").read_text()
        assert pattern in content, f".gitignore.template missing pattern: {pattern}"


# ---------------------------------------------------------------------------
# MODULE.md — YAML frontmatter
# ---------------------------------------------------------------------------


class TestModuleMd:
    """Verify MODULE.md has required YAML frontmatter."""

    def test_has_yaml_frontmatter(self, core_dir: Path) -> None:
        content = (core_dir / "MODULE.md").read_text()
        assert content.startswith("---"), "MODULE.md must start with YAML frontmatter"
        # Find closing ---
        second_marker = content.index("---", 3)
        assert second_marker > 3, "MODULE.md must have closing --- for frontmatter"

    def test_frontmatter_has_required_fields(self, core_dir: Path) -> None:
        content = (core_dir / "MODULE.md").read_text()
        # Extract YAML between --- markers
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict)
        for field in ["name", "version", "description", "dependencies", "provides"]:
            assert field in frontmatter, f"MODULE.md frontmatter missing field: {field}"

    def test_name_is_core(self, core_dir: Path) -> None:
        content = (core_dir / "MODULE.md").read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter["name"] == "core"

    def test_version_is_semver(self, core_dir: Path) -> None:
        content = (core_dir / "MODULE.md").read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        version = frontmatter["version"]
        assert re.match(r"^\d+\.\d+\.\d+$", version), f"Version {version} is not semver"

    def test_dependencies_is_empty_list(self, core_dir: Path) -> None:
        content = (core_dir / "MODULE.md").read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter["dependencies"] == []

    def test_provides_lists_templates_and_rules(self, core_dir: Path) -> None:
        content = (core_dir / "MODULE.md").read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        provides = frontmatter["provides"]
        assert "templates" in provides or "rules" in provides


# ---------------------------------------------------------------------------
# Rules files — existence and content validation
# ---------------------------------------------------------------------------


class TestRulesFiles:
    """Verify all 4 rules files exist and contain expected sections."""

    RULES_FILES = [
        "code-style.md",
        "security.md",
        "testing.md",
        "git-workflow.md",
    ]

    @pytest.mark.parametrize("rule_file", RULES_FILES)
    def test_rule_file_exists(self, rules_dir: Path, rule_file: str) -> None:
        assert (rules_dir / rule_file).is_file(), f"Rule file {rule_file} missing"

    def test_code_style_has_naming(self, rules_dir: Path) -> None:
        content = (rules_dir / "code-style.md").read_text()
        assert "naming" in content.lower()

    def test_code_style_has_imports(self, rules_dir: Path) -> None:
        content = (rules_dir / "code-style.md").read_text()
        assert "import" in content.lower()

    def test_code_style_has_file_organization(self, rules_dir: Path) -> None:
        content = (rules_dir / "code-style.md").read_text()
        assert "file organization" in content.lower() or "file org" in content.lower()

    def test_code_style_has_no_overengineering(self, rules_dir: Path) -> None:
        content = (rules_dir / "code-style.md").read_text()
        assert "over-engineer" in content.lower() or "yagni" in content.lower()

    def test_security_has_owasp(self, rules_dir: Path) -> None:
        content = (rules_dir / "security.md").read_text()
        assert "OWASP" in content

    def test_security_has_secrets(self, rules_dir: Path) -> None:
        content = (rules_dir / "security.md").read_text()
        assert "secret" in content.lower()

    def test_security_has_pii(self, rules_dir: Path) -> None:
        content = (rules_dir / "security.md").read_text()
        assert "PII" in content

    def test_security_has_input_validation(self, rules_dir: Path) -> None:
        content = (rules_dir / "security.md").read_text()
        assert "input validation" in content.lower() or "validate" in content.lower()

    def test_security_has_dependency_audit(self, rules_dir: Path) -> None:
        content = (rules_dir / "security.md").read_text()
        assert "audit" in content.lower()

    def test_testing_has_tdd(self, rules_dir: Path) -> None:
        content = (rules_dir / "testing.md").read_text()
        assert "TDD" in content or "Red" in content

    def test_testing_has_coverage(self, rules_dir: Path) -> None:
        content = (rules_dir / "testing.md").read_text()
        assert "90%" in content

    def test_testing_has_pyramid(self, rules_dir: Path) -> None:
        content = (rules_dir / "testing.md").read_text()
        assert "pyramid" in content.lower() or (
            "unit" in content.lower() and "integration" in content.lower()
        )

    def test_testing_has_naming_conventions(self, rules_dir: Path) -> None:
        content = (rules_dir / "testing.md").read_text()
        assert "naming" in content.lower() or "test_" in content

    def test_testing_has_fixture(self, rules_dir: Path) -> None:
        content = (rules_dir / "testing.md").read_text()
        assert "fixture" in content.lower()

    def test_git_has_branch_naming(self, rules_dir: Path) -> None:
        content = (rules_dir / "git-workflow.md").read_text()
        assert "branch" in content.lower()
        assert "feat/" in content

    def test_git_has_conventional_commits(self, rules_dir: Path) -> None:
        content = (rules_dir / "git-workflow.md").read_text()
        assert "conventional" in content.lower() or "type" in content.lower()

    def test_git_has_atomic_commits(self, rules_dir: Path) -> None:
        content = (rules_dir / "git-workflow.md").read_text()
        assert "atomic" in content.lower()

    def test_git_has_pr_workflow(self, rules_dir: Path) -> None:
        content = (rules_dir / "git-workflow.md").read_text()
        assert "PR" in content or "pull request" in content.lower()

    def test_git_has_force_push_policy(self, rules_dir: Path) -> None:
        content = (rules_dir / "git-workflow.md").read_text()
        assert "force-push" in content.lower() or "force push" in content.lower()


# ---------------------------------------------------------------------------
# Template rendering via TemplateEngine integration
# ---------------------------------------------------------------------------


class TestTemplateRendering:
    """Integration tests: render templates via lib/template_engine.py."""

    def test_claude_md_full_render(
        self, template_engine: TemplateEngine, sample_claude_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("CLAUDE.md.template", sample_claude_vars)
        # Key sections present in rendered output
        assert "# test-project" in result
        assert "EXECUTE" in result
        assert "VALIDATE" in result
        assert "Circuit Breaker" in result or "Circuit Breakers" in result
        assert "L1" in result
        assert "pytest tests/ -v" in result

    def test_settings_json_full_render(
        self, template_engine: TemplateEngine, sample_settings_vars: dict[str, object]
    ) -> None:
        result = template_engine.render("settings.json.template", sample_settings_vars)
        parsed = json.loads(result)
        assert parsed["$schema"] == "https://json.schemastore.org/claude-code-settings.json"
        assert "hooks" in parsed
        assert "PreToolUse" in parsed["hooks"]
        assert "PostToolUse" in parsed["hooks"]
        assert "UserPromptSubmit" in parsed["hooks"]

    def test_settings_local_full_render(self, template_engine: TemplateEngine) -> None:
        result = template_engine.render(
            "settings.local.json.template",
            {"local_env_vars": {"MY_KEY": "my_value"}},
        )
        parsed = json.loads(result)
        assert parsed["env"]["MY_KEY"] == "my_value"

    def test_claude_md_renders_without_optional_vars(
        self, template_engine: TemplateEngine
    ) -> None:
        """Minimal vars — only required fields."""
        result = template_engine.render(
            "CLAUDE.md.template",
            {"project_name": "minimal", "stack": "Go"},
        )
        assert "# minimal" in result
        assert "Go" in result
