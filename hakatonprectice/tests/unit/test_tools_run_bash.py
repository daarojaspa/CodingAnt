"""Unit tests for the run_bash tool's execution behaviour (exit codes, output caps, timeout)."""

from __future__ import annotations

from pathlib import Path

from cyborg_ant.config import Config
from cyborg_ant.tools.run_bash import run_bash


def test_exit_zero_is_ok(project_root: Path) -> None:
    result = run_bash({"command": "true"}, config=Config(project_root=project_root))
    assert result.outcome == "ok"
    assert result.metadata["exit_code"] == 0


def test_nonzero_exit_returns_stdout_stderr_and_exit_status(project_root: Path) -> None:
    result = run_bash(
        {"command": "echo out-marker; echo err-marker >&2; exit 7"},
        config=Config(project_root=project_root),
    )
    assert result.outcome == "error"
    assert result.metadata["exit_code"] == 7
    assert "out-marker" in result.content
    assert "err-marker" in result.content
    assert "7" in result.content


def test_timeout_is_error_with_timed_out_metadata(project_root: Path) -> None:
    config = Config(project_root=project_root, command_timeout_seconds=1.0)
    result = run_bash({"command": "sleep 5"}, config=config)
    assert result.outcome == "error"
    assert result.metadata["timed_out"] is True
    assert result.metadata["exit_code"] is None


def test_stdout_over_8kb_is_capped_with_true_length_stated(project_root: Path) -> None:
    result = run_bash(
        {"command": "head -c 20000 /dev/zero | tr '\\0' 'a'"},
        config=Config(project_root=project_root),
    )
    assert result.outcome == "ok"
    assert "truncated" in result.content
    assert "20000" in result.content


def test_stderr_over_8kb_is_capped_with_true_length_stated(project_root: Path) -> None:
    result = run_bash(
        {"command": "head -c 20000 /dev/zero | tr '\\0' 'a' 1>&2"},
        config=Config(project_root=project_root),
    )
    assert result.outcome == "ok"
    assert "truncated" in result.content
    assert "20000" in result.content
