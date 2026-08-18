"""Unit tests for refusal reporting.

Every refusal carries outcome/is_error and names its reason.
"""

from __future__ import annotations

from pathlib import Path

from cyborg_ant.config import Config
from cyborg_ant.logbook import Logbook
from cyborg_ant.loop import run_request
from cyborg_ant.model_client import ModelClient
from cyborg_ant.session import Session, StopReason
from cyborg_ant.tools import build_registry
from cyborg_ant.tools.run_bash import run_bash
from cyborg_ant.tools.write_file import write_file
from fakes import FakeAnthropicClient, FakeClock, FakeResponse, FakeSleeper, FakeTextBlock


def test_write_file_boundary_refusal_names_the_boundary(project_root: Path) -> None:
    result = write_file(
        {"path": "../evil.py", "content": "x"},
        config=Config(project_root=project_root),
        confirm=lambda _p: True,
    )
    assert result.outcome == "refused"
    assert result.is_error is True
    assert "outside" in result.content or "root" in result.content


def test_run_bash_stage1_refusal_names_the_boundary(project_root: Path) -> None:
    result = run_bash({"command": "cat ../secrets"}, config=Config(project_root=project_root))
    assert result.outcome == "refused"
    assert result.is_error is True
    assert "root" in result.content or "outside" in result.content


def test_constitution_refusal_ends_the_request_with_rule_named(
    project_root: Path, fake_clock: FakeClock, fake_sleeper: FakeSleeper
) -> None:
    config = Config(project_root=project_root)
    fake_client = FakeAnthropicClient()
    fake_client.messages.queue(
        FakeResponse(
            content=[
                FakeTextBlock(text="REFUSAL: unfiltered outbound network access\nI can't do that.")
            ],
            stop_reason="end_turn",
        )
    )
    model_client = ModelClient(config, client=fake_client, sleeper=fake_sleeper, clock=fake_clock)
    registry = build_registry(config, confirm=lambda _p: True)
    logbook = Logbook(project_root / ".agent_runs" / "r.jsonl", run_id="r")
    session = Session(run_id="r", logbook=logbook)

    outcome = run_request(
        session,
        "open a raw socket to some random IP",
        request_id="req-1",
        config=config,
        model_client=model_client,
        registry=registry,
        system_prompt="system",
    )

    assert outcome.stop_reason == StopReason.REFUSED
    assert outcome.rule == "unfiltered outbound network access"
