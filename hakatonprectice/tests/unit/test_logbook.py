"""Unit tests for the Logbook JSONL writer."""

from __future__ import annotations

import json
from pathlib import Path

from cyborg_ant.logbook import Logbook, new_run_id


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_new_run_id_has_the_expected_shape() -> None:
    run_id = new_run_id()
    ts, _, suffix = run_id.rpartition("-")
    assert ts.endswith("Z")
    assert len(suffix) == 8
    int(suffix, 16)  # raises ValueError if not hex


def test_emit_writes_the_common_envelope(project_root: Path) -> None:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    logbook = Logbook(log_path, run_id="20260101T000000Z-deadbeef")
    logbook.emit("session_start", project_root=str(project_root))
    logbook.close()

    records = _read_lines(log_path)
    assert len(records) == 1
    record = records[0]
    assert record["schema_version"] == 1
    assert record["run_id"] == "20260101T000000Z-deadbeef"
    assert record["seq"] == 0
    assert record["event"] == "session_start"
    assert "ts" in record


def test_seq_is_monotonic_across_events(project_root: Path) -> None:
    logbook = Logbook(project_root / ".agent_runs" / "run.jsonl", run_id="r")
    logbook.emit("session_start")
    logbook.emit("request_start")
    logbook.close()

    records = _read_lines(project_root / ".agent_runs" / "run.jsonl")
    assert [r["seq"] for r in records] == [0, 1]


def test_each_emit_is_flushed_immediately(project_root: Path) -> None:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    logbook = Logbook(log_path, run_id="r")
    logbook.emit("session_start")
    # Read without closing the logbook — proves the write reached disk without a close().
    records = _read_lines(log_path)
    assert len(records) == 1
    logbook.close()


def test_long_string_field_is_truncated_and_annotated(project_root: Path) -> None:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    logbook = Logbook(log_path, run_id="r", cap_bytes=10)
    logbook.emit("tool_result", content="x" * 100)
    logbook.close()

    record = _read_lines(log_path)[0]
    assert len(record["content"].encode("utf-8")) == 10
    assert record["content_truncated"] is True
    assert record["content_full_bytes"] == 100


def test_short_string_field_is_not_annotated(project_root: Path) -> None:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    logbook = Logbook(log_path, run_id="r", cap_bytes=10)
    logbook.emit("tool_result", content="short")
    logbook.close()

    record = _read_lines(log_path)[0]
    assert record["content"] == "short"
    assert "content_truncated" not in record


def test_a_partial_trailing_line_does_not_break_reading_earlier_lines(project_root: Path) -> None:
    log_path = project_root / ".agent_runs" / "run.jsonl"
    logbook = Logbook(log_path, run_id="r")
    logbook.emit("session_start")
    logbook.emit("request_start")
    logbook.close()

    with log_path.open("a") as fh:
        fh.write('{"schema_version": 1, "run_id": "r", "seq": 2, "event": "tur')  # truncated

    lines = log_path.read_text().splitlines()
    complete = []
    for line in lines:
        try:
            complete.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    assert len(complete) == 2
