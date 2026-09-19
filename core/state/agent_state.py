"""The explicit, shared state every agent and the LangGraph orchestrator
reads from and writes to.

Per the project's design rule: no agent may depend on hidden conversational
context. Everything an agent needs to act, and everything it produces, is a
plain, JSON-serializable field on this one object — so the whole pipeline's
progress can be inspected, logged, or resumed from any point.

Implemented as a TypedDict (not a Pydantic model) because LangGraph's
StateGraph expects a mapping type it can shallow-merge between node calls.
Nested values are the `.model_dump()` of the Pydantic schemas in
`schemas.py` — validated once when an agent produces them, then carried as
plain dicts/lists so the state stays trivially serializable.
"""
from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    task_id: str
    repository_path: str
    user_request: str

    requirement_analysis: dict  # RequirementAnalysis.model_dump()
    repository_summary: dict  # RepositorySummary.model_dump()
    plan: list[dict]  # [Task.model_dump(), ...]
    patch_proposals: list[dict]  # [PatchProposal.model_dump(), ...]

    tool_calls: list[dict]  # [ToolCallRecord.model_dump(), ...]
    errors: list[str]
    iterations: int
    final_status: str | None


def new_agent_state(task_id: str, repository_path: str, user_request: str) -> AgentState:
    """Construct a fresh AgentState with every collection field initialized,
    so downstream nodes can always append without checking for `None` first.
    """
    return AgentState(
        task_id=task_id,
        repository_path=repository_path,
        user_request=user_request,
        requirement_analysis={},
        repository_summary={},
        plan=[],
        patch_proposals=[],
        tool_calls=[],
        errors=[],
        iterations=0,
        final_status=None,
    )
