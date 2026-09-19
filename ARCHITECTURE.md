# Architecture

ForgeAI is being built incrementally across 10 phases (see `README.md` for the
full roadmap). This document describes the target architecture and, explicitly,
which parts of it exist today versus which are placeholders for a later phase.

## Target system

As of Phase 3, the top half of this diagram — from USER down through the
Requirement/Repository/Planning agents to a proposed patch — is real,
running code (see "What exists today" below). Everything from the
Execution Agent / Docker Sandbox downward is still Phase 4+.

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

## What exists today (Phases 1-3)

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
- `core` — `AgentState` (an explicit, JSON-serializable TypedDict) and
  Pydantic schemas for every agent artifact; an `LLMProvider` abstraction
  (`MockLLMProvider`, real deterministic/offline and actually exercised by
  the test suite; `AnthropicLLMProvider`, real code, unverified — no
  network/key here); the five-tier `PermissionLevel` / six-tier
  `AutonomyLevel` policy engine; and `core/orchestration/graph.py`, a real
  compiled **LangGraph** `StateGraph`. 24/24 tests pass.
- `tools` — the controlled `Tool` interface (permission-checked,
  timed, audit-logged on every call) plus three real READ_ONLY tools
  wrapping `code_intelligence`: `repository.analyze`, `code.search`,
  `symbol.search`. 12/12 tests pass.
- `agents` — four working agents: `RequirementAnalystAgent`,
  `RepositoryExplorerAgent` (no LLM needed — wraps Phase 2's scanner),
  `PlanningAgent` (validates its own output has no dangling task
  dependencies), and `CodingAgent` (proposes patches; never applies them).
  9/9 tests pass. The other seven agent roles (architecture, test, debug,
  review, security, documentation, validator) remain empty placeholders.
- `apps/api` also now exposes `POST /api/tasks` and `GET /api/tasks/{id}`,
  which clone a repository and run the full LangGraph pipeline
  (Requirement -> Repository -> Planner -> Coder) against it, storing the
  result in a new `tasks` table. Verified end-to-end against a real cloned
  fixture repo, using `MockLLMProvider` (no API key configured here).
- `docker-compose.yml` + `infrastructure/docker/*.Dockerfile` — Postgres,
  Redis, API, and web services wired together for local/prod-like runs.
  (Not yet exercised in this session, and the `api` image does not yet
  include `code_intelligence`/`core`/`agents`/`tools` in its build context
  — see `PHASE_2_STATUS.md`/`PHASE_3_STATUS.md`.)
- `.github/workflows/ci.yml` — runs `code_intelligence`, `core`, `tools`,
  `agents`, and `backend` pytest suites, plus a frontend production build,
  on every push/PR.

## What is scaffolded but not implemented (Phase 4+)

`agents/architecture`, `agents/tester`, `agents/debugger`,
`agents/reviewer`, `agents/security`, `agents/documentation`,
`agents/validator`, `sandbox/`, and `evaluation/` are currently empty
directories (holding a `.gitkeep`) that reserve the shape described in the
roadmap. None of the sandboxed tool execution, self-correction loop,
review/security scanning, or evaluation harness exists yet. Do not assume
any code there works until a later phase's status doc says so.
(`code_intelligence/`, `core/`, `agents/{requirement,repository,planner,coder}`,
and `tools/{base.py,search/}` are no longer placeholders — see above.)

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

tasks
  id                    varchar(36) PK
  repository_id         varchar(36) FK -> repositories.id NOT NULL
  user_request          text NOT NULL
  status                enum(COMPLETED, FAILED) NOT NULL
  requirement_analysis  json NULL   -- RequirementAnalysis.model_dump()
  repository_summary    json NULL   -- RepositorySummary.model_dump()
  plan                  json NULL   -- [Task.model_dump(), ...]
  patch_proposals       json NULL   -- [PatchProposal.model_dump(), ...]
  errors                json NULL
  created_at            timestamptz NOT NULL
```

Later phases add `repository_files`, `repository_symbols`, `task_steps`,
`agent_runs`, `tool_calls`, `code_changes`, `test_runs`, `test_results`,
`security_findings`, `approvals`, `evaluations`, and `audit_logs` per the
full schema in the project spec — none of these exist in the database
yet. `repository_analyses` and `tasks` above each stand in for a
lightweight version of the fuller normalized schema, storing whole
results as JSON blobs rather than normalized rows — a simplification
worth revisiting once other phases need to query individual symbols,
tasks, or tool calls directly rather than through one JSON column.

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

RBAC enforcement beyond "own vs. not-own" and prompt-injection defenses
are still not implemented. The permission-level system now exists
(`core/policies/permissions.py`: `READ_ONLY`/`SAFE_WRITE`/`EXECUTION`/
`GIT_WRITE`/`DEPLOYMENT`, gated by a 0-5 `AutonomyLevel`, with
`DEPLOYMENT` always requiring human approval) and is enforced by every
`Tool.run()` call — but sandboxed execution of anything above READ_ONLY
doesn't exist yet, so in practice only the three READ_ONLY search tools
can currently run at all.
