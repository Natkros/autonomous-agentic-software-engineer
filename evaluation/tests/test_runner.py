import os

from core.providers.llm_provider import MockLLMProvider
from evaluation.runner import EvaluationRunner
from evaluation.schemas import ExpectedOutcome

BENCHMARK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "benchmark"))
TASK_001 = os.path.join(BENCHMARK_ROOT, "task_001_add_health_endpoint")
TASK_002 = os.path.join(BENCHMARK_ROOT, "task_002_impossible_test")


def test_task_001_converges_to_success_matching_its_prediction():
    result = EvaluationRunner(llm_provider=MockLLMProvider()).run_task(TASK_001)

    assert result.task_id == "task_001_add_health_endpoint"
    assert result.expected_outcome == ExpectedOutcome.SUCCESS
    assert result.actual_outcome == ExpectedOutcome.SUCCESS
    assert result.matched_expectation is True
    assert result.iterations_used == 1
    assert result.estimated_cost_usd == 0.0  # MockLLMProvider makes no real API call


def test_task_002_correctly_exhausts_budget_matching_its_prediction():
    result = EvaluationRunner(llm_provider=MockLLMProvider(), max_iterations=2).run_task(TASK_002)

    assert result.expected_outcome == ExpectedOutcome.NEEDS_HUMAN_INTERVENTION
    assert result.actual_outcome == ExpectedOutcome.NEEDS_HUMAN_INTERVENTION
    assert result.matched_expectation is True
    assert result.iterations_used == 2


def test_run_all_aggregates_both_tasks_into_a_report():
    report = EvaluationRunner(llm_provider=MockLLMProvider(), max_iterations=2).run_all(BENCHMARK_ROOT)

    assert report.task_count == 2
    assert report.success_rate == 1.0  # both tasks' ACTUAL behavior matched their PREDICTED behavior
    assert report.average_iterations > 0
    assert report.total_estimated_cost_usd == 0.0


def test_report_success_rate_reflects_mismatches_not_task_correctness():
    """If a task's criteria predicted the wrong thing, matched_expectation
    is False even though the mechanism itself behaved correctly — this
    proves the metric measures prediction-vs-reality, not some notion of
    the agent 'passing' or 'failing' the coding task itself.
    """
    from evaluation.schemas import BenchmarkTaskResult, EvaluationReport

    report = EvaluationReport(results=[
        BenchmarkTaskResult(
            task_id="fake", problem_statement="x", expected_outcome=ExpectedOutcome.NEEDS_HUMAN_INTERVENTION,
            actual_outcome=ExpectedOutcome.SUCCESS, iterations_used=1, latency_ms=1.0,
            estimated_tokens=1, estimated_cost_usd=0.0,
        )
    ])
    assert report.success_rate == 0.0
