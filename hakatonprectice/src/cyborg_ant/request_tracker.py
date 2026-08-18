"""The outcome of one request, and the tracker that accumulates it into `request_end`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from cyborg_ant.model_client import ModelResponse
from cyborg_ant.session import Session, StopReason


@dataclass
class RequestOutcome:
    stop_reason: StopReason
    answer_text: str | None
    iterations_used: int
    truncated: bool = False
    rule: str | None = None


@dataclass
class RequestTracker:
    """Accumulates the metrics `request_end` reports, and emits it exactly once."""

    session: Session
    request_id: str
    clock: Callable[[], float]
    start: float = field(init=False)
    total_output_tokens: int = 0
    max_response_tokens: int = 0
    truncated: bool = False
    retry_attempts: int = 0
    retry_waits: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.start = self.clock()

    def record_response(self, response: ModelResponse) -> None:
        tokens = response.usage["output_tokens"]
        self.total_output_tokens += tokens
        self.max_response_tokens = max(self.max_response_tokens, tokens)
        if response.stop_reason == "max_tokens":
            self.truncated = True

    def record_retry(self, wait: float) -> None:
        self.retry_attempts += 1
        self.retry_waits.append(wait)

    def finish(
        self,
        stop_reason: StopReason,
        answer_text: str | None,
        iterations_used: int,
        *,
        rule: str | None = None,
        retry_attempts: int | None = None,
        retry_waits: list[float] | None = None,
    ) -> RequestOutcome:
        attempts = self.retry_attempts if retry_attempts is None else retry_attempts
        waits = self.retry_waits if retry_waits is None else retry_waits
        self.session.logbook.emit(
            "request_end",
            request_id=self.request_id,
            stop_reason=stop_reason.value,
            iterations_used=iterations_used,
            wall_clock_seconds=self.clock() - self.start,
            total_output_tokens=self.total_output_tokens,
            max_response_tokens=self.max_response_tokens,
            retry_attempts=attempts,
            retry_waits=waits,
            **({"rule": rule} if rule is not None else {}),
        )
        return RequestOutcome(stop_reason, answer_text, iterations_used, self.truncated, rule)
