from core.state.agent_state import new_agent_state
from core.state.schemas import Plan, PatchOperation, PatchProposal, RepositorySummary, RequirementAnalysis, RiskLevel, Task, TaskStatus


def test_new_agent_state_initializes_every_collection_field():
    state = new_agent_state(task_id="T-1", repository_path="/tmp/repo", user_request="do the thing")
    assert state["task_id"] == "T-1"
    assert state["requirement_analysis"] == {}
    assert state["plan"] == []
    assert state["patch_proposals"] == []
    assert state["tool_calls"] == []
    assert state["errors"] == []
    assert state["final_status"] is None


def test_requirement_analysis_schema_round_trips():
    analysis = RequirementAnalysis(
        task="Add auth", requirements=["login", "logout"], constraints=["no breaking changes"],
        acceptance_criteria=["tests pass"], ambiguities=[],
    )
    restored = RequirementAnalysis.model_validate(analysis.model_dump())
    assert restored == analysis


def test_plan_detects_invalid_dependencies():
    plan = Plan(tasks=[Task(id="A", description="first", dependencies=["DOES-NOT-EXIST"])])
    assert plan.has_valid_dependencies() is False


def test_plan_accepts_valid_dependency_chain():
    plan = Plan(tasks=[
        Task(id="A", description="first"),
        Task(id="B", description="second", dependencies=["A"]),
    ])
    assert plan.has_valid_dependencies() is True


def test_patch_proposal_requires_valid_operation_enum():
    proposal = PatchProposal(
        task_id="A", file="app/main.py", operation=PatchOperation.REPLACE,
        description="add a route", rationale="requested by task A",
    )
    assert proposal.operation == PatchOperation.REPLACE


def test_repository_summary_defaults():
    summary = RepositorySummary(root="/tmp/repo", file_count=3)
    assert summary.languages == []
    assert summary.frameworks == []


def test_task_default_status_and_risk():
    task = Task(id="A", description="do something")
    assert task.status == TaskStatus.PENDING
    assert task.risk == RiskLevel.MEDIUM
