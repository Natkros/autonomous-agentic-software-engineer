"""Tests for the production-hardening additions: fail-fast config
validation (app/config.py) and the auth rate limiter (app/rate_limit.py).
Neither is exercised by the rest of the test suite's normal request flow
(the limiter is disabled under ENVIRONMENT=test — see conftest.py), so
each gets a real, direct test here of the actual mechanism.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import DEFAULT_JWT_SECRET, InsecureProductionConfigError, Settings


def test_production_with_default_secret_raises_at_startup():
    settings = Settings(environment="production", jwt_secret=DEFAULT_JWT_SECRET)
    with pytest.raises(InsecureProductionConfigError):
        settings.validate_for_startup()


def test_production_with_a_real_secret_does_not_raise():
    settings = Settings(environment="production", jwt_secret="a-real-randomly-generated-secret")
    settings.validate_for_startup()  # must not raise


def test_development_with_default_secret_does_not_raise():
    """The default secret is fine for local development — only a
    production deployment running it is the real vulnerability.
    """
    settings = Settings(environment="development", jwt_secret=DEFAULT_JWT_SECRET)
    settings.validate_for_startup()  # must not raise


def test_this_test_suites_own_environment_is_exempted_from_rate_limiting():
    """ENVIRONMENT=test (set by conftest.py) is what keeps this suite's
    many rapid register/login calls from tripping the real limiter — this
    asserts that exemption is actually wired, not just assumed.
    """
    from app.rate_limit import limiter as app_limiter

    assert app_limiter.enabled is False


def test_rate_limiter_mechanism_actually_blocks_excess_requests():
    """Proves the underlying slowapi mechanism this project wires into
    /api/auth/register and /api/auth/login genuinely enforces a limit,
    using a real (enabled) Limiter against a throwaway app — independent
    of the disabled, test-only instance the rest of this suite uses.
    """
    limiter = Limiter(key_func=get_remote_address, enabled=True)
    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    def _handler(request: Request, exc: RateLimitExceeded):
        from starlette.responses import JSONResponse
        return JSONResponse(status_code=429, content={"error": "rate limited"})

    @app.get("/ping")
    @limiter.limit("2/minute")
    def ping(request: Request):
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    third = client.get("/ping")
    assert third.status_code == 429
