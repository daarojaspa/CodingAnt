"""Unit tests for the write_file tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from cyborg_ant.config import Config
from cyborg_ant.tools.write_file import write_file


def _config(project_root: Path) -> Config:
    return Config(project_root=project_root)


def _always(answer: bool):
    return lambda _prompt: answer


def test_write_new_file_is_ok(project_root: Path) -> None:
    result = write_file(
        {"path": "log.py", "content": "print('hi')\n"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "ok"
    assert result.metadata["overwrote"] is False
    assert (project_root / "log.py").read_text() == "print('hi')\n"


def test_overwrite_is_reported(project_root: Path) -> None:
    (project_root / "log.py").write_text("old")
    result = write_file(
        {"path": "log.py", "content": "new"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "ok"
    assert result.metadata["overwrote"] is True
    assert (project_root / "log.py").read_text() == "new"


def test_outside_root_path_is_refused(project_root: Path) -> None:
    result = write_file(
        {"path": "../evil.py", "content": "x"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "refused"
    assert result.is_error is True


def test_agent_runs_path_is_refused(project_root: Path) -> None:
    result = write_file(
        {"path": ".agent_runs/tampered.jsonl", "content": "x"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "refused"


def test_directory_target_is_error_not_crash(project_root: Path) -> None:
    (project_root / "adir").mkdir()
    result = write_file(
        {"path": "adir", "content": "x"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "error"


def test_missing_parent_without_confirmation_is_refused_and_creates_nothing(
    project_root: Path,
) -> None:
    result = write_file(
        {"path": "sub/log.py", "content": "x"},
        config=_config(project_root),
        confirm=_always(False),
    )
    assert result.outcome == "refused"
    assert not (project_root / "sub").exists()


def test_missing_parent_with_confirmation_creates_only_needed_parents(project_root: Path) -> None:
    result = write_file(
        {"path": "sub/dir/log.py", "content": "x"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "ok"
    assert (project_root / "sub" / "dir" / "log.py").read_text() == "x"


def test_failure_before_rename_leaves_original_file_intact(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = project_root / "log.py"
    target.write_text("original")

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("cyborg_ant.tools.write_file.os.replace", _boom)

    result = write_file(
        {"path": "log.py", "content": "new content"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "error"
    assert target.read_text() == "original"
    # No orphaned temp file left behind in the target's directory.
    assert list(project_root.glob("tmp*")) == []


def test_permission_denial_returns_error_not_a_crash(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr("cyborg_ant.tools.write_file.tempfile.mkstemp", _boom)

    result = write_file(
        {"path": "log.py", "content": "x"},
        config=_config(project_root),
        confirm=_always(True),
    )
    assert result.outcome == "error"
    assert result.is_error is True
