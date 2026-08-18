"""Builds the bwrap argv and probes that bwrap is usable."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

BWRAP_BINARY = "bwrap"
READ_ONLY_BINDS = ("/usr", "/bin", "/lib", "/lib64", "/etc")


def build_argv(command: str, project_root: Path) -> list[str]:
    """Build the bwrap argv exactly as fixed in contracts/tools.md."""
    argv = [BWRAP_BINARY]
    for path in READ_ONLY_BINDS:
        argv += ["--ro-bind", path, path]
    argv += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/home", "--tmpfs", "/tmp"]

    root = str(project_root)
    argv += ["--bind", root, root, "--chdir", root]
    argv += ["--unshare-all", "--die-with-parent", "--", "/bin/sh", "-c", command]
    return argv


@dataclass
class SandboxProbeResult:
    available: bool
    version: str | None
    reason: str | None = None


def probe(project_root: Path) -> SandboxProbeResult:
    """`bwrap --version` plus one throwaway sandboxed command. Both must succeed."""
    if shutil.which(BWRAP_BINARY) is None:
        return SandboxProbeResult(False, None, "bwrap binary not found on PATH")

    version = _probe_version()
    if isinstance(version, SandboxProbeResult):
        return version

    return _probe_sandboxed_command(project_root, version)


def _probe_version() -> str | SandboxProbeResult:
    try:
        proc = subprocess.run(
            [BWRAP_BINARY, "--version"], capture_output=True, text=True, timeout=5
        )
    except OSError as exc:
        return SandboxProbeResult(False, None, f"bwrap --version failed: {exc}")
    if proc.returncode != 0:
        return SandboxProbeResult(False, None, "bwrap --version returned non-zero")
    return proc.stdout.strip()


def _probe_sandboxed_command(project_root: Path, version: str) -> SandboxProbeResult:
    argv = build_argv("echo probe-ok", project_root)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    except OSError as exc:
        return SandboxProbeResult(False, version, f"sandboxed probe command failed: {exc}")
    if proc.returncode != 0 or "probe-ok" not in proc.stdout:
        return SandboxProbeResult(False, version, "sandboxed probe command did not succeed")
    return SandboxProbeResult(True, version, None)
