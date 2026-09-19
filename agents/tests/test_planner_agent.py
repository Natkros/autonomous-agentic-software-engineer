import pytest

from agents.planner.planner_agent import PlanningAgent
from core.providers.llm_provider import MockLLMProvider
from core.state.schemas import Plan, RepositorySummary, RequirementAnalysis


def _requirement_analysis():
    return RequirementAnalysis(
        task="Add authentication",
        requirements=["Add login endpoint", "Add password hashing"],
        constraints=["Do not break existing tests"],
        acceptance_criteria=["Tests pass"],
    )


def _repository_summary():
    return RepositorySummary(
        root="/tmp/repo", file_count=10, frameworks=["FastAPI"], key_files=["app/main.py"],
    )


def test_planner_produces_one_task_per_requirement():
    agent = PlanningAgent(MockLLMProvider())
    plan = agent.plan(_requirement_analysis(), _repository_summary())

    assert isinstance(plan, Plan)
    assert len(plan.tasks) == 2
    assert plan.has_valid_dependencies()


def test_planner_chains_task_dependencies_in_order():
    agent = PlanningAgent(MockLLMProvider())
    plan = agent.plan(_requirement_analysis(), _repository_summary())

    assert plan.tasks[0].dependencies == []
    assert plan.tasks[1].dependencies == [plan.tasks[0].id]
