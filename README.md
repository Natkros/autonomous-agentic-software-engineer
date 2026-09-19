# ForgeAI

> An autonomous AI software engineer that plans, builds, tests, debugs,
> reviews, and ships software.

ForgeAI is being built as a multi-agent, tool-using software engineering
platform — not a code-generation chatbot. The full target design (agent
graph, code intelligence pipeline, sandboxed execution, evaluation
framework, observability) is described in [`ARCHITECTURE.md`](ARCHITECTURE.md)
and [`AGENTS.md`](AGENTS.md).

**This repository was built incrementally, one phase at a time.** Only
claim a feature works if the relevant phase's status doc says it was
actually run and verified. Current status: **all 10 roadmap phases
complete** — see [`PHASE_1_STATUS.md`](PHASE_1_STATUS.md) through
[`PHASE_10_STATUS.md`](PHASE_10_STATUS.md) for exactly what was built and
tested in each one versus what's explicitly still unverified or out of
scope. "Complete" describes the roadmap's phases, not a finished,
production-ready product — see "What does not exist yet" below and each
phase doc's own limits before relying on any of this.

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
  candidate patch proposals (proposals only; not yet applied by the
  pipeline itself). Every agent output is a schema-validated Pydantic
  model flowing through one explicit `AgentState`, not hidden
  conversational context. The LLM layer defaults to a deterministic
  offline provider (`MockLLMProvider`) unless `ANTHROPIC_API_KEY` is set —
  see [`PHASE_3_STATUS.md`](PHASE_3_STATUS.md) for exactly what that does
  and doesn't mean about output quality.
- **Sandboxed execution tools** (`sandbox/`, `tools/filesystem`,
  `tools/terminal`, `tools/testing`): a path-jailed filesystem workspace;
  structured patch application that verifies Python syntax *before*
  writing (never leaves a broken file, even transiently); an allowlisted
  terminal-execute tool; a pytest-running tool that parses real pass/fail
  counts; and a `Sandbox` abstraction that uses real Docker isolation when
  a daemon is available and a clearly-labeled weaker local-process
  fallback when it isn't. A real end-to-end test copies a repository,
  applies a hand-written patch, and confirms its test suite still passes
  — see [`PHASE_4_STATUS.md`](PHASE_4_STATUS.md) for what's verified vs.
  not (Docker isolation itself is unverified — no live daemon here).
- **Self-correction loop** (`core/orchestration/self_correction.py`): a
  real, bounded `CODE -> TEST -> PASS? -> (done) / (diagnose -> patch ->
  retest)` loop capped at 5 iterations. A real, deterministic
  `agents/debugger/failure_classifier.py` classifies failures (import
  error, type error, syntax error, assertion/test failure, timeout, etc.)
  by actually running broken code and reading pytest's real output — not
  from crafted fixture strings. The loop is verified to terminate
  correctly both when a patch succeeds immediately and when nothing could
  ever make the tests pass (it stops at the cap and reports
  `NEEDS_HUMAN_INTERVENTION` rather than looping forever). See
  [`PHASE_5_STATUS.md`](PHASE_5_STATUS.md) for exactly what this does and
  doesn't prove about patch *quality* (it doesn't — see below).
- **Code review & security scanning** (`tools/security`, `agents/reviewer`,
  `agents/security`): real AST-based static analysis (`eval`/`exec`,
  `shell=True`, insecure deserialization, unsafe `yaml.load`, SQL built
  via string formatting, hardcoded credentials) and regex-based secret
  detection (AWS keys, private key material, Slack/GitHub tokens), both
  deterministic — no LLM call, same principle as the Repository Explorer
  Agent. The Code Review Agent reviews only a proposed patch's actual
  content and correctly flags `MockLLMProvider`'s own stub patches as
  unimplemented — a true finding about this project's current LLM layer,
  not a staged example. See [`PHASE_6_STATUS.md`](PHASE_6_STATUS.md).
- **Git automation** (`tools/git`): real `git.status`/`git.diff`/`git.log`
  (READ_ONLY) and `git.branch`/`git.commit`/`git.push` (GIT_WRITE) tools,
  each tested against a real, freshly-initialized git repository —
  `git.push` is verified against a real local **bare** repo acting as the
  remote, with the test independently re-reading the bare repo's own log
  to confirm the commit actually landed there. Plus
  `core/policies/approval.py`, a deterministic human-approval-request
  builder (spec section 27), and a real (network-gated, unverified)
  `GitHubPullRequestClient`. See [`PHASE_7_STATUS.md`](PHASE_7_STATUS.md).
- **Evaluation harness** (`evaluation/`): a real benchmark runner that
  copies a fixture repo, runs the actual Phase 3 Repository Explorer
  Agent and Phase 5 self-correction loop against it, and checks whether
  the result matches a predicted outcome. **Read this before quoting a
  number from it**: since `MockLLMProvider` can't produce real
  functionality, "success rate" here measures whether the
  self-correction mechanism converges the way it should for a given
  scenario type (safe patch -> quick success; unsolvable test -> bounded
  give-up) — not whether any coding task was actually solved. Also adds
  `core/providers/cost_tracker.py`: token/cost/latency tracking with a
  documented rough heuristic (not a real tokenizer) and illustrative
  pricing; mock calls are tracked at exactly $0.00 since they're not real
  API calls. See [`PHASE_8_STATUS.md`](PHASE_8_STATUS.md).
