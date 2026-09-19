# Phase 8 Status

Scope per the project roadmap: benchmark tasks, evaluation runner,
success metrics, regression detection, cost tracking.

## Read this before quoting any number from this phase

**`MockLLMProvider` (the only provider ever exercised in this
environment) cannot produce real functionality.** Every "patch" it
generates is a deterministic, valid-but-trivial stub function — it does
not solve the stated problem. That means no benchmark task built in this
phase measures "did the agent correctly solve the coding task," because
nothing in this environment is capable of that yet. What this harness
measures instead is whether `core.orchestration.self_correction`'s
*convergence behavior* matches what should happen for a given scenario
type: does a safe, non-breaking change get accepted quickly, and does a
genuinely unsolvable scenario correctly exhaust its iteration budget and
report `NEEDS_HUMAN_INTERVENTION` rather than looping forever or lying
about success. A "100% success rate" from this harness means "the
mechanism behaved exactly as predicted for both scenario types," not "the
AI solved 100% of the benchmark problems." See `evaluation/runner.py`'s
module docstring — the same warning lives right next to the code.

## Done and verified

- [x] `evaluation/benchmark/` — two real benchmark tasks, each with a
  `problem_statement.md`, `expected_behavior.md`, `evaluation_criteria.json`,
  and a real `repo/` fixture:
  - `task_001_add_health_endpoint` — an additive-only scenario; predicts
    `self_correction` converges to `SUCCESS` on the first iteration
    (nothing about the existing passing test suite gets broken by an
    additive stub).
  - `task_002_impossible_test` — a repo whose test suite asserts `False`
    unconditionally; predicts `self_correction` correctly exhausts its
    iteration budget and reports `NEEDS_HUMAN_INTERVENTION`, the same
    safety property Phase 5 verified directly.
- [x] `evaluation/runner.py` — `EvaluationRunner.run_task()` actually
  copies a task's fixture repo to a fresh temp workspace, builds a
  `RepositorySummary` via the real Phase 3 Repository Explorer Agent, and
  runs the real Phase 5 self-correction loop against it — no part of the
  pipeline is mocked or stubbed for the sake of the benchmark.
  `run_all()` aggregates every task under a benchmark directory into an
  `EvaluationReport`.
- [x] `evaluation/schemas.py` — `BenchmarkTaskResult.matched_expectation`
  (did the actual outcome match what the task predicted) and
  `EvaluationReport.success_rate` (fraction of tasks where it did) are
  both computed properties, never something an LLM asserts.
- [x] `core/providers/cost_tracker.py` — `estimate_tokens()` (a
  documented ~4-chars-per-token heuristic, not a real tokenizer),
  `MODEL_PRICING` (illustrative real per-token pricing for one Claude
  model, current as of when this was written), and `CostTracker`, which
  accumulates real (if estimated) cost/latency/token totals across calls.
  `MockLLMProvider` calls are tracked at exactly $0.00 — not a rounding
  artifact, but because they are not real API calls at all, and assigning
  them a nonzero cost would be actively misleading.
- [x] Test count: `evaluation` (new) 4, `core` grew from 41 to 47.
  **246 tests total** across all seven suites (`code_intelligence` 40,
  `core` 47, `sandbox` 12, `tools` 95, `agents` 28, `evaluation` 4,
  `apps/api` 20), re-verified in clean Python 3.12 venvs matching CI.
- [x] CI now also runs `evaluation`'s suite.

## Explicitly NOT done in Phase 8

- **No benchmark task measures coding correctness.** See the warning at
  the top of this file. A real evaluation of task-solving ability
  requires a real LLM provider (`AnthropicLLMProvider`, unverified in
  this environment) generating real code, plus benchmark tasks with
  actual expected-behavior tests — neither exists yet.
- **Only two benchmark tasks exist**, both designed to exercise the two
  outcomes Phase 5 already proved the loop handles correctly (success and
  bounded give-up). There's no task library covering the ten example
  categories the spec lists (add endpoint, fix failing test, refactor,
  add auth, add DB model, fix vulnerability, improve coverage, add
  validation, update docs, debug production-style error) — those would
  all currently reduce to the same two convergence outcomes given
  `MockLLMProvider`'s limitations, so building ten of them wouldn't
  currently measure anything additional.
- **No regression detection across runs.** `EvaluationReport` is a
  single snapshot; nothing stores previous runs or diffs against them to
  detect a newly-introduced regression, despite that being explicitly in
  this phase's scope.
- **Cost tracking is not wired into the LLM provider or orchestration
  pipeline.** `CostTracker`/`estimate_tokens()` exist as standalone,
  tested utilities; nothing in `core/providers/llm_provider.py` or
  `core/orchestration/graph.py` calls them yet to record real per-call
  costs during a pipeline run.
- **`estimate_tokens()` is a rough heuristic, not a real tokenizer** —
  documented explicitly in the module, since a ~4-char approximation can
  be meaningfully wrong for code (which tokenizes differently than
  prose) or non-English text.

## How to verify this yourself

```bash
cd evaluation && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 4 passed

cd ../core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 47 passed
```

To run the benchmark directly and see the honest framing for yourself:

```python
from core.providers.llm_provider import MockLLMProvider
from evaluation.runner import EvaluationRunner

report = EvaluationRunner(llm_provider=MockLLMProvider()).run_all("evaluation/benchmark")
print(report.success_rate, report.average_iterations, report.total_estimated_cost_usd)
```
