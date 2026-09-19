import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskRunStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task(Base):
    """One run of the Phase 3 agent pipeline (Requirement -> Repository ->
    Planner -> Coder) against a repository. Runs synchronously on the
    request thread today — a background job queue is Phase 4 scope.
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(String(36), ForeignKey("repositories.id"), nullable=False, index=True)
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskRunStatus] = mapped_column(Enum(TaskRunStatus), nullable=False)
    requirement_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    repository_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    plan: Mapped[list | None] = mapped_column(JSON, nullable=True)
    patch_proposals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    autonomy_level: Mapped[int] = mapped_column(default=1, nullable=False)
    review_results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    correction_results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    security_scan_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_requests: Mapped[list | None] = mapped_column(JSON, nullable=True)
    git_commit: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