- **Observability** (`core/observability/`): real structured JSON logging,
  real OpenTelemetry spans (verified via OTel's own in-memory exporter),
  and real Prometheus metrics (verified by parsing the library's own
  `generate_latest()` output) — all wired directly into
  `tools/base.py`'s `Tool.run()`, so every tool call anywhere in the
  system produces a span, a metric observation, and a structured log
  line. `GET /metrics` on the API serves this in real Prometheus text
  format. **Important**: no current API endpoint routes through an
  instrumented `Tool.run()` yet (`/analyze` and `/tasks` call earlier
  phases' code directly), so `/metrics` today is real but empty — see
  [`PHASE_9_STATUS.md`](PHASE_9_STATUS.md) for how to see it populated
  and what a real Prometheus/Grafana stack would need beyond the valid
  config files this phase added (`infrastructure/prometheus/prometheus.yml`,
  `infrastructure/grafana/forgeai-dashboard.json`), neither of which has
  been run against a live instance here.
- **Production deployment groundwork** (Phase 10): the API's Docker image
  now actually includes every package it needs at runtime
  (`code_intelligence`/`core`/`agents`/`tools`/`sandbox` — every earlier
  phase had flagged this as missing) and is **actually built and run in
  CI** (`docker-build-and-smoke-test` in `.github/workflows/ci.yml`),
  polling its real `/api/health`, `/api/ready`, and `/metrics` endpoints
  on the live container — something impossible to check in this
  project's local dev environment (no Docker daemon there). `GET
  /api/ready` runs a real `SELECT 1` against the database and returns a
  genuine 503 if it fails, distinct from `/api/health`'s liveness check.
  A real, syntax-verified (via `nginx -t` in CI) TLS-terminating reverse
  proxy config exists at `infrastructure/nginx/nginx.conf`. A small
  `SecretsProvider` abstraction (`core/config/secrets.py`) formalizes the
  environment-variable-based secrets handling every phase already used.
  See [`PHASE_10_STATUS.md`](PHASE_10_STATUS.md) for what's still
  missing (no live HTTPS, no cloud deployment, no real secrets-manager
  backend — none of which could be verified without infrastructure this
  environment doesn't have).
- A real pytest suite, **268 tests total**, run in this session and
  double-checked in clean Python 3.12 virtual environments matching CI
  (not just the pre-warmed shared dev venv — see `PHASE_5_STATUS.md` for
  why that distinction matters, including real CI-only bugs it caught in
  Phases 5 and 7), plus two CI-only checks (Docker build/smoke-test,
  nginx config validation) that cannot be reproduced locally at all:
  `code_intelligence` (40), `core` (64), `sandbox` (12), `tools` (95),
  `agents` (28), `evaluation` (4), `apps/api` (25), plus the frontend
  build.

## What does not exist yet

Every phase's status doc lists its own explicit gaps in detail; the
recurring ones across the whole project are:

- **The agent pipeline stops at "propose a patch."**
  `core/orchestration/graph.py` (used by `/api/tasks`) never calls the
  Phase 5 self-correction loop, the Phase 6 review/security agents, or
  the Phase 7 git/approval tools — each is real, tested, and callable
  standalone, but none is wired into the pipeline or the API. As a direct
  consequence, Phase 9's tool-level instrumentation currently observes no
  real API traffic, and `agents/architecture`, `agents/tester`,
  `agents/documentation`, and `agents/validator` remain empty
  placeholders.
- **No real LLM call has ever been made in this environment.**
  `MockLLMProvider`'s patch content is a deterministic heuristic stub —
  the self-correction loop and the evaluation harness built on it prove
  the *retry mechanism* is bounded and correct, not that any AI is
  meaningfully debugging or solving code (see
  `PHASE_5_STATUS.md`/`PHASE_8_STATUS.md`). `AnthropicLLMProvider` is
  real, complete, unverified code (no network/API key here).
- **Nothing that requires external infrastructure has been exercised
  live**: Docker sandboxing (no daemon locally — though CI's does exist
  and is now used, see Phase 10), a real GitHub PR (no network/token),
  Prometheus/Grafana actually scraping/rendering this project's metrics,
  live HTTPS, or any cloud deployment.
- **The static analysis and secret scanning are original, dependency-free
  implementations** covering a deliberately small rule set — not a
  wrapper around a real tool like Semgrep/Bandit/Gitleaks. A call graph
  (which function calls which) also doesn't exist — only file-level
  import relationships are resolved. Cost tracking exists but isn't wired
  into any real LLM call or pipeline run yet.

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
pip install -r requirements-dev.txt && python -m pytest -v   # 64 passed

cd ../sandbox && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 12 passed

cd ../tools && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 95 passed

cd ../agents && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 28 passed

cd ../evaluation && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 4 passed
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

This brings up Postgres, Redis, the API (port 8000), the web app (port
3000), Prometheus (port 9090), and Grafana (port 3001). **Note:** the
full multi-service compose stack itself (this exact command) has not
been exercised in this environment (no Docker daemon available in local
dev here) — but as of Phase 10, the `api` image's own build and runtime
behavior *has* been verified for real, in CI, which does have a Docker
daemon (see `PHASE_10_STATUS.md`): the image now includes
`code_intelligence`/`core`/`agents`/`tools`/`sandbox` and its
`/api/health`, `/api/ready`, and `/metrics` endpoints have actually
responded from a real running container. The Grafana dashboard file is
mounted but not wired into Grafana's provisioning system, so it won't
auto-load without also adding a provisioning config — see
`PHASE_9_STATUS.md`. For real HTTPS, see
`infrastructure/nginx/nginx.conf` (syntax-verified via `nginx -t` in CI;
you'll need to provide real certificates and wire it in yourself — see
`PHASE_10_STATUS.md`).

## Environment variables

See [`.env.example`](.env.example) for the full list (`DATABASE_URL`,
`REDIS_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`, etc).
`ANTHROPIC_API_KEY` is optional — see above.

## API surface

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | none | Liveness check (never touches the database) |
| GET | `/api/ready` | none | Readiness check (runs a real query against the database; 503 if unreachable) |
| POST | `/api/auth/register` | none | Create a user |
| POST | `/api/auth/login` | none | OAuth2 password flow, returns a JWT |
| POST | `/api/repositories` | Bearer | Create a repository owned by the caller |
| GET | `/api/repositories` | Bearer | List the caller's repositories |
| GET | `/api/repositories/{id}` | Bearer | Fetch one repository (404 if not owned) |
| POST | `/api/repositories/{id}/analyze` | Bearer | Clone + scan the repository; returns the analysis (COMPLETED or FAILED) |
| GET | `/api/repositories/{id}/analysis` | Bearer | Fetch the most recent analysis (404 if none has run) |
| POST | `/api/tasks` | Bearer | Clone the repository and run the agent pipeline against a natural-language request |
| GET | `/api/tasks/{id}` | Bearer | Fetch a task run's stored result |
| GET | `/metrics` | none | Real Prometheus text-exposition metrics (currently empty — see `PHASE_9_STATUS.md`) |

## Roadmap

1. **Foundation** — repo, FastAPI, Next.js, Postgres, Redis, Docker, auth, basic UI. ✅ done
2. **Repository intelligence** — indexing, AST, symbol extraction, vector search. ✅ done
3. **Agent core** — `AgentState`, tool framework, LangGraph, planner, repository agent, coding agent. ✅ done
4. **Autonomous execution** — sandboxed filesystem/terminal tools, patching, test runs. ✅ done (Docker isolation itself unverified — see `PHASE_4_STATUS.md`)
5. **Self-correction** — debugger, failure classification, iterative patch loop (max 5 iterations). ✅ done (mechanism verified; patch *quality* still depends on `MockLLMProvider`'s heuristic — see `PHASE_5_STATUS.md`)
6. **Code review** — static analysis, security scanning. ✅ done (real, deterministic checks; not wired into the pipeline yet — see `PHASE_6_STATUS.md`)
7. **Git automation** — branches, commits, diffs, PRs, approval workflow. ✅ done (branch/commit/push verified against real local repos; PR creation is real, unverified code — see `PHASE_7_STATUS.md`)
8. **Evaluation** — benchmark tasks, success metrics, cost tracking. ✅ done (measures mechanism convergence, not coding correctness — see `PHASE_8_STATUS.md`)
9. **Observability** — OpenTelemetry, Prometheus, Grafana. ✅ done (real instrumentation, verified in-process; no live Prometheus/Grafana scrape yet — see `PHASE_9_STATUS.md`)
10. **Production deployment** — CI/CD, secrets management, monitoring. ✅ done (Docker image build+run verified for real in CI; no live HTTPS/cloud deployment/secrets-manager backend — see `PHASE_10_STATUS.md`)

## Security model

See [`ARCHITECTURE.md`](ARCHITECTURE.md#security-model-phase-1-subset) for
what's enforced today, [`PHASE_3_STATUS.md`](PHASE_3_STATUS.md) for the
permission-level/autonomy-level system, and
[`PHASE_4_STATUS.md`](PHASE_4_STATUS.md) /
[`sandbox/README.md`](sandbox/README.md) for exactly what level of
execution isolation is and isn't provided today. Prompt-injection defenses
are still not implemented.

## Contributing

All 10 roadmap phases are complete, but "complete" describes the
roadmap's scope, not a finished product — see each phase status doc, and
`PHASE_10_STATUS.md`'s "Where this leaves the project" section, before
assuming any capability beyond what's explicitly documented as verified.
