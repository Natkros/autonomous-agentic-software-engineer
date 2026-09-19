"""Regex-based secret detection over plain text (any file type — unlike
`static_analysis.py`, this isn't Python-specific). Modeled on the same
idea as gitleaks/trufflehog: known credential *shapes*, not a generic
"looks random" entropy check, to keep the false-positive rate manageable
in a small, dependency-free implementation.

Real patterns matched against real-shaped (but fake/invalid) example
secrets in `tools/tests/test_secret_scanner.py` — none of the examples in
this file or its tests are live credentials.
"""
from __future__ import annotations

import re

from core.state.schemas import SecurityFinding, Severity

_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("aws-access-key-id", "AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic-private-key", "Private key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("slack-token", "Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("github-token", "GitHub personal access token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    (
        "generic-secret-assignment",
        "Hardcoded credential-shaped assignment",
        re.compile(r"""(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['"][^'"]{8,}['"]"""),
    ),
]


def scan_text_for_secrets(content: str, file_path: str) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []

    for rule_id, description, pattern in _PATTERNS:
        for match in pattern.finditer(content):
            line_number = content.count("\n", 0, match.start()) + 1
            findings.append(SecurityFinding(
                severity=Severity.BLOCKER, rule_id=rule_id,
                message=f"{description} found in source.",
                file=file_path, line=line_number,
            ))

    return findings
