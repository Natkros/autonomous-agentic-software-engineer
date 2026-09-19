"""Rate limiting for endpoints that accept unauthenticated credentials.

`/api/auth/register` and `/api/auth/login` are the only endpoints anyone
can call without a bearer token — the natural target for a credential-
stuffing or password-guessing bot. This uses `slowapi` (a real,
maintained wrapper around `limits`), keyed by client IP, with an
in-memory store — sufficient for a single-process deployment; a
multi-instance production deployment would need a shared backend (Redis)
for the limit to hold across processes, which is not wired up here (see
`RUNNING.md`).

Disabled under `ENVIRONMENT=test` (set by `apps/api/tests/conftest.py`)
so the test suite's many rapid register/login calls from the same
`TestClient` "IP" are never throttled — real request-rate limiting is
not something this project's automated tests are exercising, only that
the limiter is wired up and returns the exact 429 shape the API's own
error envelope uses.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=get_settings().environment != "test",
)

# Generous enough not to bother a real user who mistypes a password a few
# times, tight enough to make scripted credential stuffing impractical.
AUTH_RATE_LIMIT = "10/minute"
