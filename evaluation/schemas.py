"""Evaluation-specific schemas. Kept local to `evaluation/` rather than in
`core/state/schemas.py` since nothing outside this package needs them —
`core` shouldn't have to know about the benchmark harness that evaluates it.
"""
from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class ExpectedOutcome(str, enum.Enum):
    """What a benchmark task's `evaluation_criteria.json` predicts the
    self-correction loop will report. See the module docstring in
    `runner.py` for why "success" here means "converged," not "solved the
    task correctly."
    """

    SUCCESS = "success"
    NEEDS_HUMAN_INTERVENTION = "needs_human_intervention"


class BenchmarkTaskResult(BaseModel):
    task_id: str
    problem_statement: str
    expected_outcome: ExpectedOutcome
    actual_outcome: ExpectedOutcome
    iterations_used: int
    latency_ms: float
    estimated_tokens: int
    estimated_cost_usd: float

    @property
    def matched_expectation(self) -> bool:
        return self.actual_outcome == self.expected_outcome


class EvaluationReport(BaseModel):
    results: list[BenchmarkTaskResult] = Field(default_factory=list)

    @property
    def task_count(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        """Fraction of tasks where the system's actual behavior matched
        what the benchmark predicted — a regression-style correctness
        measure for the mechanism, not a "solved the coding task" rate.
        """
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.matched_expectation) / len(self.results)

    @property
    def average_iterations(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.iterations_used for r in self.results) / len(self.results)

    @property
    def total_estimated_cost_usd(self) -> float:
        return sum(r.estimated_cost_usd for r in self.results)

    @property
    def total_latency_ms(self) -> float:
        return sum(r.latency_ms for r in self.results)
