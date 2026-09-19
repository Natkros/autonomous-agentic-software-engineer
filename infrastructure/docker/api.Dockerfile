# Phase 10 fix: earlier phases' status docs (Phase 2 onward) explicitly
# flagged that this image did not include code_intelligence/core/agents/
# tools/sandbox, so /analyze and /tasks would not actually work inside a
# container built from it. This preserves the *exact* repo-relative
# directory layout inside the image (/app/apps/api/... alongside
# /app/code_intelligence, /app/core, etc.) specifically because
# apps/api/app/services/analysis_service.py and
# apps/api/app/services/task_service.py locate the repo root by walking
# a fixed number of ".." from their own file path — flattening the
# layout would silently break that math. Verified for real in CI (which
# has a live Docker daemon, unlike this project's local dev environment)
# by actually building this image and smoke-testing the running
# container — see PHASE_10_STATUS.md for exactly what that did and
# didn't cover.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc git \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY code_intelligence code_intelligence
COPY core core
COPY agents agents
COPY tools tools
COPY sandbox sandbox
COPY apps/api/app apps/api/app
COPY apps/api/migrations apps/api/migrations
COPY apps/api/alembic.ini apps/api/alembic.ini

WORKDIR /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
