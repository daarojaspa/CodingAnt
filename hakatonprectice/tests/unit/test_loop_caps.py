"""Unit tests for the loop's two caps: the iteration cap and retry exhaustion, and their tie."""

from __future__ import annotations

from pathlib import Path

import anthropic
import httpx

from cyborg_ant.config import Config
from cyborg_ant.logbook import Logbook
from cyborg_ant.loop import run_request
from cyborg_ant.model_client import ModelClient
from cyborg_ant.session import Session, StopReason
from cyborg_ant.tools import build_registry
from fakes import (
    FakeAnthropicClient,
    FakeClock,
    FakeResponse,
    FakeSleeper,
    FakeTextBlock,
    FakeToolUseBlock,
)


def _connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=httpx.Request("POST", "https://example.com"))


def _session(project_root: Path) -> Session:
    logbook = Logbook(project_root / ".agent_runs" / "run.jsonl", run_id="r")
    return Session(run_id="r", logbook=logbook)


def test_iteration_cap_fires_at_the_configured_limit(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root, max_iterations=3)
    fake_client = FakeAnthropicClient()
    # Always returns a tool_use — never a plain-text answer — so the loop never ends on its own.
    for _ in range(3):
        fake_client.messages.queue(
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="a", name="write_file", input={"path": "a.py", "content": "x"}
                    )
                ],
                stop_reason="tool_use",
            )
        )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True)

    outcome = run_request(
        _session(project_root),
        "loop forever",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.ITERATION_CAP_REACHED
    assert outcome.iterations_used == 3


def test_retries_within_one_iteration_do_not_consume_an_iteration(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root, max_iterations=1, retry_attempts=3)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        _connection_error(),
        _connection_error(),
        FakeResponse(content=[FakeTextBlock(text="finally answered")], stop_reason="end_turn"),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True)

    outcome = run_request(
        _session(project_root),
        "retry then answer",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.ANSWERED
    assert outcome.iterations_used == 1  # two retries, still just the one iteration


def test_retries_exhausted_outranks_iteration_cap_on_the_last_iteration(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root, max_iterations=1, retry_attempts=3)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(_connection_error(), _connection_error(), _connection_error())
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True)

    outcome = run_request(
        _session(project_root),
        "always fails",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.RETRIES_EXHAUSTED
