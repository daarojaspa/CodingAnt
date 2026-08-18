"""Unit tests for the read_file tool."""

from __future__ import annotations

from pathlib import Path

from cyborg_ant.config import Config
from cyborg_ant.tools.read_file import read_file


def _config(project_root: Path, **overrides: object) -> Config:
    return Config(project_root=project_root, **overrides)  # type: ignore[arg-type]


def test_reads_a_bare_filename_relative_to_project_root(project_root: Path) -> None:
    (project_root / "log.py").write_text("print(1)\n")
    result = read_file({"path": "log.py"}, config=_config(project_root))
    assert result.outcome == "ok"
    assert result.content == "print(1)\n"


def test_large_file_is_truncated_and_says_so_with_full_size(project_root: Path) -> None:
    text = " ".join(f"word{i}" for i in range(50))
    (project_root / "big.txt").write_text(text)
    result = read_file({"path": "big.txt"}, config=_config(project_root, read_word_ceiling=10))
    assert result.outcome == "ok"
    assert result.metadata["truncated"] is True
    assert "truncated" in result.content
    assert str(result.metadata["full_size_bytes"]) in result.content


def test_small_file_is_not_truncated(project_root: Path) -> None:
    (project_root / "small.txt").write_text("just a few words here")
    result = read_file({"path": "small.txt"}, config=_config(project_root, read_word_ceiling=100))
    assert result.metadata["truncated"] is False


def test_binary_file_is_refused(project_root: Path) -> None:
    (project_root / "bin.dat").write_bytes(b"\x00\x01\x02binary\xff\xfe")
    result = read_file({"path": "bin.dat"}, config=_config(project_root))
    assert result.outcome == "refused"
    assert result.is_error is True


def test_missing_file_is_error_not_crash(project_root: Path) -> None:
    result = read_file({"path": "does_not_exist.txt"}, config=_config(project_root))
    assert result.outcome == "error"


def test_directory_target_is_error(project_root: Path) -> None:
    (project_root / "adir").mkdir()
    result = read_file({"path": "adir"}, config=_config(project_root))
    assert result.outcome == "error"


def test_outside_root_path_is_refused(project_root: Path) -> None:
    result = read_file({"path": "../../etc/passwd"}, config=_config(project_root))
    assert result.outcome == "refused"
