# Phase 1 Data Model: Raw Agent + 3 Basic Tools (P1)

**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

The seven entities named in the spec, as concrete in-memory structures. Nothing here persists
between sessions except the session log, which is specified separately in
[contracts/session-log.md](./contracts/session-log.md).

---

## Config

One frozen dataclass holding every tunable value, constructed once at startup and passed down.
Nothing below it reads an environment variable or a literal.

| Field | Type | Default | Requirement |
|---|---|---|---|
| `model` | `str` | `"claude-opus-5"` | Constitution stack |
| `max_tokens` | `int` | `6000` | FR-019 |
| `effort` | `str` | `"medium"` | research §R6 |
| `retry_attempts` | `int` | `3` | FR-016 |
| `backoff_base_seconds` | `float` | `1.0` | FR-016 |
| `backoff_ratio` | `float` | `2.0` | FR-016 |
| `command_timeout_seconds` | `float` | `30.0` | FR-010 |
| `max_iterations` | `int` | `10` | FR-021 |
| `read_word_ceiling` | `int` | `1000` | FR-007a |
| `log_value_cap_bytes` | `int` | `8192` | research §R5 |
| `typo_cutoff` | `float` | `0.75` | FR-008b |
| `exit_word` | `str` | `"suerte_socio"` | FR-001 |
| `project_root` | `Path` | resolved cwd at startup | FR-012 |

**Validation**: `project_root` must be an existing directory and is stored fully resolved
(symlinks followed) — every boundary check compares against this resolved value, so resolution
happens exactly once.

---

## Session

One console conversation from start to exit. Holds the ordered turns and the counters that
enforce the caps. Does not survive process exit.

| Field | Type | Notes |
|---|---|---|
| `run_id` | `str` | `<UTC compact ISO8601>-<8 hex>`; names the log file |
| `turns` | `list[Turn]` | Ordered, append-only |
| `started_at` | `datetime` | UTC |
| `stop_reason` | `StopReason \| None` | Set exactly once, at exit |
| `logbook` | `Logbook` | Open file handle for the session log |

**Invariants**

- `turns` is append-only; nothing is ever edited or removed. Truncation happens at the *log*
  boundary, never in the live conversation.
- The first turn is always a user turn.
- Every `tool_request` turn has exactly one matching `tool_result` turn later in the list, keyed
  by `tool_use_id`. A request without a result is a bug, not a valid state.
- `stop_reason` is `None` while running and non-`None` afterwards, always.

**Derived**: the API `messages` array is projected from `turns` on each model call. The projection
is the only place turn structure meets SDK shapes.

---

## Turn

One entry in the conversation. A tagged union of four variants — a single class with a `kind`
discriminator, not four classes, so ordering is trivially preserved.

| `kind` | Payload | Origin |
|---|---|---|
| `user` | `text: str` | Typed at the prompt |
| `agent` | `text: str`, `stop_reason: str`, `usage: Usage` | Model response |
| `tool_request` | `tool_use_id: str`, `name: str`, `arguments: dict` | Model `tool_use` block |
| `tool_result` | `tool_use_id: str`, `result: ToolResult` | Our execution |

**Validation**

