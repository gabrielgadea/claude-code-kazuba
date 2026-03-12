"""P1E: Test coverage for rules-core module."""

from pathlib import Path

KAZUBA_ROOT = Path(__file__).resolve().parent.parent
RULES_MODULE = KAZUBA_ROOT / "claude_code_kazuba" / "data" / "modules" / "rules-core"


class TestRulesCoreModule:
    def test_module_dir_exists(self):
        assert RULES_MODULE.exists()

    def test_module_md_exists(self):
        assert (RULES_MODULE / "MODULE.md").exists()

    def test_governance_rule_exists(self):
        assert (RULES_MODULE / "rules" / "core" / "00-core-governance.md").exists()

    def test_plan_as_code_rule_exists(self):
        assert (RULES_MODULE / "rules" / "core" / "plan-as-code.md").exists()

    def test_governance_has_code_first(self):
        content = (RULES_MODULE / "rules" / "core" / "00-core-governance.md").read_text()
        assert "CODE-FIRST" in content
        assert "DISCOVER" in content

    def test_plan_as_code_has_violations(self):
        content = (RULES_MODULE / "rules" / "core" / "plan-as-code.md").read_text()
        assert "VIOLATION" in content

    def test_no_antt_contamination(self):
        for f in RULES_MODULE.rglob("*.md"):
            content = f.read_text()
            assert "ANTTTaskType" not in content
            assert "50500" not in content
