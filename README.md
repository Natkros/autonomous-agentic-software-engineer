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
actually run and verified. Current status: **Phase 8 complete** — see
[`PHASE_1_STATUS.md`](PHASE_1_STATUS.md),
[`PHASE_2_STATUS.md`](PHASE_2_STATUS.md),
[`PHASE_3_STATUS.md`](PHASE_3_STATUS.md),
[`PHASE_4_STATUS.md`](PHASE_4_STATUS.md),
[`PHASE_5_STATUS.md`](PHASE_5_STATUS.md),
[`PHASE_6_STATUS.md`](PHASE_6_STATUS.md),
[`PHASE_7_STATUS.md`](PHASE_7_STATUS.md), and
[`PHASE_8_STATUS.md`](PHASE_8_STATUS.md) for exactly what was built and
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
- A real pytest suite, **246 tests total**, run in this session and
  double-checked in clean Python 3.12 virtual environments matching CI
  (not just the pre-warmed shared dev venv — see `PHASE_5_STATUS.md` for
  why that distinction matters, including real CI-only bugs it caught in
  Phases 5 and 7): `code_intelligence` (40), `core` (47), `sandbox` (12),
  `tools` (95), `agents` (28), `evaluation` (4), `apps/api` (20), plus
  the frontend build.

## What does not exist yet

Observability and production deployment tooling (Phases 9-10). The
corresponding agent directories (`agents/architecture`, `agents/tester`,
`agents/documentation`, `agents/validator`) are empty scaffolding. The
agent pipeline (`core/orchestration/graph.py`, used by `/api/tasks`) does
not yet call the self-correction loop, the Phase 4 tools, the Phase 6
review/security agents, or the Phase 7 git/approval tools — it still
stops after the Coding Agent proposes a patch. `MockLLMProvider`'s patch
content is a deterministic heuristic stub (a valid-but-trivial function),
never a real fix — the self-correction loop and the evaluation harness
built on top of it prove the *retry mechanism* is bounded and correct,
not that any AI is meaningfully debugging or solving code (see
`PHASE_5_STATUS.md`/`PHASE_8_STATUS.md`). The static analysis and secret
scanning are original, dependency-free implementations covering a
deliberately small rule set — not a wrapper around a real tool like
Semgrep/Bandit/Gitleaks. No pull request has ever actually been opened —
`GitHubPullRequestClient` is real, complete code that has never been run
against the live GitHub API here (no network/token in this environment).
Cost tracking is not wired into any LLM call or pipeline run yet. A call
graph (which function calls which) also doesn't exist yet — only
file-level import relationships are resolved. See each phase's status doc
for the full list of explicit gaps, including that no real LLM call has
ever been made in this environment and Docker sandboxing has never been
run against a live daemon here.

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
pip install -r requirements-dev.txt && python -m pytest -v   # 47 passed

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

This brings up Postgres, Redis, the API (port 8000), and the web app
(port 3000). **Note:** this compose stack has not been exercised in this
environment (no Docker daemon available here), and its `api` image does
not currently include `code_intelligence`/`core`/`agents`/`tools`/`sandbox`
in its build context, so `/analyze` and `/tasks` would not work inside it
as-is — see `PHASE_2_STATUS.md`/`PHASE_3_STATUS.md`.

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
4. **Autonomous execution** — sandboxed filesystem/terminal tools, patching, test runs. ✅ done (Docker isolation itself unverified — see `PHASE_4_STATUS.md`)
5. **Self-correction** — debugger, failure classification, iterative patch loop (max 5 iterations). ✅ done (mechanism verified; patch *quality* still depends on `MockLLMProvider`'s heuristic — see `PHASE_5_STATUS.md`)
6. **Code review** — static analysis, security scanning. ✅ done (real, deterministic checks; not wired into the pipeline yet — see `PHASE_6_STATUS.md`)
7. **Git automation** — branches, commits, diffs, PRs, approval workflow. ✅ done (branch/commit/push verified against real local repos; PR creation is real, unverified code — see `PHASE_7_STATUS.md`)
8. **Evaluation** — benchmark tasks, success metrics, cost tracking. ✅ done (measures mechanism convergence, not coding correctness — see `PHASE_8_STATUS.md`)
9. Observability — OpenTelemetry, Prometheus, Grafana.
10. Production deployment — CI/CD, secrets management, monitoring.

## Security model

See [`ARCHITECTURE.md`](ARCHITECTURE.md#security-model-phase-1-subset) for
what's enforced today, [`PHASE_3_STATUS.md`](PHASE_3_STATUS.md) for the
permission-level/autonomy-level system, and
[`PHASE_4_STATUS.md`](PHASE_4_STATUS.md) /
[`sandbox/README.md`](sandbox/README.md) for exactly what level of
execution isolation is and isn't provided today. Prompt-injection defenses
are still not implemented.

## Contributing

This is an active build-out; see the phase status docs before assuming any
capability beyond Phase 8 exists.
