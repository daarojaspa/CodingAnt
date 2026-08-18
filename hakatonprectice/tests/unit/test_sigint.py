"""Unit tests for the SIGINT stop path: session_end always closes with a stop reason."""

from __future__ import annotations

import json
from pathlib import Path

from cyborg_ant.__main__ import _run_session
from cyborg_ant.config import Config
from cyborg_ant.logbook import Logbook
from cyborg_ant.session import Session


def _session(project_root: Path) -> tuple[Session, Path]:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    logbook = Logbook(log_path, run_id="r")
    return Session(run_id="r", logbook=logbook), log_path


def _read_events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text().splitlines() if line]


def test_keyboard_interrupt_closes_the_session_with_via_sigint(project_root: Path) -> None:
    session, log_path = _session(project_root)
    config = Config(project_root=project_root)

    def interrupting_repl_loop(*_args: object) -> None:
        counter = _args[-1]
        counter[0] = 2  # pretend two requests completed before the interrupt landed
        raise KeyboardInterrupt

    _run_session(
        session, config, model_client=object(), registry=object(), repl_loop=interrupting_repl_loop
    )

    events = _read_events(log_path)
    session_end = next(e for e in events if e["event"] == "session_end")
    assert session_end["via"] == "sigint"
    assert session_end["requests"] == 2


def test_normal_exit_closes_the_session_with_via_exit_word(project_root: Path) -> None:
    session, log_path = _session(project_root)
    config = Config(project_root=project_root)

    def clean_repl_loop(*_args: object) -> None:
        return None

    _run_session(
        session, config, model_client=object(), registry=object(), repl_loop=clean_repl_loop
    )

    events = _read_events(log_path)
    session_end = next(e for e in events if e["event"] == "session_end")
    assert session_end["via"] == "exit_word"
