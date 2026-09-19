import pytest

from core.orchestration.retry import RetryExhaustedError, retry_with_backoff


def test_returns_result_on_first_success():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    assert retry_with_backoff(fn, max_attempts=3, sleep=lambda s: None) == "ok"
    assert len(calls) == 1


def test_retries_until_success():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("transient")
        return "recovered"

    result = retry_with_backoff(flaky, max_attempts=5, sleep=lambda s: None)
    assert result == "recovered"
    assert attempts["count"] == 3


def test_raises_retry_exhausted_after_max_attempts():
    def always_fails():
        raise ValueError("permanent")

    with pytest.raises(RetryExhaustedError) as exc_info:
        retry_with_backoff(always_fails, max_attempts=3, sleep=lambda s: None)
    assert exc_info.value.attempts == 3


def test_backoff_delays_grow_exponentially():
    delays = []

    def always_fails():
        raise ValueError("boom")

    with pytest.raises(RetryExhaustedError):
        retry_with_backoff(
            always_fails, max_attempts=4, base_delay_seconds=1.0, backoff_factor=2.0,
            sleep=lambda s: delays.append(s),
        )
    assert delays == [1.0, 2.0, 4.0]


def test_only_retries_specified_exception_types():
    def raises_type_error():
        raise TypeError("not retryable here")

    with pytest.raises(TypeError):
        retry_with_backoff(
            raises_type_error, max_attempts=3, retryable_exceptions=(ValueError,), sleep=lambda s: None,
        )


def test_rejects_non_positive_max_attempts():
    with pytest.raises(ValueError):
        retry_with_backoff(lambda: None, max_attempts=0)
