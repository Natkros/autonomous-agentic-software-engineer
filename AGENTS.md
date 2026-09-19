# Agent Roles

This describes the multi-agent design ForgeAI is built toward. As of
Phase 9, seven of these agents are real, tested, working code
(`agents/requirement`, `agents/repository`, `agents/planner`,
`agents/coder`, `agents/debugger`, `agents/security`, `agents/reviewer` —
see `PHASE_3_STATUS.md`, `PHASE_5_STATUS.md`, and `PHASE_6_STATUS.md`).
Phases 7 (git automation), 8 (evaluation), and 9 (observability) added no
new agent role — per the spec, all three are infrastructure (`tools/git`,
`core/policies/approval.py`, `evaluation/`, `core/observability/`) that
*exercises or instruments* the existing agents and tools, not new agents
themselves. Every tool call any agent makes now produces a real trace
span, metric, and structured log line (`tools/base.py`'s `Tool.run()`) —
see `PHASE_9_STATUS.md` for why that instrumentation currently has
nothing real to observe (no API request path reaches the tool layer
yet). The remaining four agent roles still hold only empty placeholder
directories under `agents/`.

| Agent | Responsibility | Phase | Status |
|---|---|---|---|
| Requirement Analyst | Parse a natural-language task into functional/non-functional requirements, constraints, acceptance criteria | 3 | ✅ implemented |
| Repository Explorer | File tree, language/framework/entry-point detection, test discovery | 2-3 | ✅ implemented |
| Planner | Decompose the requirement into a task DAG with dependencies and risk | 3 | ✅ implemented |
| Coder | Produce minimal, targeted patches; applies via Phase 4 tools inside the self-correction loop | 3-5 | ✅ implemented |
| Debugger | Classify failures (syntax/type/import/logic/config/etc.), find root cause, propose a patch | 5 | ✅ implemented |
| Code Reviewer | Review only the diff; classify findings BLOCKER/HIGH/MEDIUM/LOW/INFO | 6 | ✅ implemented |
| Security | Scan for secrets, injection, insecure deserialization, etc.; can block finalization | 6 | ✅ implemented |
| Architecture Analyst | Map services, layers, and conventions from the indexed repo | 4 | not started |
| Test Engineer | Generate unit/integration/API/regression/security tests | 4-5 | not started |
| Documentation | Keep README/API docs in sync with the diff | 6 | not started |
| Final Validator | Confirm requirements were met before requesting human approval | 6-7 | not started |

## What "implemented" means here

Each implemented agent takes validated Pydantic input and returns
validated Pydantic output (`core/state/schemas.py`) — never a raw string.
The Requirement Analyst, Planner, Coder, and Debugger call an
`LLMProvider` (`core/providers/llm_provider.py`); in this environment
that resolves to `MockLLMProvider`, a deterministic, rule-based stand-in
with no real language understanding (no network/API key is available
here). The Repository Explorer, Security Agent, and Code Reviewer need no
LLM at all: file-tree facts, AST-pattern security findings, and secret
detection are direct computations, not judgment calls a model would
improve on — the same reasoning applied consistently since Phase 3's
Repository Explorer. The Debugger's `failure_category` field is likewise
never trusted from the LLM layer — it always comes from
`agents/debugger/failure_classifier.py`'s real pattern matching over
actual test output. See `PHASE_3_STATUS.md`/`PHASE_5_STATUS.md` before
assuming plan/patch/debug *quality* reflects a real model's reasoning —
what's verified is the pipeline's plumbing (schema validation, state
flow, dependency-graph validity, bounded retry), not the content a real
LLM would eventually produce. The Code Reviewer, notably, correctly
identifies `MockLLMProvider`'s own generated patches as unimplemented
stubs — a real, true finding about this project's current LLM layer.

## Orchestration

Four things exist, not yet connected to each other:

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
3. `SecurityAgent` and `CodeReviewAgent` (Phase 6): each callable
   standalone against a repository path or a single `PatchProposal`
   respectively, also not yet invoked from `graph.py` or the API.
4. `tools/git`'s branch/commit/push tools plus
   `core/policies/approval.py` (Phase 7): real, individually tested, not
   yet chained into one "open a PR for this change" operation, and not
   invoked from `graph.py` or the API — see `PHASE_7_STATUS.md`.

No agent relies on hidden conversational context in any of the four.
Each `graph.py` node catches its own failures into `state["errors"]`
rather than crashing the run. See `ARCHITECTURE.md` for the full target
graph shape.

## Tool framework

`tools/base.py` defines the controlled `Tool` interface every agent tool
implements: a Pydantic input schema, a minimum `PermissionLevel`, a
timeout, and mandatory audit logging on every call (win or lose). Real
tools exist at every permission level up through GIT_WRITE:
`repository.analyze`/`code.search`/`symbol.search`,
`filesystem.read`/`filesystem.list`, `git.status`/`git.diff`/`git.log`
(READ_ONLY, the last three real `git` CLI wrappers);
`filesystem.write`/`filesystem.delete`/`filesystem.patch` (SAFE_WRITE,
the last one syntax-verifying Python content before ever writing it) and
`security.scan` (READ_ONLY, combining AST-based static analysis with
regex-based secret detection); `terminal.execute`/`test.run` (EXECUTION,
allowlisted and sandboxed — both default explicitly to
`LocalProcessSandbox`, not whatever `sandbox.factory.get_default_sandbox()`
would pick, after that silent Docker-preference broke them in CI — see
`PHASE_4_STATUS.md`/`PHASE_5_STATUS.md`); and `git.branch`/`git.commit`/
`git.push` (GIT_WRITE, each tested against a real git repository —
`git.push` against a real local bare remote). Only DEPLOYMENT has no tool
yet — see `core/policies/permissions.py`.

## Autonomy levels

`core/policies/permissions.py` implements all six levels (0 read-only
through 5 full autonomy) as a real, tested policy engine mapping each
level to a maximum `PermissionLevel` it may exercise without stopping for
human approval — `DEPLOYMENT` always requires approval regardless of
level. `core/policies/approval.py` (Phase 7) turns "this exceeds the
autonomy level" into the actual structured `ApprovalRequest` a human would
see (spec section 27: reason, files affected, commands, risk level).
Tools exist for every level up through GIT_WRITE, so this policy now has
real work to gate — but real OS-level isolation for what EXECUTION-level
tools run is unverified (see `sandbox/README.md`): only
`LocalProcessSandbox`, a weaker mitigation, has actually been exercised in
this environment.
