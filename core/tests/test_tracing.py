from core.observability.tracing import configure_in_memory_tracing, get_tracer


def test_span_is_actually_created_and_captured():
    provider, exporter = configure_in_memory_tracing()
    tracer = provider.get_tracer("test.tracer")

    with tracer.start_as_current_span("do_thing") as span:
        span.set_attribute("example", "value")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "do_thing"
    assert spans[0].attributes["example"] == "value"
    assert spans[0].end_time is not None


def test_nested_spans_are_both_captured():
    provider, exporter = configure_in_memory_tracing()
    tracer = provider.get_tracer("test.tracer")

    with tracer.start_as_current_span("outer"):
        with tracer.start_as_current_span("inner"):
            pass

    names = {s.name for s in exporter.get_finished_spans()}
    assert names == {"outer", "inner"}


def test_get_tracer_auto_configures_if_nothing_configured_yet():
    # Regardless of prior test ordering, get_tracer must never raise -
    # this exercises the module-level, process-global tracer path (the
    # one tools/base.py actually uses), not a per-test isolated provider.
    tracer = get_tracer("test.tracer.auto")
    with tracer.start_as_current_span("x"):
        pass


def test_configure_in_memory_tracing_never_raises_when_called_repeatedly():
    """OpenTelemetry's global provider can only be set once per process;
    calling this repeatedly (as multiple test modules importing this
    project's own instrumentation will) must degrade gracefully rather
    than raise or silently break the caller.
    """
    for _ in range(3):
        provider, exporter = configure_in_memory_tracing()
        tracer = provider.get_tracer("test.tracer.repeat")
        with tracer.start_as_current_span("s"):
            pass
        assert len(exporter.get_finished_spans()) == 1
