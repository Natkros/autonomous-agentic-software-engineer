"""Pydantic schemas for every structured artifact agents produce.

Per the project's design rule that no LLM (or heuristic) output is trusted
without schema validation: every agent in this phase returns one of these
models, never a raw string or dict. `AgentState` (see `agent_state.py`)
stores them in their plain-dict form so the whole pipeline state stays
JSON-serializable and inspectable — never hidden in conversational memory.
"""
from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class RequirementAnalysis(BaseModel):
    """Output of the Requirement Analyst Agent."""

    task: str
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class RepositorySummary(BaseModel):
    """Output of the Repository Explorer Agent — a distillation of a
    code_intelligence RepositoryIndex into what the planner actually needs.
    """

    root: str
    file_count: int
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    test_file_count: int = 0
    symbol_count: int = 0
    key_files: list[str] = Field(default_factory=list)
    readme_summary: str | None = None


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    risk: RiskLevel = RiskLevel.MEDIUM
    status: TaskStatus = TaskStatus.PENDING


class Plan(BaseModel):
    tasks: list[Task] = Field(default_factory=list)

    def task_ids(self) -> set[str]:
        return {t.id for t in self.tasks}

    def has_valid_dependencies(self) -> bool:
        ids = self.task_ids()
        return all(dep in ids for task in self.tasks for dep in task.dependencies)


class PatchOperation(str, enum.Enum):
    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"
    CREATE_FILE = "create_file"


class PatchProposal(BaseModel):
    """A proposed code change. This is a PROPOSAL ONLY — nothing in Phase 3
    applies it to disk. Applying patches requires the sandboxed filesystem
    tools built in Phase 4.
    """

    task_id: str
    file: str
    operation: PatchOperation
    description: str
    rationale: str


class ToolCallRecord(BaseModel):
    """One audit-log entry for a single tool invocation."""

    tool_name: str
    input_summary: str
    success: bool
    duration_ms: float
    error: str | None = None
