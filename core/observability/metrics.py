"""Real Prometheus metrics via `prometheus_client` — actual `Counter`/
`Histogram` objects, rendered in real Prometheus text-exposition format
by the library's own `generate_latest()`. Verified in this project's test
suite by parsing that real output, not by asserting against a live
Prometheus server (none is reachable in this environment) — a working
`/metrics` endpoint that a real Prometheus can scrape is a separate,
unverified integration step; see `PHASE_9_STATUS.md`.

Uses a dedicated `CollectorRegistry` rather than the library's global
default registry, so importing this module repeatedly (e.g. across
pytest test modules) never raises prometheus_client's
"Duplicated timeseries" registration error.
"""
from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

REGISTRY = CollectorRegistry()

TOOL_CALLS_TOTAL = Counter(
    "forgeai_tool_calls_total", "Total tool invocations", ["tool_name", "success"], registry=REGISTRY,
)
TOOL_CALL_DURATION_SECONDS = Histogram(
    "forgeai_tool_call_duration_seconds", "Tool call duration in seconds", ["tool_name"], registry=REGISTRY,
)


def record_tool_call(tool_name: str, success: bool, duration_seconds: float) -> None:
    TOOL_CALLS_TOTAL.labels(tool_name=tool_name, success=str(success)).inc()
    TOOL_CALL_DURATION_SECONDS.labels(tool_name=tool_name).observe(duration_seconds)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)
