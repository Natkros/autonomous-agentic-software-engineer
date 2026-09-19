from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskRunStatus


class TaskCreate(BaseModel):
    repository_id: str
    user_request: str = Field(min_length=1, max_length=4000)
    # AutonomyLevel.value (core/policies/permissions.py). Defaults to
    # LEVEL_1_SUGGESTIONS — patches are proposed only, nothing is written
    # to the repository — so a caller who omits this gets the conservative
    # behavior. Raise to 2+ to let the execution node actually apply,
    # test, and (at 4+) commit approved patches.
    autonomy_level: int = Field(default=1, ge=0, le=5)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    user_request: str
    status: TaskRunStatus
    autonomy_level: int
    requirement_analysis: dict | None
    repository_summary: dict | None
    plan: list | None
    patch_proposals: list | None
    review_results: list | None
    correction_results: list | None
    security_scan_result: dict | None
    approval_requests: list | None
    git_commit: dict | None
    execution_status: str | None
    errors: list | None
    created_at: datetime
