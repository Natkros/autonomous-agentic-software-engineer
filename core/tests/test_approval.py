from core.policies.approval import build_approval_request
from core.policies.permissions import AutonomyLevel, PermissionLevel
from core.state.schemas import ApprovalStatus, Severity


def test_no_approval_needed_within_autonomy():
    request = build_approval_request(
        action="filesystem.read", permission=PermissionLevel.READ_ONLY,
        autonomy_level=AutonomyLevel.LEVEL_0_READ_ONLY,
    )
    assert request is None


def test_approval_required_when_exceeding_autonomy():
    request = build_approval_request(
        action="git.push", permission=PermissionLevel.GIT_WRITE,
        autonomy_level=AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES,
        files_affected=["app/main.py"], commands=["git push origin agent/task-1"],
    )
    assert request is not None
    assert request.status == ApprovalStatus.PENDING
    assert request.risk_level == Severity.HIGH
    assert request.files_affected == ["app/main.py"]
    assert request.commands == ["git push origin agent/task-1"]


def test_deployment_always_requires_approval_even_at_max_autonomy():
    request = build_approval_request(
        action="deploy.release", permission=PermissionLevel.DEPLOYMENT,
        autonomy_level=AutonomyLevel.LEVEL_5_FULL_AUTONOMY,
    )
    assert request is not None
    assert request.risk_level == Severity.BLOCKER


def test_default_reason_explains_why_approval_is_needed():
    request = build_approval_request(
        action="terminal.execute", permission=PermissionLevel.EXECUTION,
        autonomy_level=AutonomyLevel.LEVEL_0_READ_ONLY,
    )
    assert "EXECUTION" in request.reason
    assert "LEVEL_0_READ_ONLY" in request.reason
