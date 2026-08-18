"""Unit tests for the basic model/tool loop, using a fully fake model client."""

from __future__ import annotations

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


def _session(project_root: Path) -> Session:
    logbook = Logbook(project_root / ".agent_runs" / "run.jsonl", run_id="r")
    return Session(run_id="r", logbook=logbook)


def test_one_request_drives_tool_use_then_answer(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(
            content=[
                FakeToolUseBlock(
                    id="toolu_1", name="write_file", input={"path": "log.py", "content": "x"}
                )
            ],
            stop_reason="tool_use",
        ),
        FakeResponse(content=[FakeTextBlock(text="Done, wrote log.py.")], stop_reason="end_turn"),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _prompt: True)
    session = _session(project_root)

    outcome = run_request(
        session,
        "write a log.py",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.ANSWERED
    assert outcome.answer_text == "Done, wrote log.py."
    assert (project_root / "log.py").exists()


def test_every_tool_use_id_gets_exactly_one_result(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(
            content=[
                FakeToolUseBlock(id="a", name="write_file", input={"path": "a.py", "content": "1"}),
                FakeToolUseBlock(id="b", name="write_file", input={"path": "b.py", "content": "2"}),
            ],
            stop_reason="tool_use",
        ),
        FakeResponse(content=[FakeTextBlock(text="Both written.")], stop_reason="end_turn"),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _prompt: True)
    session = _session(project_root)

    run_request(
        session,
        "write two files",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert session.unmatched_tool_requests() == []
    tool_results = [t for t in session.turns if t.kind == "tool_result"]
    assert {t.tool_use_id for t in tool_results} == {"a", "b"}


def test_immediate_text_answer_with_no_tool_call(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(content=[FakeTextBlock(text="Hello there.")], stop_reason="end_turn"),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _prompt: True)
    session = _session(project_root)

    outcome = run_request(
        session,
        "hi",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.ANSWERED
    assert outcome.iterations_used == 1
