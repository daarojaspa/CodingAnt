"""Unit tests for the sandbox: bwrap argv, the startup probe, and run_bash's two-stage boundary.

SC-005's five escape attempts are split across this file and test_boundary.py /
test_tools_write_file.py: the two text/path-resolution and symlink cases are covered there
(boundary.is_inside and write_file already refuse them); this file covers the two run_bash
cases — stage 1's visible text pre-check and stage 2's kernel-level catch of an escape that is
invisible in the command text.
"""

from __future__ import annotations

from pathlib import Path

from cyborg_ant.config import Config
from cyborg_ant.sandbox import build_argv, probe
from cyborg_ant.tools.run_bash import run_bash


def test_build_argv_matches_the_fixed_policy(project_root: Path) -> None:
    argv = build_argv("echo hi", project_root)
    assert argv[0] == "bwrap"
    assert "--unshare-all" in argv
    assert "--die-with-parent" in argv
    assert argv[-3:] == ["/bin/sh", "-c", "echo hi"]
    assert str(project_root) in argv


def test_probe_succeeds_on_this_machine(project_root: Path) -> None:
    result = probe(project_root)
    assert result.available is True
    assert result.version


def test_stage1_refuses_a_visible_relative_escape(project_root: Path) -> None:
    config = Config(project_root=project_root)
    result = run_bash({"command": "cat ../secrets"}, config=config)
    assert result.outcome == "refused"
    assert result.metadata["blocked_by"] == "text"


def test_stage1_refuses_a_visible_absolute_escape(project_root: Path) -> None:
    config = Config(project_root=project_root)
    result = run_bash({"command": "cat /etc/shadow"}, config=config)
    assert result.outcome == "refused"
    assert result.metadata["blocked_by"] == "text"


def test_command_naming_agent_runs_is_refused(project_root: Path) -> None:
    config = Config(project_root=project_root)
    result = run_bash({"command": "cat .agent_runs/run.jsonl"}, config=config)
    assert result.outcome == "refused"
    assert result.metadata["blocked_by"] == "text"


def test_stage2_catches_an_escape_invisible_in_the_command_text(project_root: Path) -> None:
    config = Config(project_root=project_root)
    # $HOME is not a literal path in the command text — stage 1 cannot see it.
    result = run_bash({"command": "cat $HOME/.ssh/id_rsa"}, config=config)
    assert result.outcome == "error"
    assert result.metadata["blocked_by"] == "sandbox"


def test_stage2_catches_a_dynamically_built_path_via_eval(project_root: Path) -> None:
    config = Config(project_root=project_root)
    result = run_bash(
        {"command": "eval $(echo Y2F0IH4vLnNzaC9pZF9yc2E= | base64 -d)"}, config=config
    )
    assert result.outcome == "error"
    assert result.metadata["blocked_by"] == "sandbox"


def test_ordinary_command_inside_root_succeeds(project_root: Path) -> None:
    config = Config(project_root=project_root)
    (project_root / "hello.txt").write_text("hi")
    result = run_bash({"command": "cat hello.txt"}, config=config)
    assert result.outcome == "ok"
    assert "hi" in result.content


def test_nonzero_exit_reports_both_streams_and_exit_status(project_root: Path) -> None:
    config = Config(project_root=project_root)
    result = run_bash({"command": "echo out; echo err >&2; exit 3"}, config=config)
    assert result.outcome == "error"
    assert result.metadata["exit_code"] == 3
    assert "out" in result.content
    assert "err" in result.content


def test_timeout_is_reported_and_not_a_crash(project_root: Path) -> None:
    config = Config(project_root=project_root, command_timeout_seconds=1.0)
    result = run_bash({"command": "sleep 5"}, config=config)
    assert result.outcome == "error"
    assert result.metadata["timed_out"] is True
