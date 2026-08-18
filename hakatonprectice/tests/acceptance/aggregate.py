"""Reads .agent_runs/*.jsonl and reports the metrics the success criteria are checked against."""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def aggregate(run_dir: Path) -> dict:
    records = _read_all_records(run_dir)
    _require_single_schema_version(records)

    request_ends = [r for r in records if r.get("event") == "request_end"]
    tool_results = [r for r in records if r.get("event") == "tool_result"]
    gated_request_ids = _request_ids_with_confirmation_refusal(tool_results)

    return {
        "runs": len(request_ends),
        **_completion_stats(request_ends, gated_request_ids),
        "stop_reasons": dict(Counter(r["stop_reason"] for r in request_ends)),
        "cap_violations": _count_cap_violations(request_ends),
        **_wall_clock_percentiles(request_ends),
        "boundary_refusals_by_stage": _refusals_by_stage(tool_results),
    }


def _request_ids_with_confirmation_refusal(tool_results: list[dict]) -> set[str]:
    """request_ids where write_file's parent-folder confirmation gate was declined.

    That refusal carries no `blocked_by` (it isn't a boundary or sandbox violation), so it is
    identified by its distinctive wording instead — see tools/write_file.py's refusal text.
    """
    return {
        r["request_id"]
        for r in tool_results
        if r.get("outcome") == "refused" and "was not confirmed" in r.get("content", "")
    }


def _read_all_records(run_dir: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(run_dir.glob("*.jsonl")):
        records.extend(_read_records(path))
    return records


def _read_records(path: Path) -> list[dict]:
    """Parse each complete line; a trailing partial line from a crash mid-write is skipped."""
    records = []
    for line in path.read_text().splitlines():
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _require_single_schema_version(records: list[dict]) -> None:
    versions = {r["schema_version"] for r in records if "schema_version" in r}
    if len(versions) > 1:
        raise ValueError(
            f"refusing to aggregate across differing schema_version values: {versions}"
        )


def _completion_stats(request_ends: list[dict], gated_request_ids: set[str]) -> dict:
    unattended = sum(1 for r in request_ends if _completed_unattended(r, gated_request_ids))
    total = len(request_ends)
    return {"unattended": unattended, "unattended_rate": (unattended / total) if total else 0.0}


def _completed_unattended(request_end: dict, gated_request_ids: set[str]) -> bool:
    """Answered, and not preceded by a declined confirmation gate (write_file's folder ask)."""
    return (
        request_end.get("stop_reason") == "answered"
        and request_end.get("request_id") not in gated_request_ids
    )


def _count_cap_violations(request_ends: list[dict]) -> int:
    return sum(
        1
        for r in request_ends
        if r.get("iterations_used", 0) > 10 or r.get("max_response_tokens", 0) > 6000
    )


def _wall_clock_percentiles(request_ends: list[dict]) -> dict:
    waits = [r["wall_clock_seconds"] for r in request_ends if r.get("stop_reason") == "answered"]
    if not waits:
        return {"wall_clock_p50": None, "wall_clock_p95": None}
    return {"wall_clock_p50": statistics.median(waits), "wall_clock_p95": _percentile(waits, 95)}


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100)
    lower, upper = int(rank), min(int(rank) + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def _refusals_by_stage(tool_results: list[dict]) -> dict:
    stages = (
        r.get("metadata", {}).get("blocked_by")
        for r in tool_results
        if r.get("outcome") == "refused"
    )
    return dict(Counter(stage for stage in stages if stage is not None))


def _print_report(report: dict) -> None:
    rate = report["unattended_rate"] * 100
    print(f"runs: {report['runs']}   unattended: {report['unattended']} ({rate:.1f}%)")
    print(f"stop reasons: {report['stop_reasons']}")
    print(f"wall clock: p50 {report['wall_clock_p50']}  p95 {report['wall_clock_p95']}")
    print(f"cap violations: {report['cap_violations']}")
    print(f"boundary refusals by stage: {report['boundary_refusals_by_stage']}")


def main() -> None:
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".agent_runs")
    _print_report(aggregate(run_dir))


if __name__ == "__main__":
    main()
