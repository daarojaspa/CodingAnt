# Contract: Session Log

**Plan**: [../plan.md](../plan.md) | **Research**: [../research.md](../research.md) §R5

The session log is the evidence the success criteria are checked against (FR-023, FR-024, SC-010),
so its shape is a contract rather than an implementation detail. 60 acceptance runs are aggregated
by a script; every field below exists because some criterion needs it.

---

## File

```
<project_root>/.agent_runs/<run_id>.jsonl
```

`run_id` = `<UTC compact ISO8601>-<8 hex chars>`, e.g. `20260812T143052Z-a3f9c1d2`. The random
suffix means 60 runs in the same folder cannot collide even if two start in the same second.

**Format**: JSON Lines — one complete JSON object per line, appended and **flushed per event**.
Not flushed at exit: the runs SC-006 and SC-007 care about most (interrupt, retry exhaustion,
crash) are precisely the ones that never reach a clean exit.

**Gitignored**, same reasoning as Constitution V — logs contain file contents, prompts, and
command output, so anything the agent read can land in here.

**Not agent-writable**: `write_file` and `run_bash` refuse paths under `.agent_runs/`;
`read_file` is permitted (research §R5).

---

## Common envelope

Every record:

```json
{
  "schema_version": 1,
  "run_id": "20260812T143052Z-a3f9c1d2",
  "seq": 7,
  "ts": "2026-08-12T14:30:59.114Z",
  "event": "tool_result",
  "...": "event-specific fields"
}
```

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `int` | `1`. On every record, not only the header — a partial file must still be interpretable |
| `run_id` | `str` | Matches the filename |
| `seq` | `int` | Monotonic from 0; gives total order independent of timestamp resolution |
| `ts` | `str` | UTC, ISO 8601, milliseconds |
| `event` | `str` | Discriminator; the eight types below |

---

## Event types

### `session_start`

```json
{
  "event": "session_start",
  "project_root": "/home/dan/coding_ant/hakatonprectice",
  "config": { "model": "claude-opus-5", "max_tokens": 6000, "effort": "medium",
              "retry_attempts": 3, "backoff_base_seconds": 1.0, "backoff_ratio": 2.0,
              "command_timeout_seconds": 30.0, "max_iterations": 10,
              "read_word_ceiling": 1000 },
  "sandbox": { "available": true, "backend": "bwrap", "version": "0.8.0" }
}
```

The full config is recorded so a run's numbers are interpretable months later without guessing
which defaults were in force. `sandbox.available: false` means `run_bash` was not offered.

### `request_start`

```json
{ "event": "request_start", "request_id": "req-1", "user_text": "create a console program that..." }
```

A "request" is one user message and everything until an answer or a stop reason. Iteration and
token counters are scoped to it (spec Assumptions).

### `turn`

```json
{
  "event": "turn", "request_id": "req-1", "iteration": 0, "kind": "agent",
  "text": "I'll create log.py...",
  "stop_reason": "tool_use",
  "usage": { "input_tokens": 1204, "output_tokens": 380,
             "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0 }
}
```

`kind` is `user` | `agent`. `usage` is present on `agent` turns only and is what SC-008's
"no single response exceeds 6000 tokens" is checked against.

### `tool_call`

```json
{
  "event": "tool_call", "request_id": "req-1", "iteration": 0,
  "tool_use_id": "toolu_01abc", "name": "write_file",
  "arguments": { "path": "log.py", "content": "import math\n..." }
}
```

Arguments are recorded **as sent by the model**, before validation — a malformed call is exactly
what you need to see when diagnosing a failed run. Values over 8 KB are truncated per the rule
below.

### `tool_result`

```json
{
  "event": "tool_result", "request_id": "req-1", "iteration": 0,
  "tool_use_id": "toolu_01abc", "name": "write_file",
  "outcome": "ok", "duration_seconds": 0.004,
  "content": "Wrote 412 bytes to log.py (new file).",
  "metadata": { "created_parents": [], "bytes_written": 412, "overwrote": false }
}
```

`outcome` ∈ `ok` | `error` | `refused` | `invalid`. `metadata` fields are per-tool
([tools.md](./tools.md)); `run_bash` carries `blocked_by`, which is what SC-005's
"caught by the OS-level restriction" is verified from.

### `retry`

```json
{
  "event": "retry", "request_id": "req-1", "iteration": 2,
  "operation": "model_call", "attempt": 2, "of": 3,
  "error_type": "RateLimitError", "wait_seconds": 2.014
}
```

One record per retry attempt. `wait_seconds` is the **measured** wait, not the configured one —
FR-018 asks for the wait used, and reporting the nominal value would be a plausible-looking lie
the moment anything perturbs timing. `error_type` is the exception class name, so an aggregator
can tell a rate limit from a connection drop without parsing prose.

### `request_end`

```json
{
  "event": "request_end", "request_id": "req-1",
  "stop_reason": "answered",
  "iterations_used": 3,
  "wall_clock_seconds": 47.2,
  "total_output_tokens": 1140,
  "max_response_tokens": 512,
  "retry_attempts": 0,
  "retry_waits": []
}
```

The aggregator's primary record. Field-by-field, every success criterion that reads it:

| Field | Serves |
|---|---|
| `stop_reason` | SC-006, SC-007 — every terminated run reports one |
| `retry_attempts`, `retry_waits` | SC-007 — exhausted runs report attempt count and each wait |
| `iterations_used` | SC-008 — no request exceeds 10 iterations without an answer |
| `max_response_tokens` | SC-008 — no single response exceeds 6000 tokens |
| `wall_clock_seconds` | SC-009 — the p95 budget, measured from timestamps |
| all of the above | SC-003, SC-004 — "complete unattended" judged from logs, not by eye |

On `stop_reason: "retries_exhausted"`, `retry_waits` is the full list of measured waits. On
`user_exit` it also carries `via: "exit_word" | "sigint"`.

### `session_end`

```json
{ "event": "session_end", "stop_reason": "user_exit", "via": "sigint",
  "requests": 2, "duration_seconds": 118.7 }
```

Written in a `finally` block. The SIGINT handler closes the record before the process exits —
otherwise the interrupt case, which the Q5 clarification exists to cover, would be the one case
with no log.

---

## Truncation rule

Any string field over **8192 bytes** is truncated and annotated:

```json
{
  "content": "first 8192 bytes...",
  "content_truncated": true,
  "content_full_bytes": 41022
}
```

The full length is always recorded, so nothing is silently lost — a truncated 1000-word read plus
bash output across 60 runs adds up, but a size that vanishes is a size you cannot reason about.

---

## Aggregation contract

`tests/acceptance/aggregate.py` reads `.agent_runs/*.jsonl` and reports:

- **Unattended completion rate** — fraction of runs whose final `request_end` has
  `stop_reason: "answered"` with no `outcome: "refused"` on a confirmation gate (SC-003, SC-004).
- **Stop-reason histogram** — every run accounted for (SC-006, SC-007).
- **Cap violations** — any `iterations_used > 10` or `max_response_tokens > 6000` (SC-008).
- **Wall-clock p50 / p95** — over runs that completed unattended (SC-009).
- **Boundary refusals by stage** — counted by `metadata.blocked_by` (SC-005).

**Forward compatibility**: the aggregator ignores unknown fields and skips a trailing partial line
(a crash mid-write), but **refuses** to aggregate across differing `schema_version` values — the
whole point of stamping the version is knowing which runs are comparable.
