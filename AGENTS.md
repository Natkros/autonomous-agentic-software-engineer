# Agent Roles

This describes the multi-agent design ForgeAI is built toward. As of
Phase 3, four of these agents are real, tested, working code
(`agents/requirement`, `agents/repository`, `agents/planner`,
`agents/coder` — see `PHASE_3_STATUS.md`); the remaining seven still hold
only empty placeholder directories under `agents/`.

| Agent | Responsibility | Phase | Status |
|---|---|---|---|
| Requirement Analyst | Parse a natural-language task into functional/non-functional requirements, constraints, acceptance criteria | 3 | ✅ implemented |
| Repository Explorer | File tree, language/framework/entry-point detection, test discovery | 2-3 | ✅ implemented |
| Planner | Decompose the requirement into a task DAG with dependencies and risk | 3 | ✅ implemented |
| Coder | Produce minimal, targeted patch **proposals**; never applies them yet | 3-4 | ✅ proposal-only |
| Architecture Analyst | Map services, layers, and conventions from the indexed repo | 4 | not started |
| Test Engineer | Generate unit/integration/API/regression/security tests | 4-5 | not started |
| Debugger | Classify failures (syntax/type/import/logic/config/etc.), find root cause, propose a patch | 5 | not started |
| Code Reviewer | Review only the diff; classify findings BLOCKER/HIGH/MEDIUM/LOW/INFO | 6 | not started |
| Security | Scan for secrets, injection, insecure deserialization, etc.; can block finalization | 6 | not started |
| Documentation | Keep README/API docs in sync with the diff | 6 | not started |
| Final Validator | Confirm requirements were met before requesting human approval | 6-7 | not started |

## What "implemented" means here

Each implemented agent takes validated Pydantic input and returns
validated Pydantic output (`core/state/schemas.py`) — never a raw string.
The Requirement Analyst and Planner call an `LLMProvider`
(`core/providers/llm_provider.py`); in this environment that resolves to
`MockLLMProvider`, a deterministic, rule-based stand-in with no real
language understanding (no network/API key is available here). The
Repository Explorer needs no LLM at all — it wraps Phase 2's
deterministic scanner. The Coder only *proposes* a patch; nothing writes
to disk until Phase 4's sandboxed filesystem tools exist. See
`PHASE_3_STATUS.md` before assuming plan/patch *quality* reflects a real
model's reasoning — what's verified is the pipeline's plumbing (schema
validation, state flow, dependency-graph validity), not the content.

## Orchestration

A real, compiled **LangGraph** `StateGraph` (`core/orchestration/graph.py`)
wires `requirement -> repository -> planner -> coder -> END`, driven by a
single explicit `AgentState` TypedDict (`core/state/agent_state.py`) — no
agent relies on hidden conversational context. Each node catches its own
failures into `state["errors"]` rather than crashing the run. See
`ARCHITECTURE.md` for the full target graph shape (testing, debugging,
review, security, and git automation nodes are not wired in yet).

## Tool framework

`tools/base.py` defines the controlled `Tool` interface every agent tool
implements: a Pydantic input schema, a minimum `PermissionLevel`, a
timeout, and mandatory audit logging on every call (win or lose). Three
real READ_ONLY tools exist today, wrapping `code_intelligence`:
`repository.analyze`, `code.search`, `symbol.search`. Filesystem-write,
terminal-execute, and git-write tools are Phase 4 — see
`core/policies/permissions.py` for why those permission levels currently
have no tool that can exercise them.

## Autonomy levels

`core/policies/permissions.py` implements all six levels (0 read-only
through 5 full autonomy) as a real, tested policy engine mapping each
level to a maximum `PermissionLevel` it may exercise without stopping for
human approval — `DEPLOYMENT` always requires approval regardless of
level. There is no autonomous *execution* path yet for this policy to
gate beyond the READ_ONLY search tools, since Phase 4's sandboxed
write/execute tools don't exist yet.
