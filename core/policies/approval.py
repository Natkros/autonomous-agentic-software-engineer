"""Builds the human-approval prompt (spec section 27) for an action that
exceeds what the current autonomy level permits autonomously. Whether
approval is needed is a deterministic function of `PermissionLevel` and
`AutonomyLevel` (see `permissions.py`) — never an LLM's judgment call.
"""
from __future__ import annotations

from core.policies.permissions import AutonomyLevel, PermissionLevel, requires_human_approval
from core.state.schemas import ApprovalRequest, Severity

_RISK_BY_PERMISSION = {
    PermissionLevel.READ_ONLY: Severity.INFO,
    PermissionLevel.SAFE_WRITE: Severity.LOW,
    PermissionLevel.EXECUTION: Severity.MEDIUM,
    PermissionLevel.GIT_WRITE: Severity.HIGH,
    PermissionLevel.DEPLOYMENT: Severity.BLOCKER,
}


def build_approval_request(
    action: str,
    permission: PermissionLevel,
    autonomy_level: AutonomyLevel,
    files_affected: list[str] | None = None,
    commands: list[str] | None = None,
    reason: str = "",
) -> ApprovalRequest | None:
    """Returns an ApprovalRequest if `action` (requiring `permission`)
    would need a human to sign off at the given `autonomy_level`;
    returns None if it's within what that autonomy level already permits.
    """
    if not requires_human_approval(permission, autonomy_level):
        return None

    return ApprovalRequest(
        action=action,
        reason=reason or f"'{action}' requires {permission.name}, which exceeds autonomy level {autonomy_level.name}.",
        files_affected=files_affected or [],
        commands=commands or [],
        risk_level=_RISK_BY_PERMISSION[permission],
    )
