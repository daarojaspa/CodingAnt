"""Integration test for the three-tool chain: read -> write -> run within one request."""

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


def test_read_write_run_chain_in_one_request(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    (project_root / "log.py").write_text("print('v1')\n")
    config = Config(project_root=project_root)

    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(
            content=[
                FakeToolUseBlock(id="r1", name="read_file", input={"path": "log.py"}),
                FakeToolUseBlock(
                    id="w1",
                    name="write_file",
                    input={"path": "log.py", "content": "print('v2')\n"},
                ),
                FakeToolUseBlock(id="x1", name="run_bash", input={"command": "python3 log.py"}),
            ],
            stop_reason="tool_use",
        ),
        FakeResponse(
            content=[FakeTextBlock(text="Updated and ran log.py: v2")], stop_reason="end_turn"
        ),
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True, sandbox_available=True)
    logbook = Logbook(project_root / ".agent_runs" / "r.jsonl", run_id="r")
    session = Session(run_id="r", logbook=logbook)

    outcome = run_request(
        session,
        "add v2 and run it",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.ANSWERED
    assert (project_root / "log.py").read_text() == "print('v2')\n"
    assert session.unmatched_tool_requests() == []

    tool_results = [t for t in session.turns if t.kind == "tool_result"]
    assert [t.tool_use_id for t in tool_results] == ["r1", "w1", "x1"]
    assert tool_results[0].result.outcome == "ok"  # read_file saw the original content
    assert "v1" in tool_results[0].result.content
    assert tool_results[1].result.outcome == "ok"  # write_file
    assert tool_results[2].result.outcome == "ok"  # run_bash printed v2
    assert "v2" in tool_results[2].result.content
