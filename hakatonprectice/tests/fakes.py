"""Fake test doubles: clock, sleeper, and Anthropic client. No real API call, no real sleeping."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeClock:
    """A controllable monotonic clock. Advances only when told to."""

    _now: float = 0.0

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


@dataclass
class FakeSleeper:
    """Records requested sleep durations and advances a FakeClock instead of really sleeping."""

    clock: FakeClock
    calls: list[float] = field(default_factory=list)

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.clock.advance(seconds)


@dataclass
class FakeUsage:
    input_tokens: int = 10
    output_tokens: int = 10
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class FakeResponse:
    content: list
    stop_reason: str = "end_turn"
    usage: FakeUsage = field(default_factory=FakeUsage)


class FakeMessages:
    """Stands in for `anthropic.Anthropic().messages`. Scripted with a queue of results."""

    def __init__(self) -> None:
        self._queue: list[FakeResponse | Exception] = []

    def queue(self, *items: FakeResponse | Exception) -> None:
        self._queue.extend(items)

    def create(self, **kwargs: object) -> FakeResponse:
        if not self._queue:
            raise AssertionError("FakeMessages queue exhausted — script more responses")
        item = self._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeAnthropicClient:
    """Stands in for `anthropic.Anthropic()`. Never makes a real API call."""

    def __init__(self) -> None:
        self.messages = FakeMessages()
