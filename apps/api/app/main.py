import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import DatabaseError

from app.api.routes import auth, health, metrics, repositories, tasks
from app.config import get_settings
from app.rate_limit import limiter

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.observability.logging_config import configure_json_logging  # noqa: E402

_API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
settings = get_settings()
logger = logging.getLogger("forgeai.api")


def run_migrations() -> None:
    """Apply every pending Alembic migration (see `migrations/`) up to
    `head`. Replaces the `Base.metadata.create_all` this project used
    through Phase 10 — that call could create tables but never evolve an
    existing one, so every schema change from here on is a real, reviewable
    migration file instead. `migrations/env.py` reads the same
    `DATABASE_URL` this app itself uses (`app/config.py`), so this always
    migrates the real target database, never a hardcoded one.

    Handles one real, one-time transition case found deploying this
    exact change to this project's own live database: every deployment
    before this one used `Base.metadata.create_all`, which already
    created every table `eca74b6ad778` (the initial migration) also
    creates — but with no `alembic_version` row recording that. Run
    `upgrade` straight against that database and it fails outright
    (`relation "users" already exists`), inside a transaction Postgres
    rolls back cleanly, so it's always safe to catch and instead `stamp`
    the database at `head`: this asserts "the schema already matches
    this revision," which is true, without re-running any DDL. Any other
    database error (a real migration bug) is not swallowed — it still
    raises. Caught as the dialect-agnostic `DatabaseError` base class
    deliberately: Postgres/psycopg raises `ProgrammingError` for
    "relation already exists" while SQLite raises `OperationalError` for
    the equivalent "table already exists" — both are `DatabaseError`
    subclasses, and this project's tests run against SQLite while
    production runs Postgres.
    """
    alembic_cfg = AlembicConfig(os.path.join(_API_ROOT, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(_API_ROOT, "migrations"))
    try:
        alembic_command.upgrade(alembic_cfg, "head")
    except DatabaseError as exc:
        if "already exists" not in str(exc).lower():
            raise
        logger.warning(
            "Migration target tables already exist with no alembic_version recorded "
            "(expected once, adopting Alembic on a database created by the old "
            "Base.metadata.create_all path) — stamping at head instead of re-running DDL."
        )
        alembic_command.stamp(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail loudly before doing anything else if this is a production
    # deployment still running the well-known default JWT secret.
    settings.validate_for_startup()
    # Phase 9: every log line from here on is a single JSON object — see
    # core/observability/logging_config.py.
    configure_json_logging()
    run_migrations()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # Same error envelope as every other error response — see
    # http_exception_handler below — rather than slowapi's own default
    # plain-text shape.
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "HTTP_429",
                "message": "Too many requests. Please wait before trying again.",
                "retryable": True,
            }
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(repositories.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(metrics.router)


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "retryable": exc.status_code >= 500,
            }
        },
        headers=exc.headers,
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "AGENT_EXECUTION_FAILED",
                "message": "The request could not be completed.",
                "retryable": True,
            }
        },
    )
