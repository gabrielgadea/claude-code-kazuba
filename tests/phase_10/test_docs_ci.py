"""Tests for Phase 10: CI pipeline and documentation.

Validates that all CI and documentation files exist, meet minimum
line counts, and reference actual project artifacts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # noqa: TC002

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# --- CI Pipeline ---


class TestCIPipeline:
    """Tests for .github/workflows/ci.yml."""

    def test_ci_yml_exists(self) -> None:
        """CI workflow file must exist."""
        ci_path = BASE_DIR / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists(), f"Missing: {ci_path}"

    def test_ci_yml_is_valid_yaml(self) -> None:
        """CI workflow must be valid YAML."""
        ci_path = BASE_DIR / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict), "ci.yml must parse to a dict"

    def test_ci_yml_min_lines(self) -> None:
        """CI workflow must have at least 50 lines."""
        ci_path = BASE_DIR / ".github" / "workflows" / "ci.yml"
        lines = ci_path.read_text().splitlines()
        assert len(lines) >= 50, f"ci.yml has {len(lines)} lines, expected >= 50"

    def test_ci_yml_has_lint_job(self) -> None:
        """CI must include a lint job."""
        ci_path = BASE_DIR / ".github" / "workflows" / "ci.yml"
        parsed = yaml.safe_load(ci_path.read_text())
        assert "lint" in parsed.get("jobs", {}), "Missing 'lint' job"

    def test_ci_yml_has_test_job(self) -> None:
        """CI must include a test job."""
        ci_path = BASE_DIR / ".github" / "workflows" / "ci.yml"
        parsed = yaml.safe_load(ci_path.read_text())
        assert "test" in parsed.get("jobs", {}), "Missing 'test' job"

    def test_ci_yml_has_typecheck_job(self) -> None:
        """CI must include a typecheck job."""
        ci_path = BASE_DIR / ".github" / "workflows" / "ci.yml"
        parsed = yaml.safe_load(ci_path.read_text())
        assert "typecheck" in parsed.get("jobs", {}), "Missing 'typecheck' job"

    def test_ci_triggers_on_push_and_pr(self) -> None:
        """CI must trigger on push to main and pull requests."""
        ci_path = BASE_DIR / ".github" / "workflows" / "ci.yml"
        parsed = yaml.safe_load(ci_path.read_text())
        on_config = parsed.get("on", parsed.get(True, {}))
        assert "push" in on_config, "Missing push trigger"
        assert "pull_request" in on_config, "Missing pull_request trigger"


# --- Documentation Files ---


DOC_FILES = {
    "docs/ARCHITECTURE.md": 100,
    "docs/HOOKS_REFERENCE.md": 150,
    "docs/MODULES_CATALOG.md": 80,
    "docs/CREATING_MODULES.md": 60,
    "docs/MIGRATION.md": 40,
}


class TestDocumentation:
    """Tests for documentation files."""

    @pytest.mark.parametrize("doc_path", list(DOC_FILES.keys()))
    def test_doc_file_exists(self, doc_path: str) -> None:
        """Each documentation file must exist."""
        full_path = BASE_DIR / doc_path
        assert full_path.exists(), f"Missing: {full_path}"

    @pytest.mark.parametrize(
        ("doc_path", "min_lines"),
        list(DOC_FILES.items()),
    )
    def test_doc_min_lines(self, doc_path: str, min_lines: int) -> None:
        """Each documentation file must meet minimum line count."""
        full_path = BASE_DIR / doc_path
        lines = full_path.read_text().splitlines()
        assert len(lines) >= min_lines, (
            f"{doc_path} has {len(lines)} lines, expected >= {min_lines}"
        )


# --- README ---


class TestReadme:
    """Tests for README.md."""

    def test_readme_exists(self) -> None:
        """README.md must exist at project root."""
        readme = BASE_DIR / "README.md"
        assert readme.exists(), f"Missing: {readme}"

    def test_readme_has_badges(self) -> None:
        """README must include CI and license badges."""
        readme = BASE_DIR / "README.md"
        content = readme.read_text()
        assert "[![CI]" in content, "Missing CI badge"
        assert "[![License" in content or "License" in content, "Missing license badge"

    def test_readme_has_quick_start(self) -> None:
        """README must have a Quick Start section."""
        readme = BASE_DIR / "README.md"
        content = readme.read_text()
        assert "Quick Start" in content, "Missing Quick Start section"

    def test_readme_has_clone_instruction(self) -> None:
        """README quick start must include git clone."""
        readme = BASE_DIR / "README.md"
        content = readme.read_text()
        assert "git clone" in content, "Missing git clone instruction"

    def test_readme_has_preset_mention(self) -> None:
        """README must mention presets."""
        readme = BASE_DIR / "README.md"
        content = readme.read_text()
        assert "preset" in content.lower(), "Missing preset mention"

    def test_readme_has_module_table(self) -> None:
        """README must include a module catalog or architecture section."""
        readme = BASE_DIR / "README.md"
        content = readme.read_text().lower()
        assert "module" in content and ("catalog" in content or "arquitetura" in content), (
            "Missing module catalog/architecture section"
        )

    def test_readme_has_contributing(self) -> None:
        """README must have a Contributing section."""
        readme = BASE_DIR / "README.md"
        content = readme.read_text()
        assert "Contributing" in content or "Contribuindo" in content, (
            "Missing Contributing/Contribuindo section"
        )

    def test_readme_has_license(self) -> None:
        """README must mention the license."""
        readme = BASE_DIR / "README.md"
        content = readme.read_text()
        assert "License" in content or "MIT" in content, "Missing license info"


# --- Cross-reference validation ---


# All module names from the project
ACTUAL_MODULE_NAMES = [
    "core",
    "hooks-essential",
    "hooks-quality",
    "hooks-routing",
    "skills-dev",
    "skills-meta",
    "skills-planning",
    "skills-research",
    "agents-dev",
    "commands-dev",
    "commands-prp",
    "contexts",
    "config-hypervisor",
    "team-orchestrator",
]


class TestCrossReferences:
    """Tests that docs reference actual module names."""

    def test_catalog_references_all_modules(self) -> None:
        """MODULES_CATALOG.md must reference every module."""
        catalog = (BASE_DIR / "docs" / "MODULES_CATALOG.md").read_text()
        for module_name in ACTUAL_MODULE_NAMES:
            assert module_name in catalog, (
                f"MODULES_CATALOG.md missing reference to module: {module_name}"
            )

    def test_architecture_references_module_dirs(self) -> None:
        """ARCHITECTURE.md must reference key module directories."""
        arch = (BASE_DIR / "docs" / "ARCHITECTURE.md").read_text()
        key_dirs = ["hooks-essential", "hooks-quality", "skills-dev", "agents-dev"]
        for dir_name in key_dirs:
            assert dir_name in arch, f"ARCHITECTURE.md missing reference to: {dir_name}"

    def test_hooks_reference_mentions_all_events(self) -> None:
        """HOOKS_REFERENCE.md must document all 18 hook events."""
        hooks_ref = (BASE_DIR / "docs" / "HOOKS_REFERENCE.md").read_text()
        events = [
            "PreToolUse",
            "PostToolUse",
            "UserPromptSubmit",
            "Stop",
            "PreCompact",
            "SessionStart",
            "SessionStop",
            "SubagentToolUse",
            "PostSubagentToolUse",
            "PreAssistantTurn",
            "PostAssistantTurn",
            "PreApproval",
            "PostApproval",
            "PrePlanModeApproval",
            "PostPlanModeApproval",
            "PreNotification",
            "PostNotification",
            "Heartbeat",
        ]
        for event in events:
            assert event in hooks_ref, f"HOOKS_REFERENCE.md missing event: {event}"

    def test_docs_link_to_each_other(self) -> None:
        """README should link to documentation files."""
        readme = (BASE_DIR / "README.md").read_text()
        for doc_name in ["ARCHITECTURE.md", "HOOKS_REFERENCE.md", "MODULES_CATALOG.md"]:
            assert doc_name in readme, f"README missing link to {doc_name}"

    def test_readme_references_actual_presets(self) -> None:
        """README must reference the actual preset names."""
        readme = (BASE_DIR / "README.md").read_text()
        presets_dir = BASE_DIR / "claude_code_kazuba" / "data" / "presets"
        for preset_file in presets_dir.glob("*.txt"):
            preset_name = preset_file.stem
            assert preset_name in readme, f"README missing reference to preset: {preset_name}"
