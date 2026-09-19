# Architecture

ForgeAI is being built incrementally across 10 phases (see `README.md` for the
full roadmap). This document describes the target architecture and, explicitly,
which parts of it exist today versus which are placeholders for a later phase.

## Target system

As of Phase 4, everything from USER down through the Terminal/Editor/Git
tool row is real, running code, EXCEPT that nothing currently connects the
Planning/Coding agents to the Execution Agent — the tools exist and are
tested standalone (see "What exists today" below) but the pipeline itself
stops after producing a patch *proposal*. Docker Sandbox exists as real
code but is unverified (no live daemon in this environment — see
`sandbox/README.md`). Test/Debug/Review/Security agents and Git PR
automation are still Phase 5+.

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

## What exists today (Phases 1-4)

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
  timed, audit-logged on every call). Three READ_ONLY tools wrapping
  `code_intelligence` (`repository.analyze`, `code.search`,
  `symbol.search`); a path-jailed `Workspace` plus `filesystem.read`,
  `filesystem.list`, `filesystem.write`, `filesystem.delete`, and
  `filesystem.patch` (structured create/replace/insert/delete that
  syntax-verifies Python content before ever writing it); an allowlisted
  `terminal.execute`; and `test.run`, which runs pytest through a sandbox
  and parses real pass/fail/error/skip counts. 52/52 tests pass, including
  a real end-to-end apply-a-patch-then-run-the-suite integration test.
- `sandbox` — a `Sandbox` interface: `LocalProcessSandbox` (real, tested,
  no true isolation — see `sandbox/README.md`) and `DockerSandbox` (real,
  complete code — network-disabled, memory/CPU-limited containers —
  **unverified**, no live daemon here). `get_default_sandbox()` picks
  Docker only after actually confirming a daemon responds. 12/12 tests
  pass.
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
  include `code_intelligence`/`core`/`agents`/`tools`/`sandbox` in its
  build context — see `PHASE_2_STATUS.md`/`PHASE_3_STATUS.md`.)
- `.github/workflows/ci.yml` — runs `code_intelligence`, `core`,
  `sandbox`, `tools`, `agents`, and `backend` pytest suites, plus a
  frontend production build, on every push/PR.

## What is scaffolded but not implemented (Phase 5+)

`agents/architecture`, `agents/tester`, `agents/debugger`,
`agents/reviewer`, `agents/security`, `agents/documentation`,
`agents/validator`, and `evaluation/` are currently empty directories
(holding a `.gitkeep`) that reserve the shape described in the roadmap.
None of the self-correction loop, review/security scanning, or evaluation
harness exists yet. Do not assume any code there works until a later
phase's status doc says so. (`code_intelligence/`, `core/`,
`agents/{requirement,repository,planner,coder}`, `tools/`, and `sandbox/`
are no longer placeholders — see above. Note the Coding Agent and the
Phase 4 filesystem/terminal/test tools are NOT wired together yet — see
`PHASE_4_STATUS.md` for why.)

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
are still not implemented. The permission-level system exists
(`core/policies/permissions.py`: `READ_ONLY`/`SAFE_WRITE`/`EXECUTION`/
`GIT_WRITE`/`DEPLOYMENT`, gated by a 0-5 `AutonomyLevel`, with
`DEPLOYMENT` always requiring human approval) and is enforced by every
`Tool.run()` call. As of Phase 4, tools exist at every level up through
EXECUTION (`filesystem.write`/`filesystem.patch`/`filesystem.delete` at
SAFE_WRITE, `terminal.execute`/`test.run` at EXECUTION) — but real OS-level
isolation for anything they run is unverified: `DockerSandbox` is real,
complete code, but no live Docker daemon exists in this development
environment, so what actually runs today is `LocalProcessSandbox`, a
process-level mitigation (working-directory confinement, a command
allowlist, a timeout, a minimal environment), NOT the container isolation
the spec calls for. See `sandbox/README.md` before deploying anything that
executes agent-directed commands against real infrastructure.
