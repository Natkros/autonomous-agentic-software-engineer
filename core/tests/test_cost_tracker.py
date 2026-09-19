from core.providers.cost_tracker import CostTracker, estimate_tokens


def test_estimate_tokens_is_roughly_four_chars_per_token():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100


def test_mock_model_calls_are_tracked_at_zero_cost():
    tracker = CostTracker()
    tracker.record(model="mock", input_tokens=1000, output_tokens=500, latency_ms=1.0)
    assert tracker.total_cost_usd == 0.0


def test_known_model_pricing_is_applied():
    tracker = CostTracker()
    tracker.record(model="claude-sonnet-4-5-20250929", input_tokens=1_000_000, output_tokens=1_000_000, latency_ms=100.0)
    # $3/1M input + $15/1M output = $18 for this call
    assert round(tracker.total_cost_usd, 2) == 18.00


def test_unknown_model_defaults_to_zero_cost_rather_than_guessing():
    tracker = CostTracker()
    tracker.record(model="some-future-model", input_tokens=1000, output_tokens=1000, latency_ms=1.0)
    assert tracker.total_cost_usd == 0.0


def test_totals_accumulate_across_multiple_calls():
    tracker = CostTracker()
    tracker.record(model="mock", input_tokens=100, output_tokens=50, latency_ms=1.0)
    tracker.record(model="mock", input_tokens=200, output_tokens=100, latency_ms=2.0)
    assert tracker.call_count == 2
    assert tracker.total_tokens == 450


def test_calls_property_returns_a_copy_not_the_internal_list():
    tracker = CostTracker()
    tracker.record(model="mock", input_tokens=1, output_tokens=1, latency_ms=1.0)
    calls = tracker.calls
    calls.append("not a real call")
    assert tracker.call_count == 1
