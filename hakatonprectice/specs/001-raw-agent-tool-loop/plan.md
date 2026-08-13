# Implementation Plan: Raw Agent + 3 Basic Tools (P1)

**Branch**: `001-raw-agent-tool-loop` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-raw-agent-tool-loop/spec.md`

---

## Summary

A console REPL that holds a multi-turn conversation with Claude, lets the model decide when it
needs a tool, executes `read_file` / `write_file` / `run_bash` against the folder the agent was
started in, and feeds every result — success, failure, or refusal — back as the next observation.
Every path through the loop terminates: bounded geometric retries, a 10-iteration cap per request,
a 6000-token cap per response, and a stated stop reason on the way out. Every session writes a
JSONL log inside the project root that the success criteria are checked against mechanically.

The technical spine is deliberately thin, per Constitution I: an `anthropic` client with its own
retries disabled, a hand-written `while` loop, a dict of tool callables, and `bubblewrap` as the
kernel-level boundary that makes `run_bash` safe to expose at all.

---

## Technical Context

**Language/Version**: Python 3.12.2 (constitution floor is 3.11+)

**Primary Dependencies**: `anthropic` (official SDK — the only supported model interface per
constitution), `python-dotenv` (loads the existing gitignored `.env`). Dev-only: `pytest`,
`pytest-mock`, `ruff`. External binary: `bubblewrap` (`/usr/bin/bwrap`, present on this machine).

**Storage**: JSON Lines files under `<project_root>/.agent_runs/`. No database — SQLite is P4's
deliverable per the roadmap and is out of scope here.

**Testing**: `pytest` with `pytest-mock`. Two suites: a fully-mocked unit suite (default) and a
`-m acceptance` harness that makes real API calls and is deselected by default (Constitution IV).

**Target Platform**: Linux (WSL2, kernel 5.15). `bwrap` makes the sandbox Linux-only; the session
probes for it at startup and refuses to expose `run_bash` if it is unavailable.

**Project Type**: Single-project CLI application, `src/` layout under `hakatonprectice/`.

**Performance Goals**: 95% of unattended acceptance runs complete within the SC-009 wall-clock
budget. Provisional budget **240 s**, estimated in [research.md](./research.md) §R4 — to be
replaced with a measured value (T012).

**Constraints**: ≤6000 tokens per agent response; ≤10 loop iterations per request; ≤3 attempts per
retryable failure with a ×2 geometric backoff from 1 s; 30 s per shell command; ~1000-word
`read_file` ceiling held as a configurable value.

**Scale/Scope**: One interactive developer, one session at a time, no shared state, no persistence
between sessions. Roughly 12 source modules, none near the 300-line ceiling.

---

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1 design. Both passes recorded.*

| Principle | Verdict | How the design satisfies it |
|---|---|---|
| **I. Primitives Over Frameworks** (NON-NEGOTIABLE) | ✅ Pass | Hand-written loop and tool dispatch. Only the official `anthropic` SDK, no agent framework. The SDK's own retry loop is explicitly **disabled** (`max_retries=0`) so the backoff we write is the only one running — this is the principle's "understand what frameworks hide" in its most literal form. Roadmap's pairing rule (P0–P3 written by hand) is respected. |
| **II. Single Responsibility & Size Limits** | ✅ Pass | Each module states its responsibility in one line (see Source Code below). Largest projected file is `tools/run_bash.py` at ~120 lines; no class exceeds 150; the 30-line function ceiling shapes `loop.py` into `run_request` + `execute_tool_calls` + `handle_stop` rather than one long function. PR ≤300 changed lines is met by the phased task split. |
| **III. Explicit Error Handling** (NON-NEGOTIABLE) | ✅ Pass | The retryable set is enumerated by exception type in research §R2 — no `except Exception:` anywhere. `try` blocks wrap the single failing call (`client.messages.create`, `os.replace`, `subprocess.run`). Translations rethrow with `raise NewError from err`. `errors.py` defines the taxonomy so tool layers catch named types. |
| **IV. Isolated Tests Covering Failure Paths** | ✅ Pass | Unit suite is fully mocked and never makes a real API call. The sleeper and clock are **injected** into `retry.py`, so failure-path tests assert a recorded wait sequence instead of really sleeping. Tests assert exception *types*, not messages. The 60 real-API acceptance runs live in a separately-marked harness that the default suite never selects. |
| **V. Secrets Never In Version Control** (NON-NEGOTIABLE) | ✅ Pass | Key comes from the existing gitignored `.env` at the repo root. Additionally `.agent_runs/` is gitignored: logs contain file contents, prompts, and command output, so the same reasoning applies (research §R5). |
| **VI. Absolute Safety Prohibitions** (NON-NEGOTIABLE) | ✅ Pass | Two independent layers. The system prompt states the prohibitions and requires a refusal naming the rule (FR-015). Independently, `bwrap` denies the filesystem reach that most of VI's items require, so a prompt-injected instruction to exfiltrate `~/.ssh` fails at the kernel even if the model complies. Defence does not rest on the model's judgement. |
| **VII. Consent-Gated Actions** (NON-NEGOTIABLE) | ✅ Pass | Filesystem access outside the project folder is denied by construction, not by policy. Parent-folder creation is the one consent gate reached in normal use and is an explicit human confirmation (FR-008a). `--unshare-all` removes network, so unfiltered outbound connections are impossible in P1. No privilege escalation: the command runs as the developer's own uid, with strictly *fewer* capabilities. |
| **Stack constraints** | ✅ Pass | Python 3.12, official Anthropic SDK with API key from `.env`, `src/` layout, `uv` for deps with a committed lock, `ruff` for format+lint. |
| **Workflow & human gates** | ✅ Pass | Feature branch + PR; the human owns all GitHub credentials and approves every push and merge. The agent never pushes. |

**New dependency justifications** (Constitution requires one line each):

- `anthropic` — mandated by the constitution as the only supported model interface.
- `python-dotenv` — the stdlib has no `.env` parser and Constitution V mandates `.env` for the key.
- `bubblewrap` (system binary, not a Python dep) — the stdlib cannot create a mount namespace;
  without a kernel-enforced boundary, SC-005's invisible-escape case is unsatisfiable and
  `run_bash` cannot be responsibly exposed at all. Alternatives weighed in research §R1.

**Post-Phase-1 re-evaluation**: ✅ Pass, unchanged. The Phase 1 design introduced no new
dependency, no module over the size ceilings, and no broad exception handler. One design decision
was added under Principle VII — `.agent_runs/` as a deny-listed carve-out inside the allow-list
(research §R5) — which tightens rather than relaxes the boundary.

**Complexity Tracking**: not required — no violations to justify.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-raw-agent-tool-loop/
├── spec.md              # Feature specification (input)
├── clarification.md     # Answered clarification session
├── plan.md              # This file
├── research.md          # Phase 0 output — R1..R10
├── data-model.md        # Phase 1 output — entities, states, validation
├── quickstart.md        # Phase 1 output — runnable validation guide
├── contracts/
│   ├── tools.md         # The 3 tool schemas + observation contract
│   └── session-log.md   # JSONL record schema (schema_version 1)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output — NOT created by /speckit.plan
```

