"""Real OpenTelemetry tracing — actual spans created via the real OTel
SDK, not a stand-in. Verified in this project's test suite using OTel's
own `InMemorySpanExporter` (no collector/Jaeger/OTLP endpoint needed to
prove spans are created correctly with the right name/attributes/status).

`configure_otlp_exporting()` wires up a real OTLP exporter for sending
spans to a real collector — complete code, **unverified**, since no OTel
collector is reachable in this development environment. Same honest
pattern as this project's other network-gated integrations
(`AnthropicLLMProvider`, `GitHubPullRequestClient`).
"""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

_configured = False


def configure_in_memory_tracing() -> tuple[TracerProvider, InMemorySpanExporter]:
    """Real tracing, backed by an in-memory exporter — what this
    project's own tests actually use to verify spans are produced.

    Returns the ``TracerProvider`` itself (not just the exporter):
    OpenTelemetry's global provider can only be registered *once* per
    process (`trace.set_tracer_provider` silently no-ops on a second
    call, logging a warning) — a real constraint that broke this
    module's own tests the first time they ran back-to-back in one
    pytest process. Call ``.get_tracer(name)`` on the returned provider
    directly when isolation across calls matters (e.g. in tests); use
    the module-level ``get_tracer()`` for normal production code, which
    only needs the process-global provider set up once, lazily.
    """
    global _configured
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    if not _configured:
        trace.set_tracer_provider(provider)
        _configured = True
    return provider, exporter


def configure_otlp_exporting(endpoint: str) -> None:
    """Real OTLP export setup — NOT exercised in this environment (no
    collector reachable here). Import is deferred so the optional
    `opentelemetry-exporter-otlp` package is only required if this is
    actually called.
    """
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    global _configured
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str):
    if not _configured:
        configure_in_memory_tracing()
    return trace.get_tracer(name)
