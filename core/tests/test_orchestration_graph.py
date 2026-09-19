import os

from core.orchestration.graph import run_pipeline
from core.providers.llm_provider import MockLLMProvider

FIXTURE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "code_intelligence", "tests", "fixtures", "sample_repo",
))


def test_full_pipeline_runs_end_to_end_against_a_real_repository():
    """This is the Phase 3 milestone: USER -> Requirement -> Repository ->
    Planner -> Coder, running as an actual LangGraph pipeline over a real
    scanned repository, with no mocked internals except the LLM calls
    themselves (MockLLMProvider — deterministic, not a stubbed-out no-op).
    """
    final_state = run_pipeline(
        user_request="Add a health check endpoint. Do not break existing routes.",
        repository_path=FIXTURE_ROOT,
        llm_provider=MockLLMProvider(),
    )

    assert final_state["final_status"] == "COMPLETED"
    assert final_state["errors"] == []

    assert final_state["requirement_analysis"]["task"] == "Add a health check endpoint."

    repo_summary = final_state["repository_summary"]
    assert repo_summary["file_count"] > 0
    assert "FastAPI" in repo_summary["frameworks"]

    assert len(final_state["plan"]) >= 1
    assert len(final_state["patch_proposals"]) >= 1
    assert final_state["patch_proposals"][0]["task_id"] == final_state["plan"][0]["id"]


def test_pipeline_records_error_for_nonexistent_repository_path():
    final_state = run_pipeline(
        user_request="Add a feature",
        repository_path="/path/does/not/exist",
        llm_provider=MockLLMProvider(),
    )
    assert final_state["final_status"] == "FAILED"
    assert any("repository_node" in e for e in final_state["errors"])
    # Downstream nodes should degrade gracefully, not crash the whole run.
    assert final_state["plan"] == []


def test_pipeline_is_deterministic_with_the_mock_provider():
    kwargs = dict(
        user_request="Add pagination to the users API.",
        repository_path=FIXTURE_ROOT,
        llm_provider=MockLLMProvider(),
    )
    first = run_pipeline(**kwargs)
    second = run_pipeline(**kwargs)
    assert first["plan"] == second["plan"]
    assert first["patch_proposals"] == second["patch_proposals"]
