"""GET /metrics — real Prometheus text-exposition format via
`core.observability.metrics`, importing the standalone `core` package the
same way `analysis_service.py`/`task_service.py` already do.

This endpoint itself has not been scraped by a live Prometheus in this
environment — see `PHASE_9_STATUS.md` for what's verified vs. not.
"""
from __future__ import annotations

import os
import sys

from fastapi import APIRouter
from fastapi.responses import Response

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.observability.metrics import render_metrics  # noqa: E402

router = APIRouter(tags=["observability"])


@router.get("/metrics")
def metrics() -> Response:
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")
