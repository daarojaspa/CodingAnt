"""Unit tests for bounded geometric backoff, using the injected sleeper and clock."""

from __future__ import annotations

import pytest

from cyborg_ant.errors import RetriesExhaustedError
from cyborg_ant.retry import RetryPolicy, call_with_retry


class _Flaky(Exception):
    pass


class _Other(Exception):
    pass


def test_wait_sequence_is_base_then_base_times_ratio(fake_clock, fake_sleeper) -> None:
    policy = RetryPolicy(attempts=3, base_seconds=1.0, ratio=2.0)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        raise _Flaky("boom")

    with pytest.raises(RetriesExhaustedError) as exc_info:
        call_with_retry(
            flaky, retryable=(_Flaky,), policy=policy, sleeper=fake_sleeper, clock=fake_clock
        )

    assert calls["n"] == 3
    assert fake_sleeper.calls == [1.0, 2.0]
    assert exc_info.value.attempts == 3
    assert exc_info.value.waits == [1.0, 2.0]


def test_succeeds_without_retry_when_first_attempt_works(fake_clock, fake_sleeper) -> None:
    policy = RetryPolicy(attempts=3, base_seconds=1.0, ratio=2.0)
    result = call_with_retry(
        lambda: "ok", retryable=(_Flaky,), policy=policy, sleeper=fake_sleeper, clock=fake_clock
    )
    assert result == "ok"
    assert fake_sleeper.calls == []


def test_succeeds_after_one_retry(fake_clock, fake_sleeper) -> None:
    policy = RetryPolicy(attempts=3, base_seconds=1.0, ratio=2.0)
    attempts = iter([_Flaky("first"), "ok"])

    def flaky():
        item = next(attempts)
        if isinstance(item, Exception):
            raise item
        return item

    result = call_with_retry(
        flaky, retryable=(_Flaky,), policy=policy, sleeper=fake_sleeper, clock=fake_clock
    )
    assert result == "ok"
    assert fake_sleeper.calls == [1.0]


def test_only_the_enumerated_retryable_types_are_retried(fake_clock, fake_sleeper) -> None:
    policy = RetryPolicy(attempts=3, base_seconds=1.0, ratio=2.0)

    def raises_other():
        raise _Other("nope")

    with pytest.raises(_Other):
        call_with_retry(
            raises_other,
            retryable=(_Flaky,),
            policy=policy,
            sleeper=fake_sleeper,
            clock=fake_clock,
        )
    assert fake_sleeper.calls == []  # not retried at all — not in the retryable set


def test_a_returned_value_is_never_reinspected_or_retried(fake_clock, fake_sleeper) -> None:
    """call_with_retry only reacts to raised exceptions — a normal return value, including a
    refused outcome, passes straight through without inspection (spec Assumptions)."""
    policy = RetryPolicy(attempts=3, base_seconds=1.0, ratio=2.0)
    calls = {"n": 0}

    def refused():
        calls["n"] += 1
        return {"outcome": "refused"}

    result = call_with_retry(
        refused, retryable=(_Flaky,), policy=policy, sleeper=fake_sleeper, clock=fake_clock
    )
    assert result == {"outcome": "refused"}
    assert calls["n"] == 1
    assert fake_sleeper.calls == []


def test_on_retry_callback_receives_attempt_and_measured_wait(fake_clock, fake_sleeper) -> None:
    policy = RetryPolicy(attempts=2, base_seconds=1.0, ratio=2.0)
    seen = []

    def flaky():
        raise _Flaky("boom")

    with pytest.raises(RetriesExhaustedError):
        call_with_retry(
            flaky,
            retryable=(_Flaky,),
            policy=policy,
            sleeper=fake_sleeper,
            clock=fake_clock,
            on_retry=lambda attempt, of, error_type, wait: seen.append(
                (attempt, of, error_type, wait)
            ),
        )
    assert seen == [(1, 2, "_Flaky", 1.0)]
