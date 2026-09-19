# Agent Roles (Planned)

This describes the multi-agent design ForgeAI is built toward. **None of
these agents are implemented yet** — `agents/` currently holds only empty
placeholder directories. This file exists so the eventual implementation
has an agreed contract to build against, per the project roadmap's Phase 3
("Agent Core") onward.

| Agent | Responsibility | Phase |
|---|---|---|
| Requirement Analyst | Parse a natural-language task into functional/non-functional requirements, constraints, acceptance criteria | 3 |
| Repository Explorer | File tree, language/framework/entry-point detection, test discovery | 2 |
| Architecture Analyst | Map services, layers, and conventions from the indexed repo | 2 |
| Planner | Decompose the requirement into a task DAG with dependencies and risk | 3 |
| Coder | Produce minimal, targeted patches; never blind full-file rewrites | 4 |
| Test Engineer | Generate unit/integration/API/regression/security tests | 4-5 |
| Debugger | Classify failures (syntax/type/import/logic/config/etc.), find root cause, propose a patch | 5 |
| Code Reviewer | Review only the diff; classify findings BLOCKER/HIGH/MEDIUM/LOW/INFO | 6 |
| Security | Scan for secrets, injection, insecure deserialization, etc.; can block finalization | 6 |
| Documentation | Keep README/API docs in sync with the diff | 6 |
| Final Validator | Confirm requirements were met before requesting human approval | 6-7 |

## Orchestration

Planned as a LangGraph state machine (`core/orchestration/`) driven by a
single explicit `AgentState` object (`core/state/`) — no agent is allowed
to rely on hidden conversational context. See `ARCHITECTURE.md` for the
target graph shape.

## Autonomy levels

0 (read-only) through 5 (controlled autonomous PR creation), configurable
per the project spec. Not enforced anywhere yet — there is no autonomous
execution path to gate.
