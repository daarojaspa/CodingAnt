"""Unit tests for path resolution and the project-root boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from cyborg_ant.boundary import is_inside, is_under_agent_runs, require_inside_root
from cyborg_ant.errors import BoundaryViolationError


def test_is_inside_for_path_inside_root(project_root: Path) -> None:
    target = project_root / "src" / "main.py"
    target.parent.mkdir(parents=True)
    target.write_text("x")
    assert is_inside(target, project_root) is True


def test_root_itself_counts_as_inside(project_root: Path) -> None:
    assert is_inside(project_root, project_root) is True


def test_relative_dotdot_escape_is_outside(project_root: Path) -> None:
    assert is_inside(Path("../outside.txt"), project_root) is False


def test_symlink_escape_is_outside(
    project_root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside_dir = tmp_path_factory.mktemp("outside")
    secret = outside_dir / "secret.txt"
    secret.write_text("nope")
    link = project_root / "link.txt"
    link.symlink_to(secret)
    assert is_inside(link, project_root) is False


def test_nonexistent_target_resolves_against_nearest_existing_ancestor(project_root: Path) -> None:
    not_yet_created = project_root / "new_dir" / "new_file.py"
    assert is_inside(not_yet_created, project_root) is True


def test_agent_runs_is_under_agent_runs(project_root: Path) -> None:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    assert is_under_agent_runs(log_path, project_root) is True


def test_ordinary_path_is_not_under_agent_runs(project_root: Path) -> None:
    assert is_under_agent_runs(project_root / "log.py", project_root) is False


def test_require_inside_root_raises_for_outside_path(project_root: Path) -> None:
    with pytest.raises(BoundaryViolationError):
        require_inside_root("../../etc/passwd", project_root)


def test_require_inside_root_raises_for_agent_runs_when_denied(project_root: Path) -> None:
    with pytest.raises(BoundaryViolationError):
        require_inside_root(".agent_runs/run.jsonl", project_root, deny_agent_runs=True)


def test_require_inside_root_allows_agent_runs_when_not_denied(project_root: Path) -> None:
    resolved = require_inside_root(".agent_runs/run.jsonl", project_root, deny_agent_runs=False)
    assert resolved == (project_root / ".agent_runs" / "run.jsonl").resolve()


def test_require_inside_root_returns_resolved_path_for_valid_target(project_root: Path) -> None:
    resolved = require_inside_root("log.py", project_root)
    assert resolved == (project_root / "log.py").resolve()
