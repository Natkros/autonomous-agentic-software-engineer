# Architecture

ForgeAI is being built incrementally across 10 phases (see `README.md` for the
full roadmap). This document describes the target architecture and, explicitly,
which parts of it exist today versus which are placeholders for a later phase.

## Target system

```
                    USER
                      |
                      v
              +---------------+
              |   Next.js UI  |
              +-------+-------+
                      |
                      v
              +---------------+
              |    FastAPI    |
              |   API Layer   |
              +-------+-------+
                      |
                      v
            +----------------------+
            | Agent Orchestrator   |
            |     (LangGraph)      |
            +----------+-----------+
                       |
        +--------------+---------------+
        |              |               |
        v              v               v
  Requirement      Repository       Planning
    Agent            Agent           Agent
        |              |               |
        +--------------+---------------+
                       v
               +-----------------+
               | Execution Agent |
               +--------+--------+
                        |
         +--------------+--------------+
         v              v              v
      Terminal        Editor          Git
        Tool           Tool           Tool
         |              |              |
         +--------------+--------------+
                        v
                 Docker Sandbox
                        |
                        v
                   Test Agent -> Debug Agent -> Review Agent -> Security Agent
                        |
                        v
                 Final Validator -> Human Approval -> Git PR
```

## What exists today (Phases 1-2)

- `apps/api` — FastAPI backend with JWT authentication (register/login),
  role-based `User` model, `Repository` CRUD scoped to the owner, a
  structured error envelope, and a Postgres-or-SQLite SQLAlchemy layer.
  Covered by a real pytest suite (`apps/api/tests`, 14 tests) run against
  an in-memory SQLite database — no live Postgres/Redis required to pass CI.
- `apps/web` — Next.js 15 + TypeScript + Tailwind frontend with a
  login/register screen and a dashboard that lists and creates
  repositories against the live API. Verified manually end-to-end in a
  browser (register -> login -> create repository -> list -> sign out).
- `code_intelligence` — a standalone Python package (Phase 2): file tree
  analysis, real AST-based symbol extraction for Python and JavaScript
  (heuristic for TypeScript), dependency/framework detection, a file-level
  import graph, an embedding provider abstraction (deterministic offline +
  a real, unverified OpenAI implementation), a Qdrant-embedded/in-memory
  vector index, and a hybrid semantic+keyword+symbol+path retriever. 40/40
  tests pass. See `code_intelligence/README.md` for the full breakdown and
  explicit scope limits (no call graph, TS is heuristic-only, etc).
- `apps/api` also now exposes `POST /api/repositories/{id}/analyze` and
  `GET /api/repositories/{id}/analysis`, which clone a repository with the
  real `git` binary and run the `code_intelligence` scanner against it,
  storing the result in a new `repository_analyses` table. Verified
  end-to-end against a real, freshly-`git init`'d local fixture repo.
- `docker-compose.yml` + `infrastructure/docker/*.Dockerfile` — Postgres,
  Redis, API, and web services wired together for local/prod-like runs.
  (Not yet exercised in this session, and the `api` image does not yet
  include `code_intelligence` in its build context — see
  `PHASE_2_STATUS.md`.)
- `.github/workflows/ci.yml` — runs `code_intelligence` tests, backend
  pytest, and a frontend production build on every push/PR.

## What is scaffolded but not implemented (Phase 3+)

Everything under `agents/`, `core/`, `tools/`, `sandbox/`, and
`evaluation/` is currently an empty directory (holding a `.gitkeep`) that
reserves the shape described in the roadmap. None of the LangGraph
orchestration, sandboxed tool execution, or evaluation harness exists yet.
Do not assume any code there works until a later phase's status doc says
so. (`code_intelligence/` is no longer a placeholder — see above.)

## Database schema (Phase 1 subset)

```
users
  id            varchar(36) PK
  email         varchar(255) UNIQUE NOT NULL
  hashed_password varchar(255) NOT NULL
  role          enum(ADMIN, DEVELOPER, REVIEWER, VIEWER) NOT NULL DEFAULT DEVELOPER
  is_active     boolean NOT NULL DEFAULT true
  created_at    timestamptz NOT NULL

repositories
  id            varchar(36) PK
  name          varchar(255) NOT NULL
  url           varchar(1024) NOT NULL
  description   text NULL
  owner_id      varchar(36) FK -> users.id NOT NULL
  created_at    timestamptz NOT NULL

repository_analyses
  id              varchar(36) PK
  repository_id   varchar(36) FK -> repositories.id NOT NULL
  status          enum(COMPLETED, FAILED) NOT NULL
  summary         json NULL   -- the code_intelligence scan result
  error_message   text NULL
  created_at      timestamptz NOT NULL
```

Later phases add `repository_files`, `repository_symbols`, `tasks`,
`task_steps`, `agent_runs`, `tool_calls`, `code_changes`, `test_runs`,
`test_results`, `security_findings`, `approvals`, `evaluations`, and
`audit_logs` per the full schema in the project spec — none of these
exist in the database yet. (`repository_analyses` above stands in for a
lightweight version of `repository_files`/`repository_symbols` for now,
storing the whole scan as one JSON blob rather than normalized rows — a
simplification worth revisiting once other phases need to query
individual symbols directly rather than through `code_intelligence`'s own
API.)

## Error format

All API errors are returned as:

```json
{
  "error": {
    "code": "HTTP_404",
    "message": "Repository not found",
    "retryable": false
  }
}
```

## Security model (Phase 1 subset)

- Passwords hashed with bcrypt (`passlib`).
- JWT bearer tokens (`python-jose`), 60 minute expiry by default.
- `RepositoryRead`/`UserRead` responses never include `hashed_password`.
- Repositories are strictly scoped to their owner — cross-user access
  returns 404, not 403, to avoid leaking existence.
- CORS origins are explicit allow-list via `CORS_ORIGINS`, not `*`.

RBAC enforcement beyond "own vs. not-own", sandboxed execution, the
permission-level system (`READ_ONLY`/`SAFE_WRITE`/`EXECUTION`/`GIT_WRITE`/
`DEPLOYMENT`), and prompt-injection defenses are Phase 3+ work and are not
implemented yet.
