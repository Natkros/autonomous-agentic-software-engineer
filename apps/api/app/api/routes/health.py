from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Liveness: is the process up at all? Never touches the database —
    a slow/down DB should not make an orchestrator (k8s, Compose,
    Railway, etc.) kill and restart an otherwise-healthy process.
    """
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(response: Response, db: Session = Depends(get_db)) -> dict:
    """Readiness: can this instance actually serve requests right now?
    Runs a real trivial query — not a hardcoded "ok" — so a genuinely
    unreachable database is reported as not-ready (503) rather than
    silently claimed healthy.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "reachable"}
    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "unreachable", "error": str(exc)}
