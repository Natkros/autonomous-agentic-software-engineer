# Running ForgeAI

Three ways to run this project, from quickest to most complete:

1. [Live deployment](#1-live-deployment-fastest) — already running, nothing to install.
2. [Local development](#2-local-development) — run each package/service directly on your machine.
3. [Docker Compose](#3-docker-compose-full-local-stack) — the full multi-service stack in containers.

See [`README.md`](README.md) for what each part of the system actually does, and [`PHASE_11_STATUS.md`](PHASE_11_STATUS.md) for exactly what's verified about the deployment below versus what isn't.

---

## 1. Live deployment (fastest)

A real instance is deployed on [Render](https://render.com):

| Service | URL |
|---|---|
| Web dashboard | https://forgeai-web.onrender.com |
| API | https://forgeai-api-3k85.onrender.com |
| API docs (Swagger UI) | https://forgeai-api-3k85.onrender.com/docs |
| Health check | https://forgeai-api-3k85.onrender.com/api/health |
| Readiness check (real DB query) | https://forgeai-api-3k85.onrender.com/api/ready |
| Metrics (Prometheus format) | https://forgeai-api-3k85.onrender.com/metrics |

**What's actually running:** the real `infrastructure/docker/api.Dockerfile` and `web.Dockerfile` images, built directly by Render from this GitHub repository's `main` branch, backed by a managed Postgres instance, with `ANTHROPIC_API_KEY` set — real Claude calls, not `MockLLMProvider`.

**Verified for real** (not just deployed and assumed working):
- `GET /api/health` → `{"status":"ok"}`
- `GET /api/ready` → `{"status":"ready","database":"reachable"}` — a genuine query against the live Postgres instance, proving the Alembic migration that creates the schema actually ran on startup.
- `GET /metrics` → real Prometheus text output.
- The web dashboard loads and serves `200`.
- A full register → login → create-repository → run-task flow was exercised against the live API with a real account.

**Known current limitation:** the Anthropic API key that's wired in currently has **no credit balance** on the account — a live smoke test got a real, correctly-surfaced error back from Claude's API ("Your credit balance is too low to access the Anthropic API"), not a code failure. The pipeline itself ran correctly end-to-end up to that point (cloned the repo, ran the Repository Explorer Agent for real, called the real Anthropic endpoint, and reported the failure through the normal error path rather than crashing). **Add credits at [console.anthropic.com](https://console.anthropic.com) → Plans & Billing, and the very next task run will use real Claude output — no redeploy or code change needed.**

**Free-tier limits that apply to this specific deployment** (not code limitations):
- The Postgres instance is on Render's free plan and **expires 30 days after creation**. Upgrade it in the Render dashboard before then, or the API will lose its database.
- Both web services are on Render's free plan and **spin down after 15 minutes of no traffic**. The next request after a spin-down takes 30-60 seconds to respond (cold start) — this is normal, not a bug.
- Rate limiting on `/api/auth/register` and `/api/auth/login` is in-memory and per-instance (`numInstances: 1` here, so this doesn't matter yet — see `PHASE_11_STATUS.md` if you ever scale this out).

To manage the deployment (redeploy, view logs, change env vars, upgrade plans): [dashboard.render.com](https://dashboard.render.com). `render.yaml` in this repo documents the exact configuration as a Render Blueprint.

**To try the agent pipeline against the live API:**

```bash
API=https://forgeai-api-3k85.onrender.com

# 1. Register
curl -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"a-real-password"}'

# 2. Log in
TOKEN=$(curl -s -X POST "$API/api/auth/login" \
  -d "username=you@example.com&password=a-real-password" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

# 3. Register a repository to analyze (any public git URL)
REPO_ID=$(curl -s -X POST "$API/api/repositories" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-repo","url":"https://github.com/OWNER/REPO"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")

# 4. Run the agent pipeline against it (autonomy_level 1 = propose only, nothing written)
curl -X POST "$API/api/tasks" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"repository_id":"'"$REPO_ID"'","user_request":"Add a health check endpoint.","autonomy_level":1}'
```

Raise `autonomy_level` to `2`+ to let the execution node actually apply and test patches inside a throwaway clone, or `4`/`5` to also let it commit (never push) — see [`PHASE_11_STATUS.md`](PHASE_11_STATUS.md) for exactly what each level unlocks.

---

## 2. Local development

Requires Python 3.12 and Node 20+. Each package below is independently installable and testable.

### Backend API

```bash
cd apps/api
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
python -m pytest -v                # 32 passed

# Without Postgres running:
export DATABASE_URL=sqlite:///./dev.db
uvicorn app.main:app --reload --port 8000
```

Set `ANTHROPIC_API_KEY` to use real Claude calls; without it, everything runs against the deterministic `MockLLMProvider`. `git` must be on `PATH` (used to clone repositories being analyzed).

### Standalone packages

```bash
cd code_intelligence && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 40 passed

cd ../core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 68 passed

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

Set `NEXT_PUBLIC_API_URL` in `.env` (see `.env.example`) if the API isn't on `http://localhost:8000`.

---

## 3. Docker Compose (full local stack)

```bash
cp .env.example .env
docker compose up --build
```

Brings up Postgres, Redis, the API (`:8000`), the web app (`:3000`), Prometheus (`:9090`), and Grafana (`:3001`). The API container runs its real Alembic migrations on startup (see `PHASE_11_STATUS.md`) — no manual migration step needed. Requires a local Docker daemon (this project's own development environment didn't have one; the images are verified for real in CI and now also in the live Render deployment above).

---

## Database migrations

Schema changes are real Alembic migrations, not `create_all` (see `PHASE_11_STATUS.md`):

```bash
cd apps/api
alembic upgrade head                                    # apply all pending migrations
alembic revision --autogenerate -m "describe the change" # generate a new one after changing a model
```

`migrations/env.py` always reads the same `DATABASE_URL` the app itself uses — never a hardcoded value — so this is safe to run against whichever database your current environment points at.

## Environment variables

See [`.env.example`](.env.example) for the full list. The ones that matter most:

| Variable | Purpose | Required? |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | No — defaults to local Postgres |
| `JWT_SECRET` | Signs auth tokens | **Yes in production** — the app refuses to start with the default value if `ENVIRONMENT=production` |
| `ANTHROPIC_API_KEY` | Enables real Claude calls | No — falls back to `MockLLMProvider` |
| `ENVIRONMENT` | `development` / `test` / `production` | No — defaults to `development` |
| `CORS_ORIGINS` | Allowed frontend origins (JSON array) | No |