- `name` must be one of `read_file`, `write_file`, `run_bash`. An unknown name does **not** raise
  — it produces a `tool_result` with `outcome: "invalid"` (FR-011, and the "tool that does not
  exist" edge case).
- `arguments` is whatever the model sent. Schema mismatches are caught in the tool layer and
  returned as recoverable observations, never as a crash.

---

## Tool

A named capability, with a described purpose and expected arguments. Three exist. Registered in
one dict mapping name → `(json_schema, callable)`.

| Name | Purpose | Required args | Optional args |
|---|---|---|---|
| `read_file` | Load a bounded, text-only slice of a file | `path` | — |
| `write_file` | Write content atomically to a path | `path`, `content` | — |
| `run_bash` | Execute one shell command under the sandbox | `command` | — |

Wire schemas are in [contracts/tools.md](./contracts/tools.md). The registry is the only place
the three names appear together; adding a fourth tool touches exactly one file.

---

## ToolResult

The observation returned from one invocation. **Every** tool returns this shape — success,
failure, and refusal alike — which is what makes FR-011's "never an unhandled crash" checkable
rather than aspirational.

| Field | Type | Notes |
|---|---|---|
| `outcome` | `"ok" \| "error" \| "refused" \| "invalid"` | Discriminator |
| `content` | `str` | What the agent sees; the failure description on non-`ok` |
| `is_error` | `bool` | `True` for everything except `ok`; maps to the API's `tool_result.is_error` |
| `metadata` | `dict` | Structured detail for the log, not shown to the agent |

**`outcome` semantics**

| Value | Meaning | Retryable? |
|---|---|---|
| `ok` | Executed as asked | n/a |
| `error` | Executed, failed for a real reason (missing file, non-zero exit, timeout) | No — the agent reacts |
| `refused` | Blocked by the boundary or a constitution rule | **Never** (spec Assumptions) |
| `invalid` | Unknown tool, or malformed arguments | No — the agent corrects and retries itself |

**`metadata` by tool**

- `read_file`: `truncated: bool`, `full_size_bytes: int`, `detected_binary: bool`
- `write_file`: `created_parents: list[str]`, `bytes_written: int`, `overwrote: bool`
- `run_bash`: `exit_code: int | None`, `timed_out: bool`, `duration_seconds: float`,
  `blocked_by: "text" | "sandbox" | None`

That last field is what SC-005's evidence rests on: it records *which* of the two enforcement
stages caught an escape, so the criterion's "at least one caught by the OS-level restriction" is
verifiable from the log rather than asserted.

---

## Project Root

The folder the agent was started in. The outer boundary of every filesystem and command action.
Not a runtime object — a resolved `Path` on `Config`, plus one function.

```
is_inside(candidate: Path, root: Path) -> bool
```

**Rules** (FR-012, FR-013)

1. Resolve `candidate` fully — `..` segments and symlinks — **before** comparing.
2. Resolve the nearest existing ancestor when the path itself does not exist yet, so a
   not-yet-created file is still checked against a real resolved location.
3. Compare resolved paths; equality with the root counts as inside.
4. `.agent_runs/` is a deny-listed carve-out: writes and commands naming it are refused, reads
   are permitted (research §R5).

The ordering of 1 and 3 is the whole point. Checking a string before resolution is the bug this
rule exists to prevent.

---

## Stop Reason

The stated cause a request ended. A closed enum — an open string would let a typo silently
create a sixth reason and break SC-007's audit.

| Value | Set when | Extra fields recorded |
|---|---|---|
| `answered` | The model returned text with no pending tool call | — |
| `retries_exhausted` | The retry cap was hit on a retryable failure | `attempts`, `waits: list[float]` |
| `iteration_cap_reached` | 10 iterations passed with no answer | `iterations` |
| `token_cap_reached` | `stop_reason == "max_tokens"` prevented an answer | `usage` |
| `refused` | A constitution rule was applied | `rule` |
| `user_exit` | Exit word or interrupt | `via: "exit_word" \| "sigint"` |

**Precedence when several could apply** (research §R9) — `refused` > `user_exit` >
`retries_exhausted` > `iteration_cap_reached` > `token_cap_reached` > `answered`.

`retries_exhausted` carries the actual measured waits, not the nominal ones. FR-018 says "the wait
used before each attempt"; reporting the configured values instead would be a plausible-looking
lie the moment anything perturbs timing.

---

## Session Log

The machine-readable record written inside the project root for each session. It is the evidence
the success criteria are checked against, so its schema is a contract, specified in full in
[contracts/session-log.md](./contracts/session-log.md).

In-memory it is a `Logbook` object holding the open append handle and the `run_id`. It flushes
per event rather than at exit — precisely because the runs that matter most for SC-006/SC-007
(interrupt, retry exhaustion, crash) are the ones that never reach a clean exit.

---

## State Machines

### Session lifecycle

```
              ┌──────────────────────────────────────┐
              ▼                                      │
   start → awaiting_input ──user message──> running ─┘  (answer → back to awaiting_input)
              │                                │
              │ exit word                      │ stop reason other than `answered`
              ▼                                ▼
            closing ◄───────── SIGINT ─────────┘
              │
              ▼
            closed   (log finalised with a stop reason in a `finally`)
```

Every arrow out of `running` passes through `closing`, and `closing` always writes a stop reason.
There is no transition from `running` straight to process exit — that is what FR-006 and SC-007
require, and it is the reason the write happens in a `finally` block.

### One request inside `running`

```
iteration 0..9:
    call model  ──retryable failure──> retry (≤3 attempts, ×2 backoff)
        │                                   │
        │                                   └─exhausted─> stop: retries_exhausted
        │
        ├─ text, no tool call ─────────────> stop: answered
        ├─ stop_reason == max_tokens ──────> report truncation; continue or stop: token_cap_reached
        └─ tool_use blocks ────────────────> execute all, append every result, iterate

after iteration 9 with no answer ────────────> stop: iteration_cap_reached
```

**Two properties this shape guarantees** (FR-022): the iteration counter increases on every pass
and is compared before each model call, so no path loops unbounded; and retries live *inside* one
iteration, so the two caps compose rather than race.

**Multiple tool calls in one turn** (FR-005): all `tool_use` blocks from a single response are
executed and *all* results are appended before the next model call. Returning them one at a time
across separate turns would both violate FR-005 and train the model out of parallel calls.
