# Phase 10 Status

Scope per the project roadmap: Docker images, Docker Compose, CI/CD,
cloud deployment, HTTPS, secrets management, monitoring, health checks.

This is the final phase of the original 10-phase roadmap.

## Done and verified

- [x] **Fixed a real, long-documented gap**: every phase since Phase 2
  noted that `infrastructure/docker/api.Dockerfile` didn't include
  `code_intelligence`/`core`/`agents`/`tools`/`sandbox`, so `/analyze` and
  `/tasks` wouldn't actually work in a container built from it. The
  Dockerfile now copies all five packages and preserves the exact
  repo-relative directory layout inside the image
  (`/app/apps/api/...` alongside `/app/core`, `/app/tools`, etc.) —
  required because `analysis_service.py`/`task_service.py`/`metrics.py`
  locate the repo root by walking a fixed number of `..` from their own
  file path, which would silently break if the layout were flattened.
- [x] **Real health checks, not hardcoded ones.** `GET /api/health`
  (liveness — never touches the database, so a slow DB doesn't get an
  otherwise-healthy process killed) and `GET /api/ready` (readiness —
  runs an actual `SELECT 1` against the database and returns a real 503
  if it fails). Tested with a fake session object whose `.execute()`
  genuinely raises, not by asserting a hardcoded response.
  `docker-compose.yml`'s `api`/`web` services now have real
  `healthcheck` blocks using each image's own runtime (`python`/`node` —
  no `curl` added just for this) to hit those endpoints.
- [x] `core/config/secrets.py` — a small `SecretsProvider` interface
  (`get`/`require`) with `EnvSecretsProvider`, the real backend every
  phase of this project has always used (reading `os.environ`), now
  behind an explicit, swappable abstraction. No fake cloud-secrets-manager
  stub was added — see below for why.
- [x] `infrastructure/nginx/nginx.conf` — a real TLS-terminating
  reverse-proxy config (redirects HTTP to HTTPS, proxies `/api/`,
  `/metrics`, and `/` to the API/web services). **Verified for real
  syntax correctness in CI** via `nginx -t` inside the official `nginx`
  image, against a throwaway self-signed certificate generated in the CI
  step — something impossible to check at all in this project's local
  dev environment (no nginx installed there).
- [x] **A real Docker build-and-smoke-test CI job**
  (`docker-build-and-smoke-test` in `.github/workflows/ci.yml`): builds
  the actual API image, runs the actual container, polls
  `/api/health`/`/api/ready`/`/metrics` on the real running instance, and
  tears it down. This is the first time in this project's history that
  the Docker image has been proven to actually build and actually run —
  every earlier phase's Docker-related claims were "written but
  unverified, no daemon available locally." CI's `ubuntu-latest` runners
  have a real Docker daemon (the same fact that caused the Phase
  5/`sandbox` default bug), so this is genuinely checked, not asserted.
- [x] Test count: `apps/api` grew from 22 to 25 (readiness tests), `core`
  grew from 58 to 64 (secrets tests). **268 tests total** across all
  seven suites (`code_intelligence` 40, `core` 64, `sandbox` 12,
  `tools` 95, `agents` 28, `evaluation` 4, `apps/api` 25), re-verified in
  clean Python 3.12 venvs matching CI, plus two new CI-only checks
  (Docker build/smoke-test, nginx config validation) that cannot be
  reproduced in local dev here at all.

## Explicitly NOT done in Phase 10

- **No real secrets-manager backend (Vault, AWS Secrets Manager, etc.)
  was implemented.** `SecretsProvider` only has `EnvSecretsProvider`.
  Adding a cloud-backed implementation with no credentials, no reachable
  service, and no way to even structurally verify it in this environment
  would be worse than not claiming it — it would be indistinguishable
  from a non-functional stub dressed up as a real integration. Swapping
  one in later means implementing `SecretsProvider`'s two methods against
  a real SDK, once real credentials exist.
- **No live HTTPS.** The nginx config is real and its syntax is verified,
  but no live nginx has ever terminated a real TLS connection for this
  project, and no real certificate (Let's Encrypt or otherwise) has been
  provisioned — the config's cert paths are placeholders an operator must
  fill in.
- **No cloud deployment.** Nothing has been deployed to AWS/GCP/Azure/
  Railway/Fly/etc. There is no cloud account, credentials, or target
  environment in this development session. The Docker image build+run
  smoke test in CI is the closest thing to a deployment check that exists.
- **`nginx` is not wired into `docker-compose.yml`.** Adding it there
  without also documenting/generating real certificates would make
  `docker compose up` fail out of the box for anyone following the
  README — the config exists and is validated standalone instead.
- **No production secrets rotation, audit logging of secret access, or
  least-privilege secret scoping.** Out of scope for what could be built
  and verified without a real backend.
- **CI/CD stops at "tests pass and the image builds/runs."** There is no
  actual continuous *deployment* — no job pushes an image to a registry
  or deploys it anywhere. That would require registry/cloud credentials
  this project doesn't have.

## Where this leaves the project

Every one of the original roadmap's 10 phases now has real, tested code
behind it, with every phase's status doc distinguishing what was actually
run and verified from what's real-but-unverified (no Docker daemon, no
network/API keys, no live collector/Prometheus/Grafana/cloud account in
this environment) or explicitly out of scope. The agent pipeline
(`core/orchestration/graph.py`) still only reaches "propose a patch" —
wiring in the self-correction loop, the review/security agents, and the
git/approval tools is real, tested, standalone work waiting to be
connected, not still-to-be-built capability. See `README.md`'s "What does
not exist yet" section for the complete, current list.

## How to verify this yourself

```bash
cd apps/api && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 25 passed

cd ../../core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 64 passed
```

The Docker build/smoke-test and nginx config checks can only be verified
by CI (or any machine with a real Docker daemon) — they are not
reproducible in this project's local development environment.
