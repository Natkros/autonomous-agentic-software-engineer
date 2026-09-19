from prometheus_client import CollectorRegistry, Counter, Histogram

import core.observability.metrics as metrics_module
from core.observability.metrics import record_tool_call, render_metrics


def _fresh_registry(monkeypatch):
    """Each test gets an isolated registry so call counts from other
    tests (and from tools/base.py instrumenting real tool calls
    elsewhere in the same process) never leak in.
    """
    registry = CollectorRegistry()
    calls_total = Counter("forgeai_tool_calls_total", "t", ["tool_name", "success"], registry=registry)
    duration = Histogram("forgeai_tool_call_duration_seconds", "t", ["tool_name"], registry=registry)
    monkeypatch.setattr(metrics_module, "REGISTRY", registry)
    monkeypatch.setattr(metrics_module, "TOOL_CALLS_TOTAL", calls_total)
    monkeypatch.setattr(metrics_module, "TOOL_CALL_DURATION_SECONDS", duration)
    return registry


def test_record_tool_call_increments_the_counter(monkeypatch):
    _fresh_registry(monkeypatch)
    record_tool_call("git.commit", success=True, duration_seconds=0.05)

    output = render_metrics().decode()
    assert 'forgeai_tool_calls_total{success="True",tool_name="git.commit"} 1.0' in output


def test_record_tool_call_tracks_success_and_failure_separately(monkeypatch):
    _fresh_registry(monkeypatch)
    record_tool_call("test.run", success=True, duration_seconds=0.1)
    record_tool_call("test.run", success=False, duration_seconds=0.2)

    output = render_metrics().decode()
    assert 'forgeai_tool_calls_total{success="True",tool_name="test.run"} 1.0' in output
    assert 'forgeai_tool_calls_total{success="False",tool_name="test.run"} 1.0' in output


def test_render_metrics_produces_valid_prometheus_text_format(monkeypatch):
    _fresh_registry(monkeypatch)
    record_tool_call("filesystem.read", success=True, duration_seconds=0.01)

    output = render_metrics().decode()
    assert "# HELP forgeai_tool_calls_total" in output
    assert "# TYPE forgeai_tool_calls_total counter" in output
    assert "forgeai_tool_call_duration_seconds_bucket" in output
