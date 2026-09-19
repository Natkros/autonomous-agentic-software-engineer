# Agent Roles

This describes the multi-agent design ForgeAI is built toward. As of
Phase 5, five of these agents are real, tested, working code
(`agents/requirement`, `agents/repository`, `agents/planner`,
`agents/coder`, `agents/debugger` — see `PHASE_3_STATUS.md` and
`PHASE_5_STATUS.md`); the remaining six still hold only empty placeholder
directories under `agents/`.

| Agent | Responsibility | Phase | Status |
|---|---|---|---|
| Requirement Analyst | Parse a natural-language task into functional/non-functional requirements, constraints, acceptance criteria | 3 | ✅ implemented |
| Repository Explorer | File tree, language/framework/entry-point detection, test discovery | 2-3 | ✅ implemented |
| Planner | Decompose the requirement into a task DAG with dependencies and risk | 3 | ✅ implemented |
| Coder | Produce minimal, targeted patches; applies via Phase 4 tools inside the self-correction loop | 3-5 | ✅ implemented |
| Debugger | Classify failures (syntax/type/import/logic/config/etc.), find root cause, propose a patch | 5 | ✅ implemented |
| Architecture Analyst | Map services, layers, and conventions from the indexed repo | 4 | not started |
| Test Engineer | Generate unit/integration/API/regression/security tests | 4-5 | not started |
| Code Reviewer | Review only the diff; classify findings BLOCKER/HIGH/MEDIUM/LOW/INFO | 6 | not started |
| Security | Scan for secrets, injection, insecure deserialization, etc.; can block finalization | 6 | not started |
| Documentation | Keep README/API docs in sync with the diff | 6 | not started |
| Final Validator | Confirm requirements were met before requesting human approval | 6-7 | not started |

## What "implemented" means here

Each implemented agent takes validated Pydantic input and returns
validated Pydantic output (`core/state/schemas.py`) — never a raw string.
The Requirement Analyst, Planner, Coder, and Debugger call an
`LLMProvider` (`core/providers/llm_provider.py`); in this environment
that resolves to `MockLLMProvider`, a deterministic, rule-based stand-in
with no real language understanding (no network/API key is available
here). The Repository Explorer needs no LLM at all — it wraps Phase 2's
deterministic scanner. The Debugger's `failure_category` field is never
trusted from the LLM layer at all — it always comes from
`agents/debugger/failure_classifier.py`'s real pattern matching over
actual test output. See `PHASE_3_STATUS.md`/`PHASE_5_STATUS.md` before
assuming plan/patch/debug *quality* reflects a real model's reasoning —
what's verified is the pipeline's plumbing (schema validation, state
flow, dependency-graph validity, bounded retry), not the content a real
LLM would eventually produce.

## Orchestration

Two things exist, not yet connected to each other:

1. A real, compiled **LangGraph** `StateGraph`
   (`core/orchestration/graph.py`, used by `POST /api/tasks`) wiring
   `requirement -> repository -> planner -> coder -> END`, driven by a
   single explicit `AgentState` TypedDict (`core/state/agent_state.py`).
   It stops after the Coder *proposes* a patch.
2. A real, bounded self-correction loop
   (`core/orchestration/self_correction.py`): apply a proposed patch,
   run tests, and on failure diagnose + retry, up to 5 iterations, then
   stop and report `NEEDS_HUMAN_INTERVENTION`. Callable and tested
   standalone; not yet invoked from `graph.py` or the API (a deliberate,
   separately-reviewable next step — see `PHASE_5_STATUS.md`).

No agent relies on hidden conversational context in either path. Each
`graph.py` node catches its own failures into `state["errors"]` rather
than crashing the run. See `ARCHITECTURE.md` for the full target graph
shape (review, security, and git automation nodes are not wired in yet).

## Tool framework

`tools/base.py` defines the controlled `Tool` interface every agent tool
implements: a Pydantic input schema, a minimum `PermissionLevel`, a
timeout, and mandatory audit logging on every call (win or lose). Real
tools exist at every permission level up through EXECUTION:
`repository.analyze`/`code.search`/`symbol.search` (READ_ONLY, wrapping
`code_intelligence`); `filesystem.read`/`filesystem.list` (READ_ONLY) and
`filesystem.write`/`filesystem.delete`/`filesystem.patch` (SAFE_WRITE,
the last one syntax-verifying Python content before ever writing it); and
`terminal.execute`/`test.run` (EXECUTION, allowlisted and sandboxed).
GIT_WRITE and DEPLOYMENT tools don't exist yet — see
`core/policies/permissions.py`.

## Autonomy levels

`core/policies/permissions.py` implements all six levels (0 read-only
through 5 full autonomy) as a real, tested policy engine mapping each
level to a maximum `PermissionLevel` it may exercise without stopping for
human approval — `DEPLOYMENT` always requires approval regardless of
level. As of Phase 4/5, tools exist for every level up through EXECUTION,
so this policy now has real work to gate — but real OS-level isolation
for what EXECUTION-level tools run is unverified (see
`sandbox/README.md`): only `LocalProcessSandbox`, a weaker mitigation, has
actually been exercised in this environment.
