"""Tool permission levels and autonomy-level gating.

Implements the two related concepts from the project's design (sections 28
and 56 of the spec): every tool declares a minimum ``PermissionLevel`` it
needs, and every run declares a maximum ``AutonomyLevel`` it's allowed to
operate at. A tool call is only allowed to execute without stopping for a
human if its required permission is within what the current autonomy level
grants; DEPLOYMENT-level actions always require human approval regardless
of autonomy level, per the project's human-in-the-loop requirement.
"""
from __future__ import annotations

import enum


class PermissionLevel(enum.IntEnum):
    READ_ONLY = 0
    SAFE_WRITE = 1
    EXECUTION = 2
    GIT_WRITE = 3
    DEPLOYMENT = 4


class AutonomyLevel(enum.IntEnum):
    LEVEL_0_READ_ONLY = 0
    LEVEL_1_SUGGESTIONS = 1
    LEVEL_2_AUTO_CODE_CHANGES = 2
    LEVEL_3_AUTO_TEST_AND_DEBUG = 3
    LEVEL_4_AUTO_BRANCH_AND_PR = 4
    LEVEL_5_FULL_AUTONOMY = 5


# The highest PermissionLevel a given AutonomyLevel is allowed to exercise
# without stopping for human approval. Level 1 ("code suggestions") is
# still READ_ONLY: an agent may *propose* a patch, but nothing may write it
# to disk until autonomy reaches level 2.
_AUTONOMY_MAX_PERMISSION: dict[AutonomyLevel, PermissionLevel] = {
    AutonomyLevel.LEVEL_0_READ_ONLY: PermissionLevel.READ_ONLY,
    AutonomyLevel.LEVEL_1_SUGGESTIONS: PermissionLevel.READ_ONLY,
    AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES: PermissionLevel.SAFE_WRITE,
    AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG: PermissionLevel.EXECUTION,
    AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR: PermissionLevel.GIT_WRITE,
    AutonomyLevel.LEVEL_5_FULL_AUTONOMY: PermissionLevel.DEPLOYMENT,
}


class PermissionDeniedError(PermissionError):
    pass


def max_permission_for(autonomy_level: AutonomyLevel) -> PermissionLevel:
    return _AUTONOMY_MAX_PERMISSION[autonomy_level]


def is_permitted(tool_permission: PermissionLevel, autonomy_level: AutonomyLevel) -> bool:
    """Whether a tool at ``tool_permission`` may run autonomously (without
    human approval) at ``autonomy_level``. DEPLOYMENT is never autonomous.
    """
    if tool_permission is PermissionLevel.DEPLOYMENT:
        return False
    return tool_permission <= max_permission_for(autonomy_level)


def requires_human_approval(tool_permission: PermissionLevel, autonomy_level: AutonomyLevel) -> bool:
    return not is_permitted(tool_permission, autonomy_level)


def enforce_permission(tool_name: str, tool_permission: PermissionLevel, autonomy_level: AutonomyLevel) -> None:
    """Raise PermissionDeniedError if the tool may not run autonomously at
    this autonomy level. Callers (the tool framework) call this before
    executing a tool; a False result means "route to human approval," not
    "silently skip."
    """
    if requires_human_approval(tool_permission, autonomy_level):
        raise PermissionDeniedError(
            f"Tool '{tool_name}' requires permission {tool_permission.name}, which exceeds what "
            f"autonomy level {autonomy_level.name} ({max_permission_for(autonomy_level).name} max) "
            f"allows without human approval."
        )
