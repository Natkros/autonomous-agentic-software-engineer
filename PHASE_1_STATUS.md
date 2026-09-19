# Phase 1 Status

Scope per the project roadmap: repository, FastAPI, Next.js, PostgreSQL,
Redis, Docker, authentication, basic UI.

## Done and verified

- [x] Git repository initialized.
- [x] FastAPI backend (`apps/api`) with `/api/health`, `/api/auth/register`,
      `/api/auth/login`, and `/api/repositories` (CRUD, owner-scoped).
- [x] JWT authentication with bcrypt password hashing.
- [x] SQLAlchemy models (`User`, `Repository`) with a Postgres connection
      string by default, SQLite-compatible for tests.
- [x] Structured JSON error envelope for both handled and unhandled errors.
- [x] Backend test suite: **9/9 tests passing** (`apps/api/tests`), run
      against an isolated in-memory SQLite database — no external services
      required. Verified by actually running `pytest -v` in this session.
- [x] Next.js 15 + TypeScript + Tailwind frontend (`apps/web`) — login /
      register page and a repository dashboard.
- [x] Frontend production build verified (`npm run build` succeeds, type
      checking passes, 0 `npm audit` vulnerabilities after pinning patched
      `next`/`postcss`/`react` versions).
- [x] Full manual browser verification of the real user flow against the
      real API: register -> redirected to dashboard -> add a repository ->
      see it listed -> sign out -> redirected to login. No mocks.
- [x] `docker-compose.yml` and Dockerfiles for `api`/`web` alongside
      `postgres`/`redis` services.
- [x] GitHub Actions CI running backend tests and frontend build.
- [x] `.env.example`, `Makefile`, `.gitignore`.

## Explicitly NOT done in Phase 1 (do not assume these work)

- Docker Compose stack has **not** been built/run in this session (no
  Docker daemon available in this environment). The Dockerfiles and
  compose file are written to the same contract as the working local
  setup, but they are unverified — run `make up` and confirm before
  relying on them.
- No Alembic migrations yet; the API creates tables directly via
  `Base.metadata.create_all` on startup. Migrations are deferred to a
  later phase once the schema stabilizes further.
- No RBAC beyond "resource belongs to the requesting user or it doesn't."
  The `role` field exists on `User` but nothing branches on it yet.
- No rate limiting, no audit log table, no secrets encryption.
- Everything in Phase 2 onward (repository indexing, AST parsing,
  LangGraph agents, sandboxed execution, code review/security agents,
  Git automation, observability, evaluation) is unimplemented — see
  `ARCHITECTURE.md` for exactly what's scaffolded vs. real.

## How to verify this yourself

```bash
# Backend
cd apps/api
python -m venv .venv && source .venv/Scripts/activate  # or .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
python -m pytest -v

# Frontend
cd apps/web
npm install
npm run build
```

Both were run in this session on Windows with Python 3.14.7 and Node
24.14.0/npm 11.9.0; the backend `requirements.txt` pins versions with
prebuilt wheels for that Python version specifically because several
default pins (psycopg2, older pydantic/SQLAlchemy) do not ship wheels for
Python 3.14 yet — see git history / this file if downgrading Python and
hitting build errors, you may be able to relax those pins.
