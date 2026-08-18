"""Unit tests for the 6000-token response cap: truncation is detected and reported, never hidden."""

from __future__ import annotations

import json
from pathlib import Path

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


def _session(project_root: Path) -> tuple[Session, Path]:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    logbook = Logbook(log_path, run_id="r")
    return Session(run_id="r", logbook=logbook), log_path


def _read_events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text().splitlines() if line]


def test_max_tokens_with_no_tool_call_is_reported_as_cut_short_not_answered(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root, max_tokens=6000)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(content=[FakeTextBlock(text="cut off mid-sent")], stop_reason="max_tokens"),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True)
    session, _ = _session(project_root)

    outcome = run_request(
        session,
        "write something very long",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.TOKEN_CAP_REACHED
    assert outcome.stop_reason != StopReason.ANSWERED
    assert outcome.truncated is True


def test_max_response_tokens_lands_in_request_end(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(content=[FakeTextBlock(text="hi")], stop_reason="end_turn"),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True)
    session, log_path = _session(project_root)

    run_request(
        session,
        "hello",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    request_end = next(e for e in _read_events(log_path) if e["event"] == "request_end")
    assert "max_response_tokens" in request_end
    assert request_end["max_response_tokens"] == 10  # FakeUsage default output_tokens


def test_max_tokens_with_a_tool_call_continues_but_flags_truncated(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(
            content=[
                FakeToolUseBlock(id="a", name="write_file", input={"path": "a.py", "content": "x"})
            ],
            stop_reason="max_tokens",
        ),
        FakeResponse(content=[FakeTextBlock(text="done")], stop_reason="end_turn"),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True)
    session, _ = _session(project_root)

    outcome = run_request(
        session,
        "do something",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.ANSWERED
    assert outcome.truncated is True
