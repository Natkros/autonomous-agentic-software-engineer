from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.repository_analysis import AnalysisStatus


class RepositoryAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    status: AnalysisStatus
    summary: dict | None
    error_message: str | None
    created_at: datetime
