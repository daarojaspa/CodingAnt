"""Resolves a path and decides whether it is inside the project root."""

from __future__ import annotations

from pathlib import Path

from cyborg_ant.errors import BoundaryViolationError

AGENT_RUNS_DIR_NAME = ".agent_runs"


def resolve_candidate(candidate: Path, root: Path) -> Path:
    """Resolve candidate fully against root: symlinks and `..` segments, before any comparison.

    If candidate does not exist yet, resolves the nearest existing ancestor and rebuilds the
    remaining (not-yet-created) segments on top of it, so a target that will be created later is
    still checked against a real, resolved location rather than a raw string.
    """
    if not candidate.is_absolute():
        candidate = root / candidate

    if candidate.exists():
        return candidate.resolve()

    remainder: list[str] = []
    existing = candidate
    while not existing.exists():
        remainder.append(existing.name)
        parent = existing.parent
        if parent == existing:
            break
        existing = parent

    resolved = existing.resolve()
    for part in reversed(remainder):
        resolved = resolved / part
    return resolved


def is_inside(candidate: Path, root: Path) -> bool:
    """Whether candidate, once fully resolved, falls inside root. Equality with root counts."""
    resolved_root = root.resolve()
    resolved_candidate = resolve_candidate(candidate, resolved_root)
    return resolved_candidate == resolved_root or resolved_root in resolved_candidate.parents


def is_under_agent_runs(candidate: Path, root: Path) -> bool:
    """Whether candidate falls under the `.agent_runs/` deny-listed carve-out."""
    resolved_root = root.resolve()
    resolved_candidate = resolve_candidate(candidate, resolved_root)
    agent_runs = resolve_candidate(Path(AGENT_RUNS_DIR_NAME), resolved_root)
    return resolved_candidate == agent_runs or agent_runs in resolved_candidate.parents


def require_inside_root(path_str: str, root: Path, *, deny_agent_runs: bool = False) -> Path:
    """Resolve path_str against root, raising BoundaryViolationError on any refusal."""
    candidate = Path(path_str)
    resolved_root = root.resolve()
    resolved = resolve_candidate(candidate, resolved_root)

    if not (resolved == resolved_root or resolved_root in resolved.parents):
        raise BoundaryViolationError(f"'{path_str}' resolves outside the project root")

    if deny_agent_runs and is_under_agent_runs(candidate, resolved_root):
        raise BoundaryViolationError(
            f"'{path_str}' is inside {AGENT_RUNS_DIR_NAME}/, which the agent may not write to"
        )

    return resolved
