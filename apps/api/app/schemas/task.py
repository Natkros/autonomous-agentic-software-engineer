from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskRunStatus


class TaskCreate(BaseModel):
    repository_id: str
    user_request: str = Field(min_length=1, max_length=4000)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    user_request: str
    status: TaskRunStatus
    requirement_analysis: dict | None
    repository_summary: dict | None
    plan: list | None
    patch_proposals: list | None
    errors: list | None
    created_at: datetime
