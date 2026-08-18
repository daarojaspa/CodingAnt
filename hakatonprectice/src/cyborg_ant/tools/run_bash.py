"""Runs one shell command under the sandbox with a timeout."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path

from cyborg_ant.boundary import is_under_agent_runs, require_inside_root
from cyborg_ant.config import Config
from cyborg_ant.errors import BoundaryViolationError
from cyborg_ant.sandbox import build_argv
from cyborg_ant.tools import ToolResult

SCHEMA = {
    "name": "run_bash",
    "description": (
        "Run one shell command inside the project folder and return its standard output, "
        "standard error, and exit status. The command runs with the project folder as its "
        "working directory and cannot read or write anything outside it — paths outside the "
        "project simply do not exist from the command's point of view. There is no network "
        "access. Commands are cut off after a time limit and the timeout is reported as an "
        "ordinary result."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "The shell command to run, executed with /bin/sh -c inside the project folder."
                ),
            }
        },
        "required": ["command"],
    },
}

_TOKEN_SPLIT = re.compile(r"[\s|;&]+")
_SANDBOX_DENIAL_PATTERNS = (
    "read-only file system",
    "permission denied",
    "no such file or directory",
    "operation not permitted",
)


def run_bash(arguments: dict, *, config: Config) -> ToolResult:
    command = arguments.get("command")
    if not isinstance(command, str):
        return ToolResult(outcome="invalid", content="run_bash requires a string 'command'")

    refusal = _stage1_text_precheck(command, config.project_root)
    if refusal is not None:
        return refusal

    return _execute_sandboxed(command, config)


def _stage1_text_precheck(command: str, root: Path) -> ToolResult | None:
    """Refuse before execution if a path-like token in the command text resolves outside root."""
    for token in _extract_path_like_tokens(command):
        if is_under_agent_runs(Path(token), root):
            return ToolResult(
                outcome="refused",
                content=f"command references '{token}', which is inside .agent_runs/",
                metadata={"blocked_by": "text"},
            )
        try:
            require_inside_root(token, root)
        except BoundaryViolationError:
            return ToolResult(
                outcome="refused",
                content=f"command references '{token}', which resolves outside the project root",
                metadata={"blocked_by": "text"},
            )
    return None


def _extract_path_like_tokens(command: str) -> list[str]:
    tokens = (t.strip("'\"") for t in _TOKEN_SPLIT.split(command))
    return [
        t
        for t in tokens
        if t and not t.startswith("-") and _looks_like_a_path(t) and not _is_device_path(t)
    ]


def _looks_like_a_path(token: str) -> bool:
    return "/" in token or token in (".", "..") or ".agent_runs" in token


def _is_device_path(token: str) -> bool:
    """`/dev/*` is a synthetic device the sandbox itself provides, not a data escape route."""
    return token.startswith("/dev/")


def _execute_sandboxed(command: str, config: Config) -> ToolResult:
    """Run the sandboxed command in its own process group so an interrupt kills the whole tree."""
    argv = build_argv(command, config.project_root)
    start = time.monotonic()
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=config.project_root,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=config.command_timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        return _timeout_result(config.command_timeout_seconds, time.monotonic() - start)
    except KeyboardInterrupt:
        _kill_process_group(proc)
        raise

    return _build_result(proc.returncode, stdout, stderr, time.monotonic() - start)


def _kill_process_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def _timeout_result(timeout_seconds: float, duration: float) -> ToolResult:
    return ToolResult(
        outcome="error",
        content=f"command timed out after {timeout_seconds}s",
        metadata={
            "timed_out": True,
            "duration_seconds": duration,
            "blocked_by": None,
            "exit_code": None,
        },
    )


def _build_result(returncode: int, stdout: str, stderr: str, duration: float) -> ToolResult:
    formatted_stdout = _format_stream("stdout", stdout)
    formatted_stderr = _format_stream("stderr", stderr)
    blocked_by = "sandbox" if returncode != 0 and _looks_like_sandbox_denial(stderr) else None

    return ToolResult(
        outcome="ok" if returncode == 0 else "error",
        content=f"exit status {returncode}\n{formatted_stdout}\n{formatted_stderr}",
        metadata={
            "exit_code": returncode,
            "timed_out": False,
            "duration_seconds": duration,
            "blocked_by": blocked_by,
        },
    )


def _format_stream(name: str, text: str, cap_bytes: int = 8192) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= cap_bytes:
        return f"{name}:\n{text}"
    truncated = encoded[:cap_bytes].decode("utf-8", errors="ignore")
    return f"{name} (truncated, showing {cap_bytes} of {len(encoded)} bytes):\n{truncated}"


def _looks_like_sandbox_denial(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(pattern in lowered for pattern in _SANDBOX_DENIAL_PATTERNS)
