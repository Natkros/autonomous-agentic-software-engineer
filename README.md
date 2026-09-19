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
actually run and verified. Current status: **Phase 1 complete** — see
[`PHASE_1_STATUS.md`](PHASE_1_STATUS.md) for exactly what was built and
tested versus what's still a placeholder.

## What works right now

- Register/login with JWT auth (FastAPI + bcrypt + `python-jose`).
- Create and list Git repository records, scoped per-user.
- A Next.js dashboard that drives the API above.
- A real pytest suite (9 tests) exercising auth and repository ownership
  rules, run against an isolated in-memory database.

## What does not exist yet

Repository indexing, AST/code intelligence, the LangGraph agent
orchestrator, sandboxed tool execution, automated code review/security
agents, Git branch/PR automation, observability, and the evaluation
harness. These are Phases 2-10 of the roadmap below and are not
implemented — the corresponding directories (`agents/`, `core/`, `tools/`,
`code_intelligence/`, `sandbox/`, `evaluation/`) are empty scaffolding.

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
environment (no Docker daemon available here) — see `PHASE_1_STATUS.md`.

## Environment variables

See [`.env.example`](.env.example) for the full list (`DATABASE_URL`,
`REDIS_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`, etc).

## API surface (Phase 1)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | none | Liveness check |
| POST | `/api/auth/register` | none | Create a user |
| POST | `/api/auth/login` | none | OAuth2 password flow, returns a JWT |
| POST | `/api/repositories` | Bearer | Create a repository owned by the caller |
| GET | `/api/repositories` | Bearer | List the caller's repositories |
| GET | `/api/repositories/{id}` | Bearer | Fetch one repository (404 if not owned) |

## Roadmap

1. **Foundation** — repo, FastAPI, Next.js, Postgres, Redis, Docker, auth, basic UI. ✅ done
2. Repository intelligence — indexing, AST, symbol extraction, vector search.
3. Agent core — `AgentState`, tool framework, LangGraph, planner.
4. Autonomous execution — sandboxed filesystem/terminal tools, patching, test runs.
5. Self-correction — debugger, failure classification, iterative patch loop (max 5 iterations).
6. Code review — static analysis, security scanning.
7. Git automation — branches, commits, diffs, PRs, approval workflow.
8. Evaluation — benchmark tasks, success metrics, cost tracking.
9. Observability — OpenTelemetry, Prometheus, Grafana.
10. Production deployment — CI/CD, secrets management, monitoring.

## Security model

See [`ARCHITECTURE.md`](ARCHITECTURE.md#security-model-phase-1-subset) for
what's enforced today. Full RBAC, sandboxing, and prompt-injection
defenses land in later phases.

## Contributing

This is an active build-out; see the phase status docs before assuming any
capability beyond Phase 1 exists.
