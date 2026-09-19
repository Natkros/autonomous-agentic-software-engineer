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
    """A proposed code change.

    `content` is optional: Phase 3's CodingAgent originally produced a
    description-only proposal (nothing to apply). As of Phase 5, when
    `content` is present it is real, syntactically valid text that
    `tools/filesystem/patch_tool.py` can actually apply — see
    `core/orchestration/self_correction.py` for the loop that does so.
    """

    task_id: str
    file: str
    operation: PatchOperation
    description: str
    rationale: str
    content: str | None = None


class ToolCallRecord(BaseModel):
    """One audit-log entry for a single tool invocation."""

    tool_name: str
    input_summary: str
    success: bool
    duration_ms: float
    error: str | None = None


class FailureCategory(str, enum.Enum):
    """Per spec section 22 — the Debug Agent classifies a failure into one
    of these before proposing a fix.
    """

    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    IMPORT_ERROR = "import_error"
    LOGIC_ERROR = "logic_error"
    TEST_ERROR = "test_error"
    CONFIG_ERROR = "config_error"
    DEPENDENCY_ERROR = "dependency_error"
    ENVIRONMENT_ERROR = "environment_error"
    TIMEOUT = "timeout"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN = "unknown"


class DebugReport(BaseModel):
    """Output of the Debugger Agent for one failed test run."""

    failure_category: FailureCategory
    root_cause: str
    evidence: str
    proposed_fix: str
    iteration: int = 0


class SelfCorrectionStatus(str, enum.Enum):
    SUCCESS = "success"
    NEEDS_HUMAN_INTERVENTION = "needs_human_intervention"


class SelfCorrectionResult(BaseModel):
    """Output of the bounded test -> debug -> patch -> retest loop
    (spec section 21). `iterations_used` is always <= the loop's
    `max_iterations` cap (5, per spec) — it never runs forever.
    """

    status: SelfCorrectionStatus
    iterations_used: int
    debug_reports: list[DebugReport] = Field(default_factory=list)
    final_test_counts: dict = Field(default_factory=dict)
