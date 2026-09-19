# Phase 3 Status

Scope per the project roadmap: `AgentState`, tool framework, LLM provider
abstraction, LangGraph, planner, repository agent, coding agent.

## Done and verified

- [x] `core/state/schemas.py` + `core/state/agent_state.py` — every agent
      artifact (`RequirementAnalysis`, `RepositorySummary`, `Task`, `Plan`,
      `PatchProposal`, `ToolCallRecord`) is a validated Pydantic model; the
      shared `AgentState` is an explicit, JSON-serializable `TypedDict` —
      no agent depends on hidden conversational context.
- [x] `core/providers/llm_provider.py` — an `LLMProvider` abstraction with
      `MockLLMProvider` (deterministic, rule-based, offline — genuinely
      derives its output from its input via sentence-splitting/keyword
      heuristics, not hardcoded) and `AnthropicLLMProvider` (real code
      against the Messages API using tool-use to force schema-shaped JSON;
      **not exercised** — no network/API key in this environment).
- [x] `core/policies/permissions.py` — the five-tier `PermissionLevel`
      system (READ_ONLY/SAFE_WRITE/EXECUTION/GIT_WRITE/DEPLOYMENT) and six
      `AutonomyLevel`s (0-5), with `DEPLOYMENT` always requiring human
      approval regardless of autonomy level.
- [x] `tools/base.py` — the controlled `Tool` interface: every call is
      permission-checked before it runs, timed, and recorded to an
      `AuditLog` win or lose. Three real, working, READ_ONLY tools wrap
      Phase 2's `code_intelligence`: `repository.analyze`, `code.search`,
      `symbol.search`.
- [x] Four agents, each with a single clear responsibility:
  - `RequirementAnalystAgent` — natural language -> validated `RequirementAnalysis`.
  - `RepositoryExplorerAgent` — wraps the Phase 2 scanner (no LLM call needed; deterministic facts don't need one).
  - `PlanningAgent` — requirements + repo summary -> a validated task DAG (`Plan`), rejecting any plan with a dependency on a nonexistent task id.
  - `CodingAgent` — proposes a single patch per task. **Proposal only** — nothing is written to disk (that needs Phase 4's sandboxed filesystem tools).
- [x] `core/orchestration/graph.py` — a real, compiled **LangGraph**
      `StateGraph` wiring all four agents: `requirement -> repository ->
      planner -> coder -> END`. Each node catches its own failures into
      `state["errors"]` instead of crashing the run.
- [x] **This is the first phase where the project's stated architecture —
      an explicit state object flowing through a graph of specialized
      agents, instead of one raw `USER -> LLM -> CODE` call — is running
      code**, not just a diagram. Verified with a full pipeline run against
      a real scanned repository (`core/tests/test_orchestration_graph.py`).
- [x] **API integration**: `POST /api/tasks` clones the repository (same
      pattern as `/analyze`) and runs the full pipeline against it,
      storing the result in a new `tasks` table; `GET /api/tasks/{id}`
      retrieves it. Verified end-to-end against a real cloned fixture repo.
- [x] Test count: `code_intelligence` 40, `core` 24, `tools` 12, `agents` 9,
      `apps/api` 20 — **105 tests total**, all run in this session.
- [x] CI now runs all five suites (`code-intelligence`, `core`, `tools`,
      `agents`, `backend`) plus the frontend build, one job each.

## Explicitly NOT done in Phase 3

- **No real LLM has ever been called.** `MockLLMProvider` is real,
  deterministic, heuristic logic — not a trained model. It does not
  understand language. Every "requirement," "plan," and "patch proposal"
  produced by the test suite and by `/api/tasks` in this environment is a
  heuristic derivation, not an LLM's reasoning. `AnthropicLLMProvider` is
  real, complete code that has simply never been run (no network/API key
  here). Do not judge plan/patch *quality* from this phase — judge whether
  the pipeline's plumbing (state, validation, orchestration, permissions)
  is correct, because that's what was actually exercised.
- **Coding Agent proposals are never applied.** There is no filesystem
  write tool yet. A `PatchProposal` names a file and describes an intended
  change; nothing modifies that file. Patch application, testing, and
  debugging are Phase 4-5.
- **No architecture/test/debug/review/security/documentation/validator
  agents yet.** Only Requirement, Repository, Planner, and Coder exist.
  The other seven agent directories under `agents/` remain empty
  placeholders.
- **No background job queue.** `/api/tasks` runs the full pipeline
  synchronously on the request thread, same limitation as `/analyze`.
- **`core`/`agents`/`tools` are not packaged as installable dependencies.**
  Same `sys.path` bootstrap simplification as Phase 2's
  `analysis_service.py` — see `apps/api/app/services/task_service.py`.
- **The coder node caps patch proposals at 5 tasks per run**
  (`MAX_TASKS_TO_PROPOSE` in `core/orchestration/graph.py`) to bound LLM
  calls per request. There is no real cost/iteration budget system yet
  (that's Phase 8, Evaluation).
- **No self-correction loop.** The pipeline runs once, straight through.
  The retry/debug loop (max 5 iterations, per the project's own rule) is
  Phase 5.

## How to verify this yourself

```bash
# core (AgentState, LLM provider, permissions, orchestration graph)
cd core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 24 passed

# tools (permissioned tool framework + real search tools)
cd ../tools && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 12 passed

# agents (Requirement, Repository, Planner, Coder)
cd ../agents && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 9 passed

# apps/api (now includes POST/GET /api/tasks)
cd ../apps/api && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 20 passed
```

All four suites were run in this session on Windows with Python 3.14.7 and
LangGraph 1.2.11.
