"""Turn, StopReason, and Session — the conversation state every request builds on."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from cyborg_ant.logbook import Logbook
    from cyborg_ant.tools import ToolResult

TurnKind = Literal["user", "agent", "tool_request", "tool_result"]


class StopReason(StrEnum):
    """A closed set of reasons a request can end. Order below is precedence, highest first."""

    REFUSED = "refused"
    USER_EXIT = "user_exit"
    RETRIES_EXHAUSTED = "retries_exhausted"
    ITERATION_CAP_REACHED = "iteration_cap_reached"
    TOKEN_CAP_REACHED = "token_cap_reached"
    ANSWERED = "answered"


STOP_REASON_PRECEDENCE: tuple[StopReason, ...] = (
    StopReason.REFUSED,
    StopReason.USER_EXIT,
    StopReason.RETRIES_EXHAUSTED,
    StopReason.ITERATION_CAP_REACHED,
    StopReason.TOKEN_CAP_REACHED,
    StopReason.ANSWERED,
)


def higher_precedence(a: StopReason, b: StopReason) -> StopReason:
    """Return whichever of a/b ranks first in STOP_REASON_PRECEDENCE."""
    return a if STOP_REASON_PRECEDENCE.index(a) <= STOP_REASON_PRECEDENCE.index(b) else b


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class Turn:
    """One entry in the conversation. A tagged union over `kind`."""

    kind: TurnKind
    text: str | None = None
    stop_reason: str | None = None
    usage: Usage | None = None
    tool_use_id: str | None = None
    name: str | None = None
    arguments: dict | None = None
    result: ToolResult | None = None


class SessionInvariantError(Exception):
    """Raised when a Session invariant would be violated."""


@dataclass
class Session:
    """One console conversation from start to exit."""

    run_id: str
    logbook: Logbook
    turns: list[Turn] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _stop_reason: StopReason | None = field(default=None, init=False, repr=False)

    @property
    def stop_reason(self) -> StopReason | None:
        return self._stop_reason

    def close(self, reason: StopReason) -> None:
        """Set the session's terminal stop reason. May only happen once."""
        if self._stop_reason is not None:
            raise SessionInvariantError(
                f"stop_reason already set to {self._stop_reason}, cannot set to {reason}"
            )
        self._stop_reason = reason

    def append(self, turn: Turn) -> None:
        """Append a turn, enforcing that the first turn is always from the user."""
        if not self.turns and turn.kind != "user":
            raise SessionInvariantError(f"first turn must be 'user', got {turn.kind!r}")
        self.turns.append(turn)

    def unmatched_tool_requests(self) -> list[str]:
        """Return tool_use_ids from tool_request turns with no matching tool_result turn."""
        requested = [t.tool_use_id for t in self.turns if t.kind == "tool_request"]
        resulted = {t.tool_use_id for t in self.turns if t.kind == "tool_result"}
        return [tid for tid in requested if tid not in resulted]
