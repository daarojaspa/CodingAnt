"""Reads a bounded, text-only slice of a file."""

from __future__ import annotations

from pathlib import Path

from cyborg_ant.boundary import require_inside_root
from cyborg_ant.config import Config
from cyborg_ant.errors import BoundaryViolationError
from cyborg_ant.tools import ToolResult

SCHEMA = {
    "name": "read_file",
    "description": (
        "Read a text file from the project and return its contents. Accepts either a path "
        "relative to the project root or an absolute path inside it. Large files are truncated "
        "to a fixed word ceiling and the result says so, including the file's full size. Binary "
        "files are refused — use run_bash with a tool like `file` or `head` to inspect those."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Path to the file, relative to the project root or absolute inside it."
                ),
            }
        },
        "required": ["path"],
    },
}


def read_file(arguments: dict, *, config: Config) -> ToolResult:
    path_str = arguments.get("path")
    if not isinstance(path_str, str):
        return ToolResult(outcome="invalid", content="read_file requires a string 'path'")

    try:
        target = require_inside_root(path_str, config.project_root)
    except BoundaryViolationError as exc:
        return ToolResult(outcome="refused", content=str(exc))

    existence_problem = _check_target(target, path_str)
    if existence_problem is not None:
        return existence_problem

    try:
        raw = target.read_bytes()
    except OSError as exc:
        return ToolResult(outcome="error", content=f"failed to read '{path_str}': {exc}")

    binary = _detect_binary(raw)
    if binary is not None:
        return ToolResult(
            outcome="refused",
            content=(
                f"'{path_str}' looks like a binary file ({binary}); refusing to read it as text"
            ),
        )

    return _bounded_result(raw.decode("utf-8"), config.read_word_ceiling)


def _check_target(target: Path, path_str: str) -> ToolResult | None:
    if not target.exists():
        return ToolResult(outcome="error", content=f"'{path_str}' does not exist")
    if target.is_dir():
        return ToolResult(outcome="error", content=f"'{path_str}' is a directory, not a file")
    return None


def _detect_binary(raw: bytes) -> str | None:
    if b"\x00" in raw[:8192]:
        return "NUL byte in the first 8 KB"
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return "not valid UTF-8"
    return None


def _bounded_result(text: str, word_ceiling: int) -> ToolResult:
    words = text.split()
    full_size = len(text.encode("utf-8"))
    if len(words) <= word_ceiling:
        metadata = {"truncated": False, "full_size_bytes": full_size, "detected_binary": False}
        return ToolResult(outcome="ok", content=text, metadata=metadata)

    truncated_text = " ".join(words[:word_ceiling])
    content = (
        f"{truncated_text}\n"
        f"[truncated: returned {word_ceiling} of {len(words)} words; file is {full_size} bytes]"
    )
    metadata = {"truncated": True, "full_size_bytes": full_size, "detected_binary": False}
    return ToolResult(outcome="ok", content=content, metadata=metadata)
