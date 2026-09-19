import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, health, metrics, repositories, tasks
from app.config import get_settings
from app.database import Base, engine

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.observability.logging_config import configure_json_logging  # noqa: E402

settings = get_settings()
logger = logging.getLogger("forgeai.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 9: every log line from here on is a single JSON object — see
    # core/observability/logging_config.py.
    configure_json_logging()
    # Phase 1: schema is created directly. Alembic migrations land in a later phase.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
