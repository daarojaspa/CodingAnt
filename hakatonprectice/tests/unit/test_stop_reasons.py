"""Unit tests for the StopReason precedence order (research §R9)."""

from __future__ import annotations

import itertools

import pytest

from cyborg_ant.session import STOP_REASON_PRECEDENCE, StopReason, higher_precedence

EXPECTED_ORDER = (
    StopReason.REFUSED,
    StopReason.USER_EXIT,
    StopReason.RETRIES_EXHAUSTED,
    StopReason.ITERATION_CAP_REACHED,
    StopReason.TOKEN_CAP_REACHED,
    StopReason.ANSWERED,
)


def test_precedence_tuple_matches_the_full_specified_order() -> None:
    assert STOP_REASON_PRECEDENCE == EXPECTED_ORDER


@pytest.mark.parametrize(
    ("higher", "lower"),
    list(itertools.combinations(EXPECTED_ORDER, 2)),
)
def test_higher_precedence_picks_the_earlier_reason_in_either_argument_order(
    higher: StopReason, lower: StopReason
) -> None:
    assert higher_precedence(higher, lower) == higher
    assert higher_precedence(lower, higher) == higher


def test_higher_precedence_is_stable_for_equal_reasons() -> None:
    assert higher_precedence(StopReason.ANSWERED, StopReason.ANSWERED) == StopReason.ANSWERED