### Source Code (repository root)

The Python project lives under `hakatonprectice/`, alongside the constitution and specs. The P0
experiment (`chatbot.py` at the git root) is left untouched.

```text
hakatonprectice/
├── pyproject.toml            # uv project; deps, ruff config, pytest markers
├── uv.lock                   # committed (constitution)
├── src/
│   └── nocturne/
│       ├── __init__.py
│       ├── __main__.py       # Console entry point: reads input, prints replies, exits.
│       ├── config.py         # All tunable values in one frozen dataclass.
│       ├── errors.py         # The project's exception taxonomy.
│       ├── session.py        # Holds ordered turns and the counters that enforce the caps.
│       ├── loop.py           # Runs one user request to an answer or a stated stop reason.
│       ├── model_client.py   # Wraps the Anthropic SDK; owns request shape and stop_reason.
│       ├── retry.py          # Bounded geometric backoff with an injected sleeper and clock.
│       ├── logbook.py        # Appends one JSON object per event to the session log.
│       ├── boundary.py       # Resolves a path and decides whether it is inside the root.
│       ├── sandbox.py        # Builds the bwrap argv and probes that bwrap is usable.
│       ├── prompts.py        # The system prompt text.
│       └── tools/
│           ├── __init__.py   # Tool registry: schemas out, dispatch in.
│           ├── read_file.py  # Reads a bounded, text-only slice of a file.
│           ├── write_file.py # Writes a file atomically, gated on the parent-folder rule.
│           └── run_bash.py   # Runs one shell command under the sandbox with a timeout.
└── tests/
    ├── conftest.py           # Fixtures: temp project root, fake clock, fake sleeper, fake client.
    ├── unit/                 # Fully mocked; the default suite.
    │   ├── test_boundary.py
    │   ├── test_sandbox.py       # SC-005's five escape attempts
    │   ├── test_retry.py
    │   ├── test_loop_caps.py
    │   ├── test_logbook.py
    │   └── test_tools_*.py
    └── acceptance/           # -m acceptance; real API calls, deselected by default
        ├── conftest.py           # Seeds a pristine temp root per run
        ├── test_sc001_sc002.py
        └── aggregate.py          # Reads .agent_runs/*.jsonl → pass-rate report
```

