"""Integration tests for the bounded self-correction loop, run against
real repositories on disk with the real filesystem/test-execution tools —
no step in the loop is mocked except the LLM layer itself.
"""
import os
import shutil
import tempfile

from core.orchestration.self_correction import run_self_correction_loop
from core.providers.llm_provider import MockLLMProvider
from core.state.schemas import RepositorySummary, SelfCorrectionStatus, Task

FIXTURE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "code_intelligence", "tests", "fixtures", "sample_repo",
))


def test_succeeds_on_first_iteration_when_patch_does_not_break_existing_tests():
    with tempfile.TemporaryDirectory() as workdir:
        workspace_root = os.path.join(workdir, "repo")
        shutil.copytree(FIXTURE_ROOT, workspace_root)

        task = Task(id="TASK-001", description="Add a health check endpoint", files=["app/main.py"])
        summary = RepositorySummary(root=workspace_root, file_count=1, frameworks=["FastAPI"])

        result = run_self_correction_loop(
            workspace_root=workspace_root, task=task, repository_summary=summary,
            llm_provider=MockLLMProvider(), max_iterations=5, test_path="tests",
        )

        assert result.status == SelfCorrectionStatus.SUCCESS
        assert result.iterations_used == 1
        assert result.debug_reports == []
        assert result.final_test_counts.get("failed", 0) == 0

        with open(os.path.join(workspace_root, "app", "main.py")) as fh:
            assert "def handle_" in fh.read()


def test_exhausts_max_iterations_and_reports_needs_human_intervention_when_nothing_can_pass():
    with tempfile.TemporaryDirectory() as workspace_root:
        with open(os.path.join(workspace_root, "app.py"), "w") as fh:
            fh.write("x = 1\n")
        with open(os.path.join(workspace_root, "test_always_fails.py"), "w") as fh:
            fh.write("def test_always_fails():\n    assert False, 'this can never pass'\n")

        task = Task(id="TASK-001", description="Add a feature", files=["app.py"])
        summary = RepositorySummary(root=workspace_root, file_count=2)

        result = run_self_correction_loop(
            workspace_root=workspace_root, task=task, repository_summary=summary,
            llm_provider=MockLLMProvider(), max_iterations=2,
        )

        assert result.status == SelfCorrectionStatus.NEEDS_HUMAN_INTERVENTION
        assert result.iterations_used == 2
        assert len(result.debug_reports) == 2
        assert all(r.failure_category.value == "test_error" for r in result.debug_reports)
        assert all(r.iteration == i + 1 for i, r in enumerate(result.debug_reports))


def test_never_exceeds_the_configured_iteration_cap():
    """The loop must be bounded no matter what — this is the safety
    property the spec cares most about (never run forever)."""
    with tempfile.TemporaryDirectory() as workspace_root:
        with open(os.path.join(workspace_root, "app.py"), "w") as fh:
            fh.write("x = 1\n")
        with open(os.path.join(workspace_root, "test_always_fails.py"), "w") as fh:
            fh.write("def test_always_fails():\n    assert False\n")

        task = Task(id="TASK-001", description="Add a feature", files=["app.py"])
        summary = RepositorySummary(root=workspace_root, file_count=2)

        result = run_self_correction_loop(
            workspace_root=workspace_root, task=task, repository_summary=summary,
            llm_provider=MockLLMProvider(), max_iterations=1,
        )

        assert result.iterations_used == 1
        assert result.status == SelfCorrectionStatus.NEEDS_HUMAN_INTERVENTION
