"""The Security Agent (spec section 25). Deterministic — no LLM call.
Real static analysis and secret scanning already produce a structured,
severity-classified finding list; there is nothing for a model to add to
"does this line call eval()," the same principle already applied to the
Repository Explorer Agent in Phase 3.
"""
from __future__ import annotations

from core.policies.permissions import AutonomyLevel
from core.state.schemas import SecurityFinding, SecurityScanResult, Severity
from tools.base import AuditLog
from tools.security.security_scan_tool import SecurityScanTool


class SecurityScanError(RuntimeError):
    pass


class SecurityAgent:
    def __init__(self, scan_tool: SecurityScanTool | None = None):
        self.scan_tool = scan_tool or SecurityScanTool()

    def scan(self, repository_path: str) -> SecurityScanResult:
        audit_log = AuditLog()
        result = self.scan_tool.run(audit_log, AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=repository_path)
        if not result.success:
            raise SecurityScanError(result.error)

        findings = [
            SecurityFinding(
                severity=Severity(f["severity"]), rule_id=f["rule_id"],
                message=f["message"], file=f["file"], line=f.get("line"),
            )
            for f in result.output["findings"]
        ]
        return SecurityScanResult(findings=findings)