**Structure Decision**: single project, `src/` layout, mandated by the constitution and chosen by
the user during planning. `hakatonprectice/` is a self-contained workspace holding the
constitution, the specs, and now the code; the P0 `chatbot.py` at the git root stays as a
historical artifact of the previous phase.

---

## Design Notes That Bind Implementation

These are the decisions the spec deliberately deferred to planning. Full reasoning in
[research.md](./research.md).

### Configuration values (all in `config.py`, none hard-coded at use sites)

| Value | Setting | Source |
|---|---|---|
| Model | `claude-opus-5` | R6 |
| Max tokens per response | `6000` | FR-019 |
| Effort | `medium` | R6 |
| Retry attempts | `3` (1 initial + 2 retries) | R2 |
| Backoff base / ratio | `1.0 s` / `2.0` | R2 |
| Shell command timeout | `30 s` | R3 |
| Loop iteration cap | `10` | FR-021 |
| `read_file` word ceiling | `1000` | FR-007a |
| Log tool-result cap | `8 KB`, then truncate with a stated full size | R5 |
| Typo-suggestion cutoff | `0.75` | R8 |
| Exit word | `suerte_socio` | FR-001 |

### Three rules that resolve stated ambiguities in the spec

1. **Retries do not consume a loop iteration.** They are internal to one iteration. On the same
   step, retry exhaustion outranks the iteration cap. Full precedence order in R9. Without this,
   SC-007 fails on ambiguous stop reasons.
2. **A `run_bash` timeout is an observation, not a retryable failure.** This is what FR-010
   already says, and it is what prevents the 30 s × 3 = 90 s compounding that
   `clarification.md:156` warned about.
3. **`.agent_runs/` is a deny-listed carve-out inside the allow-list.** `write_file` and
   `run_bash` refuse it; `read_file` is permitted. One rule, enforced in `boundary.py`.

### Two facts about Opus 5 that shape the request

- **Thinking is on by default** when the `thinking` field is omitted, and `max_tokens` caps
  thinking *plus* answer text together. With `max_tokens` fixed at 6000 by FR-019, FR-020's
  "state when a response was cut short" will fire more often than on a non-thinking model.
- **Disabling thinking is not an option here.** On Opus 5, disabled thinking can emit a tool call
  as *plain text* — the turn succeeds, the call silently never runs, and the text pollutes later
  turns. That failure mode would corrupt SC-003's pass/fail judgement outright.

### Open item carried into implementation

**SC-009's budget is an estimate, not a measurement.** Research §R4 derives **240 s** from
component latencies and marks confidence as low, because model latency dominates and is the least
certain term. The retry and timeout values above were chosen small enough that they do not need
re-derivation if the budget moves. A dedicated task (T012) replaces the estimate with a measured
p95 and updates SC-009 in the spec.

---

## Phase 1 Artifacts

- **[data-model.md](./data-model.md)** — the seven spec entities as concrete structures, with
  validation rules and the session/request state machines.
- **[contracts/tools.md](./contracts/tools.md)** — the three tool schemas as sent to the API, and
  the observation contract every tool result obeys.
- **[contracts/session-log.md](./contracts/session-log.md)** — the JSONL record schema
  (`schema_version: 1`) and the field-by-field mapping from SC-007/SC-008/SC-010 to log fields.
- **[quickstart.md](./quickstart.md)** — how to set the project up and run each success criterion
  end to end, including the SC-005 escape probes that need no API key.

---

## Completion

Command ends after Phase 1 design. `tasks.md` is produced by `/speckit.tasks`, not by this
command.
