# Phase 9 Status

Scope per the project roadmap: OpenTelemetry, Prometheus, Grafana,
structured logs, agent traces, latency metrics.

## Done and verified

- [x] `core/observability/logging_config.py` — real structured (JSON)
  logging via stdlib `logging` with a custom `JsonFormatter`. Every log
  line is one JSON object with stable base fields (timestamp, level,
  logger, message) plus whatever structured context a caller attaches
  via `extra={...}`. Tested by actually emitting log records into an
  in-memory stream and parsing the real JSON output — including an
  exception log, which includes a real formatted traceback.
- [x] `core/observability/tracing.py` — real distributed tracing via the
  actual OpenTelemetry SDK. `configure_in_memory_tracing()` is what this
  project's own tests use to verify spans are created with the right
  name/attributes/end-time, using OTel's own `InMemorySpanExporter` — no
  collector needed to prove the instrumentation itself is correct.
  `configure_otlp_exporting()` is real, complete code for shipping spans
  to a real OTLP collector, **unverified** (no collector reachable here).
- [x] `core/observability/metrics.py` — real Prometheus metrics via
  `prometheus_client`: a `Counter` (`forgeai_tool_calls_total`, labeled by
  tool name and success) and a `Histogram`
  (`forgeai_tool_call_duration_seconds`). `render_metrics()` calls the
  library's own `generate_latest()` — tests parse that real Prometheus
  text-exposition output, not a hand-rolled stand-in.
- [x] `tools/base.py`'s `Tool.run()` is now instrumented with all three:
  every tool call produces a real span, a real metric observation, and a
  real structured log line, on both the success and failure paths. This
  is genuinely wired into existing, already-tested code — not a
  disconnected add-on — so all 95 `tools` tests (which exercise dozens of
  real tool calls) continue to pass with instrumentation active.
- [x] `GET /metrics` (`apps/api/app/api/routes/metrics.py`) — a real
  FastAPI endpoint serving `render_metrics()`'s output with the correct
  Prometheus content type, unauthenticated (scrapers don't carry a bearer
  token). The API now also configures JSON logging globally on startup.
- [x] `infrastructure/prometheus/prometheus.yml` — a real, valid
  (YAML-parsed and structurally checked) scrape config targeting the
  API's `/metrics` endpoint.
- [x] `infrastructure/grafana/forgeai-dashboard.json` — a real, valid
  (JSON-parsed) Grafana dashboard definition with four panels (tool call
  rate, failure rate, p95 duration, total calls) built from the actual
  metric names this project emits.
- [x] `docker-compose.yml` gained `prometheus` and `grafana` services
  wired to the config files above.
- [x] Test count: `core` grew from 47 to 58 (11 new observability tests),
  `apps/api` grew from 20 to 22. **259 tests total** across all seven
  suites (`code_intelligence` 40, `core` 58, `sandbox` 12, `tools` 95,
  `agents` 28, `evaluation` 4, `apps/api` 22), re-verified in clean Python
  3.12 venvs matching CI.

## A real bug caught and fixed during this phase's own development

OpenTelemetry's global `TracerProvider` can only be registered **once**
per process — a second `trace.set_tracer_provider(...)` call silently
no-ops (logging a warning) rather than replacing it. The first version of
`configure_in_memory_tracing()` returned a fresh exporter on every call
but relied on the global provider actually being replaced each time,
which broke as soon as more than one test in the same pytest process
called it: the second test's assertions failed because its spans were
silently going to the *first* test's already-finished exporter. Fixed by
returning the `TracerProvider` object itself (not just the exporter) so
callers that need per-call isolation (this project's own tests) create a
tracer directly from that provider (`provider.get_tracer(...)`), bypassing
the "set once" global entirely; the module-level `get_tracer()` (what
production code like `tools/base.py` actually uses) still relies on the
global provider being configured exactly once, which is the correct
behavior for a real running process.

## Explicitly NOT done in Phase 9

- **No API endpoint currently produces any real metric/trace/log data
  through this instrumentation.** `/metrics` is real and returns valid
  Prometheus output, but with zero observations: `/analyze` calls the
  Phase 2 scanner directly and `/tasks` calls the Phase 3 pipeline,
  neither of which routes through `tools/base.py`'s instrumented
  `Tool.run()` (consistent with every earlier phase's status doc — the
  pipeline still doesn't call the Phase 4/6/7 tools at all). The
  instrumentation is real and tested at the `Tool.run()` layer; nothing
  in this project's current request paths exercises it yet.
- **Nothing has been scraped by a live Prometheus or rendered in a live
  Grafana.** `prometheus.yml` and `forgeai-dashboard.json` are real,
  valid config — parsed and structurally checked in this session — but
  neither has been run against an actual Prometheus/Grafana instance (no
  Docker daemon available here; see `PHASE_1_STATUS.md`).
- **The Grafana dashboard JSON is not wired into Grafana's provisioning
  system.** Mounting the file into `/var/lib/grafana/dashboards/` alone
  is not sufficient for Grafana to auto-load it — a real deployment needs
  a provisioning YAML pointing at that directory too, which hasn't been
  added (would be untestable without a live Grafana anyway).
- **`configure_otlp_exporting()` has never sent a span anywhere real.**
  Complete code, gated behind a collector endpoint that doesn't exist in
  this environment — same honest pattern as `AnthropicLLMProvider` and
  `GitHubPullRequestClient`.
- **No agent-level tracing.** Instrumentation lives at the `Tool.run()`
  layer (every tool call gets a span/metric/log), not at the agent or
  pipeline layer — `core/orchestration/graph.py` and
  `self_correction.py`'s own steps aren't individually traced yet, only
  the tool calls Phase 4/6/7 tools make when something actually calls
  them (which, per earlier phases' status docs, the pipeline itself
  still doesn't).
- **No log aggregation, alerting, or dashboards-as-code deployment
  pipeline.** Structured JSON logs go to stdout, same as before this
  phase — nothing ships them anywhere.

## How to verify this yourself

```bash
cd core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 58 passed

cd ../tools && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 95 passed

cd ../apps/api && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 22 passed
```

To see real Prometheus output locally without Docker: start the API
(`uvicorn app.main:app --port 8000`) and `curl http://localhost:8000/metrics`
— you'll see the real `# HELP`/`# TYPE` lines with zero observations,
because (per every earlier phase's status doc) no API endpoint currently
calls a `tools/base.py` `Tool` — `/analyze` calls the Phase 2 scanner
directly and `/tasks` calls the Phase 3 pipeline, neither of which routes
through the instrumented `Tool.run()`. To see non-zero metrics, call a
tool directly in Python, e.g.:

```python
from core.policies.permissions import AutonomyLevel
from tools.base import AuditLog
from tools.search.repository_analyze_tool import RepositoryAnalyzeTool
from core.observability.metrics import render_metrics

RepositoryAnalyzeTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=".")
print(render_metrics().decode())
```
