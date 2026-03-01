"""Reusable regex patterns for secrets, PII, and bash safety detection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Match:
    """A single pattern match result."""

    pattern_name: str
    matched_text: str
    start: int
    end: int


@dataclass(frozen=True)
class PatternSet:
    """A named collection of regex patterns with optional whitelist exclusions."""

    name: str
    patterns: list[re.Pattern[str]]
    whitelist: list[re.Pattern[str]]

    def detect(self, text: str) -> list[Match]:
        """Scan text for pattern matches, excluding whitelisted matches."""
        # Collect whitelisted spans first
        whitelisted_spans: set[tuple[int, int]] = set()
        for wp in self.whitelist:
            for wm in wp.finditer(text):
                whitelisted_spans.add((wm.start(), wm.end()))

        matches: list[Match] = []
        for pattern in self.patterns:
            for m in pattern.finditer(text):
                # Check if this match overlaps with any whitelisted span
                is_whitelisted = any(
                    m.start() >= ws and m.end() <= we for ws, we in whitelisted_spans
                )
                if not is_whitelisted:
                    matches.append(
                        Match(
                            pattern_name=pattern.pattern,
                            matched_text=m.group(),
                            start=m.start(),
                            end=m.end(),
                        )
                    )
        return matches


class SecretPatterns:
    """Factory for secret detection patterns."""

    @staticmethod
    def create() -> PatternSet:
        """Create a PatternSet for detecting secrets and credentials."""
        patterns = [
            # Generic API key assignments
            re.compile(
                r"""(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)"""
                r"""\s*[=:]\s*["'][A-Za-z0-9\-_]{16,}["']""",
                re.IGNORECASE,
            ),
            # AWS Access Key ID
            re.compile(r"AKIA[0-9A-Z]{16}"),
            # GitHub Personal Access Token
            re.compile(r"ghp_[A-Za-z0-9]{36}"),
            # OpenAI API key
            re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{20,}"),
            # Private key headers
            re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
            # Generic high-entropy tokens (base64-like, 40+ chars)
            re.compile(
                r"""(?:password|passwd|pwd)\s*[=:]\s*["'][^\s"']{8,}["']""",
                re.IGNORECASE,
            ),
        ]
        whitelist = [
            # Placeholder/example values
            re.compile(r"sk-(?:proj-)?xxx+", re.IGNORECASE),
            re.compile(
                r"""(?:api[_-]?key|secret)\s*[=:]\s*["'](?:your[_-]|example)""", re.IGNORECASE
            ),
        ]
        return PatternSet(name="secrets", patterns=patterns, whitelist=whitelist)


class PIIPatterns:
    """Factory for PII detection patterns with country-specific support."""

    _COUNTRY_PATTERNS: ClassVar[dict[str, list[re.Pattern[str]]]] = {
        "BR": [
            # CPF: 000.000.000-00
            re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"),
            # CNPJ: 00.000.000/0000-00
            re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"),
        ],
        "US": [
            # SSN: 000-00-0000
            re.compile(r"\d{3}-\d{2}-\d{4}"),
        ],
        "EU": [
            # Email
            re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            # Phone (international format)
            re.compile(r"\+\d{1,3}\s?\d{4,14}"),
        ],
    }

    @classmethod
    def for_country(cls, country_code: str) -> PatternSet:
        """Create a PatternSet for PII detection for a specific country."""
        patterns = cls._COUNTRY_PATTERNS.get(country_code.upper(), [])
        return PatternSet(name=f"pii_{country_code.lower()}", patterns=patterns, whitelist=[])


class BashSafetyPatterns:
    """Factory for detecting dangerous bash commands."""

    @staticmethod
    def create() -> PatternSet:
        """Create a PatternSet for dangerous shell command detection."""
        patterns = [
            # rm -rf / or rm -rf /*
            re.compile(r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?-*r[a-zA-Z]*f?\s+/(?:\s|$|\*)"),
            re.compile(r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+)?-*f[a-zA-Z]*r?\s+/(?:\s|$|\*)"),
            # chmod 777
            re.compile(r"chmod\s+777\s+"),
            # curl | bash / wget | sh
            re.compile(r"(?:curl|wget)\s+.*\|\s*(?:ba)?sh"),
            # dd writing to block devices
            re.compile(r"dd\s+.*of=/dev/(?:sd|hd|nvme|vd)[a-z]"),
            # mkfs on block devices
            re.compile(r"mkfs\s+.*(?:/dev/(?:sd|hd|nvme|vd)[a-z])"),
            # Fork bomb
            re.compile(r":\(\)\{.*\|.*\}"),
            # Direct write to /dev/sda etc.
            re.compile(r">\s*/dev/(?:sd|hd|nvme|vd)[a-z]"),
        ]
        return PatternSet(name="bash_safety", patterns=patterns, whitelist=[])
