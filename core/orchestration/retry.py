"""Generic retry-with-exponential-backoff, per the project's failure
recovery rule (spec section 31): retries are bounded and back off, they
never loop forever.
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    def __init__(self, attempts: int, last_error: Exception):
        super().__init__(f"Gave up after {attempts} attempts; last error: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


def retry_with_backoff(
    fn: Callable[[], T],
    max_attempts: int = 3,
    base_delay_seconds: float = 0.1,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn`` up to ``max_attempts`` times, sleeping
    ``base_delay_seconds * backoff_factor**attempt`` between attempts.
    Raises ``RetryExhaustedError`` (wrapping the last exception) if every
    attempt fails. ``sleep`` is injectable so tests don't have to actually
    wait.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except retryable_exceptions as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                sleep(base_delay_seconds * (backoff_factor ** attempt))

    raise RetryExhaustedError(max_attempts, last_error)
