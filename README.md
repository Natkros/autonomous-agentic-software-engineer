# ForgeAI

> An autonomous AI software engineer that plans, builds, tests, debugs,
> reviews, and ships software.

ForgeAI is being built as a multi-agent, tool-using software engineering
platform — not a code-generation chatbot. The full target design (agent
graph, code intelligence pipeline, sandboxed execution, evaluation
framework, observability) is described in [`ARCHITECTURE.md`](ARCHITECTURE.md)
and [`AGENTS.md`](AGENTS.md).

**This repository is being built incrementally, one phase at a time.**
Only claim a feature works if the relevant phase's status doc says it was
actually run and verified. Current status: **Phase 3 complete** — see
[`PHASE_1_STATUS.md`](PHASE_1_STATUS.md),
[`PHASE_2_STATUS.md`](PHASE_2_STATUS.md), and
[`PHASE_3_STATUS.md`](PHASE_3_STATUS.md) for exactly what was built and
tested versus what's still a placeholder.

## What works right now

- Register/login with JWT auth (FastAPI + bcrypt + `python-jose`).
- Create and list Git repository records, scoped per-user.
- A Next.js dashboard that drives the API above.
- **Repository analysis**: `POST /api/repositories/{id}/analyze` clones a
  repository with the real `git` binary and runs the `code_intelligence`
  scanner against it — file tree analysis, AST-based symbol extraction
  (Python and JavaScript; heuristic for TypeScript), dependency/framework
  detection, API route and DB model detection, and a hybrid
  semantic+keyword+symbol+path code search (see
  [`code_intelligence/README.md`](code_intelligence/README.md)).
- **Agent pipeline**: `POST /api/tasks` clones a repository and runs a real,
  compiled **LangGraph** state machine — Requirement Analyst -> Repository
  Explorer -> Planner -> Coder — producing a validated task plan and
  candidate patch proposals (proposals only; nothing is written to disk
  yet). Every agent output is a schema-validated Pydantic model flowing
  through one explicit `AgentState`, not hidden conversational context.
  The LLM layer defaults to a deterministic offline provider
  (`MockLLMProvider`) unless `ANTHROPIC_API_KEY` is set — see
  [`PHASE_3_STATUS.md`](PHASE_3_STATUS.md) for exactly what that does and
  doesn't mean about output quality.
- A real pytest suite, **105 tests total**, run in this session:
  `code_intelligence` (40), `core` (24), `tools` (12), `agents` (9),
  `apps/api` (20).

## What does not exist yet

Sandboxed tool execution, self-correction/debugging loops, automated code
review/security agents, Git branch/PR automation, observability, and the
evaluation harness. These are Phases 4-10 of the roadmap below and are not
implemented — the corresponding agent directories (`agents/architecture`,
`agents/tester`, `agents/debugger`, `agents/reviewer`, `agents/security`,
`agents/documentation`, `agents/validator`) and `sandbox/`/`evaluation/`
are empty scaffolding. A call graph (which function calls which) also
doesn't exist yet — only file-level import relationships are resolved.
See `PHASE_2_STATUS.md` and `PHASE_3_STATUS.md` for the full list of
explicit gaps, including that no real LLM call has ever been made in this
environment (no network/API key here).

## Local development

### Backend

```bash
cd apps/api
python -m venv .venv
source .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -v             # run the test suite
uvicorn app.main:app --reload --port 8000
```

By default the API points at `postgresql+psycopg://forgeai:forgeai@localhost:5432/forgeai`.
For local development without Postgres running, set `DATABASE_URL=sqlite:///./dev.db`.

The `/analyze` and `/tasks` endpoints import the standalone `code_intelligence`,
`core`, `agents`, and `tools` packages from the repository root (see each
package's README for why) and shell out to `git` — make sure `git` is on
`PATH`. Set `ANTHROPIC_API_KEY` to use real LLM calls instead of the
deterministic offline `MockLLMProvider`; without it, `/tasks` still runs
end-to-end using the mock.

### Standalone packages

Each of these can be installed and tested independently of the API:

```bash
cd code_intelligence && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 40 passed

cd ../core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 24 passed

cd ../tools && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 12 passed

cd ../agents && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 9 passed
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` (see `.env.example`) if the API isn't on
`http://localhost:8000`.

### Full stack via Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

This brings up Postgres, Redis, the API (port 8000), and the web app
(port 3000). **Note:** this compose stack has not been exercised in this
environment (no Docker daemon available here), and its `api` image does
not currently include `code_intelligence`/`core`/`agents`/`tools` in its
build context, so `/analyze` and `/tasks` would not work inside it as-is
— see `PHASE_2_STATUS.md`/`PHASE_3_STATUS.md`.

## Environment variables

See [`.env.example`](.env.example) for the full list (`DATABASE_URL`,
`REDIS_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`, etc).
`ANTHROPIC_API_KEY` is optional — see above.

## API surface

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | none | Liveness check |
| POST | `/api/auth/register` | none | Create a user |
| POST | `/api/auth/login` | none | OAuth2 password flow, returns a JWT |
| POST | `/api/repositories` | Bearer | Create a repository owned by the caller |
| GET | `/api/repositories` | Bearer | List the caller's repositories |
| GET | `/api/repositories/{id}` | Bearer | Fetch one repository (404 if not owned) |
| POST | `/api/repositories/{id}/analyze` | Bearer | Clone + scan the repository; returns the analysis (COMPLETED or FAILED) |
| GET | `/api/repositories/{id}/analysis` | Bearer | Fetch the most recent analysis (404 if none has run) |
| POST | `/api/tasks` | Bearer | Clone the repository and run the agent pipeline against a natural-language request |
| GET | `/api/tasks/{id}` | Bearer | Fetch a task run's stored result |

## Roadmap

1. **Foundation** — repo, FastAPI, Next.js, Postgres, Redis, Docker, auth, basic UI. ✅ done
2. **Repository intelligence** — indexing, AST, symbol extraction, vector search. ✅ done
3. **Agent core** — `AgentState`, tool framework, LangGraph, planner, repository agent, coding agent. ✅ done
4. Autonomous execution — sandboxed filesystem/terminal tools, patching, test runs.
5. Self-correction — debugger, failure classification, iterative patch loop (max 5 iterations).
6. Code review — static analysis, security scanning.
7. Git automation — branches, commits, diffs, PRs, approval workflow.
8. Evaluation — benchmark tasks, success metrics, cost tracking.
9. Observability — OpenTelemetry, Prometheus, Grafana.
10. Production deployment — CI/CD, secrets management, monitoring.

## Security model

See [`ARCHITECTURE.md`](ARCHITECTURE.md#security-model-phase-1-subset) for
what's enforced today, and [`PHASE_3_STATUS.md`](PHASE_3_STATUS.md) for the
new permission-level/autonomy-level system. Sandboxed execution and
prompt-injection defenses land in Phase 4+.

## Contributing

This is an active build-out; see the phase status docs before assuming any
capability beyond Phase 3 exists.
