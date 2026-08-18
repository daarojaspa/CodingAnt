"""Writes a file atomically, gated on the parent-folder confirmation rule."""

from __future__ import annotations

import difflib
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from cyborg_ant.boundary import require_inside_root
from cyborg_ant.config import Config
from cyborg_ant.errors import BoundaryViolationError
from cyborg_ant.tools import ToolResult

ConfirmFn = Callable[[str], bool]

SCHEMA = {
    "name": "write_file",
    "description": (
        "Write content to a file in the project, replacing it if it exists. The write is "
        "atomic: content is staged in a temporary file and swapped into place, so an "
        "interrupted write never leaves a partial file. If the parent folders do not exist, "
        "the write pauses and asks the user to confirm creating them; without confirmation "
        "it is refused."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to write, relative to the project root or absolute inside it.",
            },
            "content": {
                "type": "string",
                "description": "The full new contents of the file.",
            },
        },
        "required": ["path", "content"],
    },
}


def write_file(arguments: dict, *, config: Config, confirm: ConfirmFn) -> ToolResult:
    validated = _validate_arguments(arguments)
    if isinstance(validated, ToolResult):
        return validated
    path_str, content = validated

    try:
        target = require_inside_root(path_str, config.project_root, deny_agent_runs=True)
    except BoundaryViolationError as exc:
        return ToolResult(outcome="refused", content=str(exc))

    if target.exists() and target.is_dir():
        return ToolResult(outcome="error", content=f"'{path_str}' is a directory, not a file")

    parents = _ensure_parent(target, path_str, config, confirm)
    if isinstance(parents, ToolResult):
        return parents

    return _write_and_report(target, path_str, content, parents)


def _validate_arguments(arguments: dict) -> tuple[str, str] | ToolResult:
    path_str = arguments.get("path")
    content = arguments.get("content")
    if not isinstance(path_str, str) or not isinstance(content, str):
        return ToolResult(
            outcome="invalid", content="write_file requires a string 'path' and 'content'"
        )
    return path_str, content


def _ensure_parent(
    target: Path, path_str: str, config: Config, confirm: ConfirmFn
) -> list[str] | ToolResult:
    """Create the target's parent folders if needed, gated on user confirmation."""
    if target.parent.exists():
        return []

    gate = _confirm_parent_creation(target, path_str, config, confirm)
    if gate is None:
        return ToolResult(
            outcome="refused",
            content=f"parent folder for '{path_str}' does not exist and was not confirmed",
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return ToolResult(
            outcome="error", content=f"failed to create parent folders for '{path_str}': {exc}"
        )
    return gate


def _write_and_report(
    target: Path, path_str: str, content: str, created_parents: list[str]
) -> ToolResult:
    overwrote = target.exists()
    try:
        bytes_written = _atomic_write(target, content)
    except OSError as exc:
        return ToolResult(outcome="error", content=f"failed to write '{path_str}': {exc}")

    verb = "Overwrote" if overwrote else "Wrote"
    return ToolResult(
        outcome="ok",
        content=f"{verb} {bytes_written} bytes to {path_str}.",
        metadata={
            "created_parents": created_parents,
            "bytes_written": bytes_written,
            "overwrote": overwrote,
        },
    )


def _confirm_parent_creation(
    target: Path, path_str: str, config: Config, confirm: ConfirmFn
) -> list[str] | None:
    """Ask the user before creating missing parent folders. Default is no."""
    missing: list[str] = []
    walker = target.parent
    while not walker.exists():
        missing.append(walker.name)
        walker = walker.parent
    missing.reverse()

    deepest_existing = walker
    siblings = [p.name for p in deepest_existing.iterdir()] if deepest_existing.exists() else []
    close_matches = difflib.get_close_matches(missing[0], siblings, n=3, cutoff=config.typo_cutoff)

    missing_repr = "/".join(missing) + "/"
    lines = [f"The folder '{missing_repr}' does not exist."]
    for match in close_matches:
        lines.append(f"  Did you mean '{match}'?  (existing, close match)")
    lines.append(f"Create '{missing_repr}' and write {target.name} into it?  [y/N]")

    if confirm("\n".join(lines)):
        return missing
    return None


def _atomic_write(target: Path, content: str) -> int:
    """mkstemp -> write -> fsync -> os.replace, unlinking the temp file on any failure."""
    fd, tmp_path = tempfile.mkstemp(dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return len(content.encode("utf-8"))
