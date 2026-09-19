"""LangGraph wiring for the Phase 3 pipeline:

    USER
      -> Requirement Analyst Agent
      -> Repository Explorer Agent
      -> Planning Agent
      -> Coding Agent (proposes patches only; nothing is applied)

This is the first phase where the project's stated architecture
(explicit AgentState flowing through a graph of specialized agents,
instead of one raw LLM call) actually exists as running code. Testing,
debugging, review, security scanning, and git automation are later
phases — this graph stops at "here is a plan and some proposed patches,"
which is exactly the Phase 3 scope.

Every node catches its own agent's exceptions and appends a message to
`state["errors"]` rather than raising — a single failing task must not
crash the whole pipeline run, matching the project's "never expose a raw
stack trace" error-handling rule.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.coder.coding_agent import CodingAgent
from agents.planner.planner_agent import PlanInvalidError, PlanningAgent
from agents.repository.repository_agent import RepositoryExplorerAgent
from agents.requirement.requirement_agent import RequirementAnalystAgent
from core.providers.llm_provider import LLMProvider, get_default_llm_provider
from core.state.agent_state import AgentState, new_agent_state
from core.state.schemas import Plan, RepositorySummary, RequirementAnalysis, Task

# Phase 3 demo/safety cap: propose patches for at most this many tasks per
# run, so a large plan doesn't turn into dozens of LLM calls unbounded.
# Revisit once there's a real cost/iteration budget (Phase 8).
MAX_TASKS_TO_PROPOSE = 5


def build_pipeline_graph(llm_provider: LLMProvider | None = None):
    provider = llm_provider or get_default_llm_provider()

    requirement_agent = RequirementAnalystAgent(provider)
    repository_agent = RepositoryExplorerAgent()
    planning_agent = PlanningAgent(provider)
    coding_agent = CodingAgent(provider)

    def requirement_node(state: AgentState) -> dict:
        try:
            analysis = requirement_agent.analyze(state["user_request"])
            return {"requirement_analysis": analysis.model_dump()}
        except Exception as exc:
            return {"errors": [*state.get("errors", []), f"requirement_node: {exc}"]}

    def repository_node(state: AgentState) -> dict:
        try:
            summary = repository_agent.explore(state["repository_path"])
            return {"repository_summary": summary.model_dump()}
        except Exception as exc:
            return {"errors": [*state.get("errors", []), f"repository_node: {exc}"]}

    def planner_node(state: AgentState) -> dict:
        if not state.get("requirement_analysis") or not state.get("repository_summary"):
            return {"errors": [*state.get("errors", []), "planner_node: missing upstream requirement_analysis or repository_summary"]}
        try:
            requirement_analysis = RequirementAnalysis.model_validate(state["requirement_analysis"])
            repository_summary = RepositorySummary.model_validate(state["repository_summary"])
            plan = planning_agent.plan(requirement_analysis, repository_summary)
            return {"plan": [t.model_dump() for t in plan.tasks]}
        except PlanInvalidError as exc:
            return {"errors": [*state.get("errors", []), f"planner_node: {exc}"]}
        except Exception as exc:
            return {"errors": [*state.get("errors", []), f"planner_node: {exc}"]}

    def coder_node(state: AgentState) -> dict:
        plan_tasks = state.get("plan") or []
        if not plan_tasks:
            return {"errors": [*state.get("errors", []), "coder_node: no plan to propose patches for"]}
        try:
            repository_summary = RepositorySummary.model_validate(state["repository_summary"])
            proposals = []
            errors = list(state.get("errors", []))
            for task_dict in plan_tasks[:MAX_TASKS_TO_PROPOSE]:
                task = Task.model_validate(task_dict)
                try:
                    proposal = coding_agent.propose_patch(task, repository_summary)
                    proposals.append(proposal.model_dump())
                except Exception as exc:
                    errors.append(f"coder_node[{task.id}]: {exc}")
            return {"patch_proposals": proposals, "errors": errors}
        except Exception as exc:
            return {"errors": [*state.get("errors", []), f"coder_node: {exc}"]}

    graph = StateGraph(AgentState)
    graph.add_node("requirement", requirement_node)
    graph.add_node("repository", repository_node)
    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)

    graph.set_entry_point("requirement")
    graph.add_edge("requirement", "repository")
    graph.add_edge("repository", "planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", END)

    return graph.compile()


def run_pipeline(
    user_request: str,
    repository_path: str,
    task_id: str = "TASK-RUN-001",
    llm_provider: LLMProvider | None = None,
) -> AgentState:
    app = build_pipeline_graph(llm_provider)
    initial_state = new_agent_state(task_id=task_id, repository_path=repository_path, user_request=user_request)
    final_state = app.invoke(initial_state)
    final_state["final_status"] = "FAILED" if final_state.get("errors") else "COMPLETED"
    return final_state
