"""LangGraph wiring for the full pipeline:

    USER
      -> Requirement Analyst Agent
      -> Repository Explorer Agent
      -> Planning Agent
      -> Coding Agent           (proposes patches)
      -> Execution node          (review -> self-correct -> security scan
                                   -> commit, each gated by autonomy level)

This is the first phase where the project's stated architecture
(explicit AgentState flowing through a graph of specialized agents,
instead of one raw LLM call) actually exists as running code end to end:
earlier phases proved every stage below in isolation (self-correction in
Phase 5, review/security in Phase 6, git automation in Phase 7) but never
called them from this graph — `execution_node` is what actually wires
them together.

Every node catches its own agent's exceptions and appends a message to
`state["errors"]` rather than raising — a single failing task must not
crash the whole pipeline run, matching the project's "never expose a raw
stack trace" error-handling rule.

Nothing here does anything an operator didn't authorize: every write,
test run, and commit is gated by the same `AutonomyLevel` /
`PermissionLevel` system every tool already enforces (see
`core/policies/permissions.py`). At the conservative default
(`LEVEL_1_SUGGESTIONS`), this graph behaves exactly as it did before this
node existed — patches are proposed, nothing is written.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.coder.coding_agent import CodingAgent
from agents.planner.planner_agent import PlanInvalidError, PlanningAgent
from agents.repository.repository_agent import RepositoryExplorerAgent
from agents.requirement.requirement_agent import RequirementAnalystAgent
from agents.reviewer.review_agent import CodeReviewAgent
from agents.security.security_agent import SecurityAgent, SecurityScanError
from core.orchestration.self_correction import run_self_correction_loop
from core.policies.approval import build_approval_request
from core.policies.permissions import AutonomyLevel, PermissionLevel
from core.providers.llm_provider import LLMProvider, get_default_llm_provider
from core.state.agent_state import AgentState, new_agent_state
from core.state.schemas import (
    PatchProposal,
    Plan,
    RepositorySummary,
    RequirementAnalysis,
    Task,
)
from tools.base import AuditLog
from tools.git.git_write_tools import GitCommitTool

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
    review_agent = CodeReviewAgent()
    security_agent = SecurityAgent()

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

    def execution_node(state: AgentState) -> dict:
        """Review every proposed patch, apply and test the approved ones
        through the Phase 5 self-correction loop, run a whole-workspace
        security scan as a finalization gate, and commit if the active
        autonomy level allows it — each step gated by
        `core.policies.permissions`/`core.policies.approval`, never by an
        LLM's own judgment.
        """
        autonomy_level = AutonomyLevel(state.get("autonomy_level", AutonomyLevel.LEVEL_1_SUGGESTIONS.value))
        proposals = state.get("patch_proposals") or []
        errors = list(state.get("errors", []))

        if not proposals:
            return {"execution_status": "NO_PATCHES_PROPOSED"}

        # Step 1: review every proposal's actual diff content before anything
        # is applied (spec section 24 — "review only the diff").
        review_results = []
        approved_task_ids = []
        for proposal_dict in proposals:
            proposal = PatchProposal.model_validate(proposal_dict)
            review = review_agent.review(proposal)
            review_results.append({"task_id": proposal.task_id, **review.model_dump()})
            if review.approved:
                approved_task_ids.append(proposal.task_id)
            else:
                errors.append(f"execution_node[{proposal.task_id}]: blocked by code review")

        if not approved_task_ids:
            return {
                "review_results": review_results, "errors": errors,
                "execution_status": "BLOCKED_BY_REVIEW",
            }

        # Step 2: applying anything to disk needs at least SAFE_WRITE. Below
        # that, stop here — the proposals above are exactly what a human
        # would see to approve manually.
        write_approval = build_approval_request(
            action="apply_agent_generated_patches",
            permission=PermissionLevel.SAFE_WRITE,
            autonomy_level=autonomy_level,
            files_affected=[p["file"] for p in proposals],
            reason="Applying agent-generated patches to the repository working tree.",
        )
        if write_approval is not None:
            return {
                "review_results": review_results,
                "approval_requests": [write_approval.model_dump()],
                "errors": errors,
                "execution_status": "AWAITING_APPROVAL",
            }

        # Step 3: apply + test + retry each approved task's patch for real,
        # through the same bounded loop Phase 5 verified never runs forever.
        repository_summary = RepositorySummary.model_validate(state["repository_summary"])
        plan_tasks = {t["id"]: Task.model_validate(t) for t in state.get("plan", [])}
        correction_results = []
        for task_id in approved_task_ids:
            task = plan_tasks.get(task_id)
            if task is None:
                continue
            try:
                result = run_self_correction_loop(
                    workspace_root=state["repository_path"], task=task,
                    repository_summary=repository_summary, llm_provider=provider,
                    autonomy_level=autonomy_level,
                )
                correction_results.append({"task_id": task_id, **result.model_dump()})
            except Exception as exc:
                errors.append(f"execution_node[{task_id}]: self-correction failed: {exc}")

        # Step 4: a whole-workspace security scan is the finalization gate,
        # independent of the per-patch review above (spec section 25).
        security_scan_result = None
        try:
            security_scan_result = security_agent.scan(state["repository_path"])
        except SecurityScanError as exc:
            errors.append(f"execution_node: security scan failed: {exc}")

        if security_scan_result is not None and security_scan_result.blocks_finalization:
            return {
                "review_results": review_results,
                "correction_results": correction_results,
                "security_scan_result": security_scan_result.model_dump(),
                "errors": errors,
                "execution_status": "BLOCKED_BY_SECURITY",
            }

        # Step 5: commit only if autonomy allows GIT_WRITE; otherwise hand
        # back a structured approval request instead of committing silently.
        git_approval = build_approval_request(
            action="commit_agent_applied_changes",
            permission=PermissionLevel.GIT_WRITE,
            autonomy_level=autonomy_level,
            reason="Committing changes the self-correction loop already applied and tested.",
        )
        git_commit = None
        approval_requests = []
        if git_approval is not None:
            approval_requests.append(git_approval.model_dump())
        else:
            commit_result = GitCommitTool().run(
                AuditLog(), autonomy_level,
                repository_path=state["repository_path"],
                message=f"ForgeAI: {state.get('user_request', 'agent-applied change')[:72]}",
            )
            if commit_result.success:
                git_commit = commit_result.output
            else:
                errors.append(f"execution_node: git commit failed: {commit_result.error}")

        return {
            "review_results": review_results,
            "correction_results": correction_results,
            "security_scan_result": security_scan_result.model_dump() if security_scan_result else None,
            "approval_requests": approval_requests,
            "git_commit": git_commit,
            "errors": errors,
            "execution_status": "COMPLETED",
        }

    graph = StateGraph(AgentState)
    graph.add_node("requirement", requirement_node)
    graph.add_node("repository", repository_node)
    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("execution", execution_node)

    graph.set_entry_point("requirement")
    graph.add_edge("requirement", "repository")
    graph.add_edge("repository", "planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "execution")
    graph.add_edge("execution", END)

    return graph.compile()


def run_pipeline(
    user_request: str,
    repository_path: str,
    task_id: str = "TASK-RUN-001",
    llm_provider: LLMProvider | None = None,
    autonomy_level: AutonomyLevel = AutonomyLevel.LEVEL_1_SUGGESTIONS,
) -> AgentState:
    app = build_pipeline_graph(llm_provider)
    initial_state = new_agent_state(
        task_id=task_id, repository_path=repository_path, user_request=user_request,
        autonomy_level=autonomy_level.value,
    )
    final_state = app.invoke(initial_state)
    final_state["final_status"] = "FAILED" if final_state.get("errors") else "COMPLETED"
    return final_state
