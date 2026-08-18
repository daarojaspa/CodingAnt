"""Bounded geometric backoff with an injected sleeper and clock."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cyborg_ant.errors import RetriesExhaustedError

Sleeper = Callable[[float], None]
Clock = Callable[[], float]
OnRetry = Callable[[int, int, str, float], None]


@dataclass
class RetryPolicy:
    attempts: int
    base_seconds: float
    ratio: float


def call_with_retry[T](
    func: Callable[[], T],
    *,
    retryable: tuple[type[Exception], ...],
    policy: RetryPolicy,
    sleeper: Sleeper,
    clock: Clock,
    on_retry: OnRetry | None = None,
) -> T:
    """Call func, retrying up to policy.attempts total on the enumerated retryable types.

    Returns func()'s result on success. Raises RetriesExhaustedError — carrying the measured
    wait sequence, not the nominal one — once the attempt cap is reached without success. Any
    non-retryable exception propagates immediately, unretried.
    """
    waits: list[float] = []
    wait = policy.base_seconds
    last_error: Exception | None = None

    for attempt in range(1, policy.attempts + 1):
        try:
            return func()
        except retryable as exc:
            last_error = exc
            if attempt == policy.attempts:
                break
            measured = _sleep_and_measure(sleeper, clock, wait)
            waits.append(measured)
            if on_retry is not None:
                on_retry(attempt, policy.attempts, type(exc).__name__, measured)
            wait *= policy.ratio

    raise RetriesExhaustedError(
        f"exhausted {policy.attempts} attempts: {last_error}",
        attempts=policy.attempts,
        waits=waits,
    ) from last_error


def _sleep_and_measure(sleeper: Sleeper, clock: Clock, wait: float) -> float:
    start = clock()
    sleeper(wait)
    return clock() - start
