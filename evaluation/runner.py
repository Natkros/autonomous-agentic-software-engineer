"""The benchmark evaluation runner (spec sections 36-37).

**What "success" means here, and what it does not:** `MockLLMProvider`
(the only provider ever exercised in this environment) cannot produce
real functionality — its patches are deterministic stub functions, not
solutions to the stated problem. So no benchmark task in this harness
measures "did the agent correctly solve the coding task." What it
measures instead is whether `core.orchestration.self_correction`'s
convergence behavior matches what a human would predict for that
scenario: does a safe, non-breaking patch get accepted quickly (Phase 5's
"success" path), and does a genuinely unsolvable scenario correctly
exhaust the iteration budget and report `NEEDS_HUMAN_INTERVENTION` rather
than looping forever or falsely claiming success (Phase 5's other
verified path)? `BenchmarkTaskResult.matched_expectation` is therefore a
regression-style check on the *mechanism*, not a coding-competence score.
Re-read this before quoting a "success rate" from this harness as if it
meant something else.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time

from agents.repository.repository_agent import RepositoryExplorerAgent
from core.orchestration.self_correction import run_self_correction_loop
from core.providers.cost_tracker import estimate_tokens
from core.providers.llm_provider import LLMProvider, MockLLMProvider
from core.state.schemas import SelfCorrectionStatus, Task
from evaluation.schemas import BenchmarkTaskResult, EvaluationReport, ExpectedOutcome

_STATUS_TO_OUTCOME = {
    SelfCorrectionStatus.SUCCESS: ExpectedOutcome.SUCCESS,
    SelfCorrectionStatus.NEEDS_HUMAN_INTERVENTION: ExpectedOutcome.NEEDS_HUMAN_INTERVENTION,
}


class EvaluationRunner:
    def __init__(self, llm_provider: LLMProvider | None = None, max_iterations: int = 5):
        self.llm_provider = llm_provider or MockLLMProvider()
        self.max_iterations = max_iterations

    def run_task(self, task_dir: str) -> BenchmarkTaskResult:
        task_id = os.path.basename(os.path.normpath(task_dir))

        with open(os.path.join(task_dir, "problem_statement.md"), encoding="utf-8") as fh:
            problem_statement = fh.read().strip()
        with open(os.path.join(task_dir, "evaluation_criteria.json"), encoding="utf-8") as fh:
            criteria = json.load(fh)
        expected_outcome = ExpectedOutcome(criteria["expected_status"])

        with tempfile.TemporaryDirectory() as workdir:
            workspace_root = os.path.join(workdir, "repo")
            shutil.copytree(os.path.join(task_dir, "repo"), workspace_root)

            repository_summary = RepositoryExplorerAgent().explore(workspace_root)
            candidate_file = repository_summary.entry_points[0] if repository_summary.entry_points else None
            task = Task(
                id="TASK-EVAL",
                description=problem_statement,
                files=[candidate_file] if candidate_file else [],
            )

            start = time.monotonic()
            result = run_self_correction_loop(
                workspace_root=workspace_root, task=task, repository_summary=repository_summary,
                llm_provider=self.llm_provider, max_iterations=self.max_iterations,
            )
            latency_ms = (time.monotonic() - start) * 1000

        estimated_tokens = estimate_tokens(problem_statement) * result.iterations_used

        return BenchmarkTaskResult(
            task_id=task_id,
            problem_statement=problem_statement,
            expected_outcome=expected_outcome,
            actual_outcome=_STATUS_TO_OUTCOME[result.status],
            iterations_used=result.iterations_used,
            latency_ms=latency_ms,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=0.0,  # MockLLMProvider makes no real API call — see module docstring
        )

    def run_all(self, benchmark_dir: str) -> EvaluationReport:
        task_dirs = sorted(
            os.path.join(benchmark_dir, name)
            for name in os.listdir(benchmark_dir)
            if os.path.isdir(os.path.join(benchmark_dir, name))
        )
        results = [self.run_task(task_dir) for task_dir in task_dirs]
        return EvaluationReport(results=results)
