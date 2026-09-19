import pytest

from core.policies.permissions import (
    AutonomyLevel,
    PermissionDeniedError,
    PermissionLevel,
    enforce_permission,
    is_permitted,
    max_permission_for,
    requires_human_approval,
)


def test_read_only_tool_permitted_at_every_autonomy_level():
    for level in AutonomyLevel:
        assert is_permitted(PermissionLevel.READ_ONLY, level) is True


def test_safe_write_requires_at_least_autonomy_level_2():
    assert is_permitted(PermissionLevel.SAFE_WRITE, AutonomyLevel.LEVEL_1_SUGGESTIONS) is False
    assert is_permitted(PermissionLevel.SAFE_WRITE, AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES) is True


def test_deployment_is_never_autonomous_even_at_max_level():
    assert is_permitted(PermissionLevel.DEPLOYMENT, AutonomyLevel.LEVEL_5_FULL_AUTONOMY) is False
    assert requires_human_approval(PermissionLevel.DEPLOYMENT, AutonomyLevel.LEVEL_5_FULL_AUTONOMY) is True


def test_max_permission_for_matches_expected_ceiling():
    assert max_permission_for(AutonomyLevel.LEVEL_0_READ_ONLY) == PermissionLevel.READ_ONLY
    assert max_permission_for(AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR) == PermissionLevel.GIT_WRITE


def test_enforce_permission_raises_when_exceeding_autonomy():
    with pytest.raises(PermissionDeniedError):
        enforce_permission("terminal.execute", PermissionLevel.EXECUTION, AutonomyLevel.LEVEL_0_READ_ONLY)


def test_enforce_permission_passes_when_within_autonomy():
    enforce_permission("filesystem.read", PermissionLevel.READ_ONLY, AutonomyLevel.LEVEL_0_READ_ONLY)
