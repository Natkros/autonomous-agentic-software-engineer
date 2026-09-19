"""The Code Review Agent (spec section 24): reviews only the diff (here,
a `PatchProposal`'s actual `content`), never the whole file. Deterministic
— no LLM call, for the same reason as the Security Agent: the checks it
runs (security patterns, stub-body detection) are direct computations,
not judgment calls that need a model.
"""
from __future__ import annotations

import re

from core.state.schemas import PatchProposal, ReviewFinding, ReviewResult, Severity
from tools.security.secret_scanner import scan_text_for_secrets
from tools.security.static_analysis import analyze_python_source

_STUB_BODY_RE = re.compile(r"\n\s*pass\s*$")


class CodeReviewAgent:
    def review(self, proposal: PatchProposal) -> ReviewResult:
        findings: list[ReviewFinding] = []

        if not proposal.content:
            findings.append(ReviewFinding(
                severity=Severity.INFO, category="review",
                message="Proposal has no content to review (description-only).",
                file=proposal.file,
            ))
            return ReviewResult(findings=findings)

        if proposal.file.endswith(".py"):
            for finding in analyze_python_source(proposal.content, proposal.file):
                findings.append(ReviewFinding(
                    severity=finding.severity, category="security",
                    message=finding.message, file=finding.file, line=finding.line,
                    rule_id=finding.rule_id,
                ))

        for finding in scan_text_for_secrets(proposal.content, proposal.file):
            findings.append(ReviewFinding(
                severity=finding.severity, category="security",
                message=finding.message, file=finding.file, line=finding.line,
                rule_id=finding.rule_id,
            ))

        if _STUB_BODY_RE.search(proposal.content):
            findings.append(ReviewFinding(
                severity=Severity.LOW, category="quality",
                message="Proposed change appears to be an unimplemented stub (function body is just 'pass').",
                file=proposal.file, rule_id="stub-implementation",
            ))

        return ReviewResult(findings=findings)
