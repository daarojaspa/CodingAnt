"""Appends one JSON object per event to the session log."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def new_run_id(now: datetime | None = None) -> str:
    ts = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{secrets.token_hex(4)}"


def _truncate_strings(value: Any, cap_bytes: int) -> Any:
    """Recursively truncate any string field over cap_bytes, annotating alongside it."""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, v in value.items():
            if isinstance(v, str):
                encoded = v.encode("utf-8")
                if len(encoded) > cap_bytes:
                    result[key] = encoded[:cap_bytes].decode("utf-8", errors="ignore")
                    result[f"{key}_truncated"] = True
                    result[f"{key}_full_bytes"] = len(encoded)
                else:
                    result[key] = v
            else:
                result[key] = _truncate_strings(v, cap_bytes)
        return result
    if isinstance(value, list):
        return [_truncate_strings(v, cap_bytes) for v in value]
    return value


class Logbook:
    """JSONL append log for one session, flushed after every event."""

    def __init__(self, path: Path, run_id: str, cap_bytes: int = 8192) -> None:
        self.path = path
        self.run_id = run_id
        self.cap_bytes = cap_bytes
        self._seq = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")

    def emit(self, event: str, **fields: Any) -> None:
        record = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "seq": self._seq,
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "event": event,
            **_truncate_strings(fields, self.cap_bytes),
        }
        self._seq += 1
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> Logbook:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
