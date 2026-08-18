# Tasks: Raw Agent + 3 Basic Tools (P1)

**Project**: cyborgAnt (Python package `cyborg_ant`)

**Input**: Design documents from `/specs/001-raw-agent-tool-loop/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: **Included and mandatory.** Constitution §9 requires pytest unit tests covering failure
paths, and plan.md fixes the two-suite strategy (research §R10). Tests are not optional here.

**Organization**: Tasks are grouped by user story so each can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All paths are relative to the git root (`/home/dan/coding_ant/`), matching plan.md's tree

## Path Conventions

Single project, `src/` layout, rooted at `hakatonprectice/` per plan.md "Structure Decision":

- Source: `hakatonprectice/src/cyborg_ant/`
- Tests: `hakatonprectice/tests/unit/` (default suite) and `hakatonprectice/tests/acceptance/` (`-m acceptance`, deselected by default)

## Module assignments not explicitly fixed by plan.md

plan.md names 12 modules but does not say where three data-model entities live. Assigned here to
avoid inventing a thirteenth module:

- `Turn`, `StopReason`, `Session` → `session.py`
- `ToolResult` + the tool registry → `tools/__init__.py`
- `Project Root` → a resolved `Path` field on `Config` plus `boundary.is_inside()`

## Phase ordering note

US1 → **US3** → US2. All three are P1, so any order among them is priority order. US3 comes second
because `sandbox.py` is a hard prerequisite for `run_bash`, which US2 needs. Building US2 first
would mean either a forward dependency or shipping an unsandboxed `run_bash` — the one thing
Constitution VI/VII forbid outright.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create `hakatonprectice/pyproject.toml` — uv project named `cyborg-ant`, `requires-python = ">=3.12"`, runtime deps `anthropic` and `python-dotenv`, dev deps `pytest`/`pytest-mock`/`ruff`, `src/` layout, ruff format+lint config, and a registered `acceptance` pytest marker with `addopts = "-m 'not acceptance'"` so real-API runs are deselected by default (plan.md Technical Context, research §R10)
- [X] T002 Run `uv sync` in `hakatonprectice/` and commit the generated `hakatonprectice/uv.lock` — the constitution requires a committed lock
- [X] T003 [P] Create the package skeleton: empty `hakatonprectice/src/cyborg_ant/__init__.py`, `hakatonprectice/src/cyborg_ant/tools/__init__.py`, `hakatonprectice/tests/unit/`, and `hakatonprectice/tests/acceptance/`
- [X] T004 [P] Add `.agent_runs/` to `.gitignore` at the git root — session logs contain file contents, prompts, and command output (Constitution V, research §R5)
- [X] T005 [P] Verify the `bwrap` prerequisite per `specs/001-raw-agent-tool-loop/quickstart.md` §"Verify the sandbox works before writing any code" and record the version — if this fails, the entire `run_bash` design is unusable and US3 must be re-planned before any code is written

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The entities, config, and cross-cutting machinery every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement the `Config` frozen dataclass in `hakatonprectice/src/cyborg_ant/config.py` with all 13 fields and the defaults from plan.md "Configuration values", validating that `project_root` is an existing directory and storing it fully resolved so resolution happens exactly once (data-model.md §Config)
- [X] T007 [P] Define the exception taxonomy in `hakatonprectice/src/cyborg_ant/errors.py`, including the enumerated retryable set from research §R2 — named types only, so no call site ever needs `except Exception:` (Constitution III)
- [X] T008 [P] Write the system prompt in `hakatonprectice/src/cyborg_ant/prompts.py`, stating the constitution's absolute prohibitions (VI) and consent-gated actions (VII) and requiring any refusal to name the rule that applies (FR-015)
- [X] T009 Implement `Turn` (single class with a `kind` discriminator over `user`/`agent`/`tool_request`/`tool_result`), `StopReason` (closed enum with the precedence order from research §R9), and `Session` in `hakatonprectice/src/cyborg_ant/session.py`, enforcing the data-model.md invariants: append-only turns, first turn is `user`, every `tool_request` has exactly one matching `tool_result` by `tool_use_id`, `stop_reason` set exactly once
- [X] T010 Implement `ToolResult` (`outcome` ∈ ok/error/refused/invalid, `content`, `is_error`, `metadata`) and the name→(json_schema, callable) registry in `hakatonprectice/src/cyborg_ant/tools/__init__.py` per contracts/tools.md "Shared observation contract"
- [X] T011 Implement `is_inside(candidate, root)` in `hakatonprectice/src/cyborg_ant/boundary.py` — resolve `..` segments and symlinks fully **before** comparing, resolve the nearest existing ancestor for paths that do not exist yet, treat equality with the root as inside, and apply the `.agent_runs/` deny-listed carve-out (FR-012, FR-013, data-model.md §Project Root)
- [X] T012 [P] Implement `Logbook` in `hakatonprectice/src/cyborg_ant/logbook.py` — JSONL append flushed per event, the common envelope (`schema_version`/`run_id`/`seq`/`ts`/`event`), the `run_id` format `<UTC compact ISO8601>-<8 hex>`, and the 8192-byte string truncation rule with `*_truncated` and `*_full_bytes` annotations (contracts/session-log.md)
- [X] T013 [P] Implement bounded geometric backoff in `hakatonprectice/src/cyborg_ant/retry.py` with an **injected** sleeper and clock, returning the list of measured (not nominal) waits (FR-016, FR-018, research §R2)
- [X] T014 Implement `hakatonprectice/src/cyborg_ant/model_client.py` wrapping the Anthropic SDK with `max_retries=0` and `timeout=60.0`, sending `model`/`max_tokens`/`output_config={"effort": ...}` from `Config` with the `thinking` field **omitted**, and exposing the response `stop_reason` and `usage` to the caller (research §R6)
- [X] T015 [P] Create shared fixtures in `hakatonprectice/tests/conftest.py`: temp project root, fake clock, fake sleeper, and a fake Anthropic client — the default suite must never make a real API call (Constitution IV)
- [X] T016 [P] Unit tests for path resolution and the boundary in `hakatonprectice/tests/unit/test_boundary.py`, asserting exception types not messages
- [X] T017 [P] Unit tests for the logbook in `hakatonprectice/tests/unit/test_logbook.py` — envelope fields, per-event flush, truncation annotation, and that a partial trailing line is still interpretable

**Checkpoint**: Entities, config, logging, retry, and the model client exist and are unit-tested. User story work can begin.

---

## Phase 3: User Story 1 - Agent creates a working program on request (Priority: P1) 🎯 MVP

**Goal**: The loop closes — a plain-language request becomes a real file on disk, and the result comes back into the conversation.

**Independent Test**: Start a session in an empty folder, ask for "a console program that asks for a number `a` and a base `b` and prints log base b of a". Confirm `log.py` exists and runs correctly by hand (quickstart.md §SC-001).

### Tests for User Story 1

- [X] T018 [P] [US1] Unit tests for `write_file` in `hakatonprectice/tests/unit/test_tools_write_file.py` — atomic sequence leaves the original intact on failure before the rename, overwrite is reported, outside-root and `.agent_runs/` paths are refused, directory target and permission denial return `error` not a crash
- [X] T019 [P] [US1] Unit tests for the basic loop in `hakatonprectice/tests/unit/test_loop_basic.py` using the fake client — one request drives model call → `tool_use` → `tool_result` → `answered`, and every `tool_use` id gets exactly one result

### Implementation for User Story 1

- [X] T020 [US1] Implement the atomic write in `hakatonprectice/src/cyborg_ant/tools/write_file.py`: `tempfile.mkstemp(dir=target.parent)` → write → `flush` → `os.fsync` → `os.replace` → `finally` unlink, returning a `ToolResult` with `bytes_written` and `overwrote` metadata (FR-008c, research §R7)
- [X] T021 [US1] Add the parent-folder confirmation gate to `hakatonprectice/src/cyborg_ant/tools/write_file.py` — list the deepest existing ancestor, surface near matches via `difflib.get_close_matches(cutoff=0.75)` **before** asking, default to no, create only the parents the target needs, and return `refused` without confirmation (FR-008a, FR-008b, research §R8)
- [X] T022 [US1] Register `write_file` with its schema from contracts/tools.md in `hakatonprectice/src/cyborg_ant/tools/__init__.py`
- [X] T023 [US1] Implement `run_request` and `execute_tool_calls` in `hakatonprectice/src/cyborg_ant/loop.py` — project `Session.turns` into the API `messages` array, execute **all** `tool_use` blocks from one response and append every result before the next model call, and return an answer when text arrives with no pending tool call (FR-003, FR-004, FR-005)
- [X] T024 [US1] Implement the console REPL in `hakatonprectice/src/cyborg_ant/__main__.py` — load `.env` via `python-dotenv`, resolve the project root from cwd, read input, print replies, carry full history into every turn, and exit on the word `suerte_socio` (FR-001, FR-002)
- [X] T025 [US1] Wire the logbook through the loop and REPL, emitting `session_start`, `request_start`, `turn`, `tool_call`, `tool_result`, `request_end`, and `session_end` with the fields contracts/session-log.md specifies; record `tool_call.arguments` **as sent by the model**, before validation (FR-023)
- [X] T026 [US1] Run the SC-001 walkthrough in `specs/001-raw-agent-tool-loop/quickstart.md` end to end and confirm `log.py` is produced unattended and the conversation states that it was written

**Checkpoint**: US1 is fully functional. The agent can create working programs. This is the MVP.

---

## Phase 4: User Story 3 - Session stays inside its sandbox (Priority: P1)

**Goal**: Nothing the agent does — instructed or self-generated — reaches outside the project root, and every refusal names its reason.

**Independent Test**: Ask the agent to read `~/.ssh/id_rsa`, write into the parent directory, and run a command touching a home-directory path. All three refused, filesystem outside the root untouched (quickstart.md §SC-005 — needs no API key).

**Why before US2**: `sandbox.py` is a prerequisite for `run_bash`, which US2 depends on.

### Tests for User Story 3

- [X] T027 [P] [US3] Unit tests for the sandbox in `hakatonprectice/tests/unit/test_sandbox.py` — SC-005's five escape attempts including a relative-path escape, a symlink escape, and **at least one whose escape is invisible in the command text** (`eval`, `$HOME`, or a runtime-built path) so it can only be caught by the kernel; assert `metadata.blocked_by` distinguishes `"text"` from `"sandbox"`
- [X] T028 [P] [US3] Unit tests for refusal reporting in `hakatonprectice/tests/unit/test_refusals.py` — every refusal carries `outcome: "refused"`, `is_error: True`, and content naming either the boundary or the constitution rule (FR-014)

### Implementation for User Story 3

- [X] T029 [US3] Implement the `bwrap` argv builder in `hakatonprectice/src/cyborg_ant/sandbox.py` exactly as fixed in contracts/tools.md — `--ro-bind` for `/usr /bin /lib /lib64 /etc`, `--proc`, `--dev`, `--tmpfs /home`, `--tmpfs /tmp`, `--bind`/`--chdir` on the project root, `--unshare-all`, `--die-with-parent`
- [X] T030 [US3] Implement the startup probe in `hakatonprectice/src/cyborg_ant/sandbox.py` — `bwrap --version` plus one throwaway sandboxed command; on failure `run_bash` is **not offered as a tool at all** and the session states why, rather than degrading to text-inspection-only
- [X] T031 [US3] Implement the stage-1 text pre-check in `hakatonprectice/src/cyborg_ant/tools/run_bash.py` — extract path-like tokens, refuse before execution if any resolves outside the root, set `metadata.blocked_by = "text"` (FR-012a stage 1)
- [X] T032 [US3] Return kernel denials as ordinary observations with `metadata.blocked_by = "sandbox"` in `hakatonprectice/src/cyborg_ant/tools/run_bash.py` — the OS, not the text check, is the authoritative boundary (FR-012b)
- [X] T033 [US3] Apply the `.agent_runs/` deny-list in `hakatonprectice/src/cyborg_ant/tools/write_file.py` and `hakatonprectice/src/cyborg_ant/tools/run_bash.py` (refuse) while `read_file` stays permitted, all routed through the single rule in `boundary.py` (research §R5)
- [X] T034 [US3] Implement the constitution refusal path in `hakatonprectice/src/cyborg_ant/loop.py` — a request under prohibitions VI or consent gates VII ends the request with `stop_reason: "refused"` naming the rule, and is **never retried** (FR-015, spec Assumptions)
- [X] T035 [US3] Record `sandbox: {available, backend, version}` in the `session_start` log record so a run's boundary posture is readable months later (contracts/session-log.md)

**Checkpoint**: The boundary holds at both stages and every refusal is legible. `run_bash` is now safe to expose.

---

## Phase 5: User Story 2 - Agent reads, modifies, and verifies existing code (Priority: P1)

**Goal**: Three tools chained inside a single request — read, rewrite, run, report — with no developer intervention. This is the actual P1 deliverable.

**Independent Test**: With `log.py` present, ask the agent to add exponentiation of `a` to the power `b`. Confirm it read the file, rewrote it, executed it, and stated the observed result (quickstart.md §SC-002).

### Tests for User Story 2

- [X] T036 [P] [US2] Unit tests for `read_file` in `hakatonprectice/tests/unit/test_tools_read_file.py` — the word ceiling truncates and the observation says so with the full size, binary is refused, a missing file is `error` not a crash, a directory target is `error`, a bare filename resolves relative to the project root
- [X] T037 [P] [US2] Unit tests for `run_bash` in `hakatonprectice/tests/unit/test_tools_run_bash.py` — exit 0 is `ok`, non-zero returns stdout **and** stderr **and** exit status, a timeout is `error` with `metadata.timed_out = true`, stdout/stderr each cap at 8 KB with the true length stated
- [X] T038 [P] [US2] Integration test for the three-tool chain in `hakatonprectice/tests/unit/test_loop_chaining.py` with a scripted fake client — read → write → run within one request, all results appended before the next model call

### Implementation for User Story 2

- [X] T039 [US2] Implement `read_file` in `hakatonprectice/src/cyborg_ant/tools/read_file.py` — resolve a bare name relative to the project root, apply the configurable word ceiling, and state truncation **inside `content`** (not only metadata) with the file's full size, since the agent cannot see metadata (FR-007, FR-007a)
- [X] T040 [US2] Add binary detection to `hakatonprectice/src/cyborg_ant/tools/read_file.py` — a NUL byte in the first 8 KB or a UTF-8 decode failure refuses the file with a stated reason (FR-007b)
- [X] T041 [US2] Implement command execution in `hakatonprectice/src/cyborg_ant/tools/run_bash.py` — run under the sandbox from T029, capture stdout/stderr/exit status, and start the child in its own process group so an interrupt kills the whole tree (FR-009, research §R9)
- [X] T042 [US2] Apply the 30 s wall-clock timeout in `hakatonprectice/src/cyborg_ant/tools/run_bash.py`, returning the timeout as an **ordinary observation that is never retried** — retrying a 30 s timeout three times would spend 90 s of the wall-clock budget on a command already declared stuck (FR-010, research §R3, plan.md rule 2)
- [X] T043 [US2] Register `read_file` and `run_bash` with their schemas from contracts/tools.md in `hakatonprectice/src/cyborg_ant/tools/__init__.py`, omitting `run_bash` entirely when the T030 probe failed
- [X] T044 [US2] Run the SC-002 walkthrough in `specs/001-raw-agent-tool-loop/quickstart.md` and confirm all three tools chained unattended within one request, with the observed output reported as evidence

**Checkpoint**: All three tools work and chain. US1, US2, and US3 are each independently testable.

---

## Phase 6: User Story 4 - Failures are bounded and visible (Priority: P2)

**Goal**: Every failure path terminates within the caps and says exactly how it ended. The developer never watches it spin.

**Independent Test**: Point the session at an unreachable API endpoint, issue a request, and confirm it ends within the retry cap naming the attempt count and each wait (quickstart.md §SC-006, SC-007).

### Tests for User Story 4

- [X] T045 [P] [US4] Unit tests for retry in `hakatonprectice/tests/unit/test_retry.py` — with the injected sleeper, assert the recorded wait sequence is 1.0 s then 2.0 s across 3 attempts, that only the enumerated retryable types are retried, and that a `refused` outcome is never retried
- [X] T046 [P] [US4] Unit tests for the caps in `hakatonprectice/tests/unit/test_loop_caps.py` — the iteration cap fires at 10 with `stop_reason: "iteration_cap_reached"`, retries do **not** consume an iteration, and on a tie `retries_exhausted` outranks the iteration cap
- [X] T047 [P] [US4] Unit tests for stop-reason precedence in `hakatonprectice/tests/unit/test_stop_reasons.py` covering the full order: `refused` > `user_exit` > `retries_exhausted` > `iteration_cap_reached` > `token_cap_reached` > `answered` (research §R9)

### Implementation for User Story 4

- [X] T048 [US4] Wrap tool invocation in the bounded retry from `retry.py` inside `hakatonprectice/src/cyborg_ant/loop.py`, keeping retries **internal to one iteration** so the two caps compose rather than race (FR-016, plan.md rule 1)
- [X] T049 [US4] Apply the same bounded retry to model API calls in `hakatonprectice/src/cyborg_ant/model_client.py`, matching only the enumerated retryable exception types from research §R2 (FR-017)
- [X] T050 [US4] Emit one `retry` log record per attempt with `operation`, `attempt`, `of`, `error_type`, and the **measured** `wait_seconds` from `hakatonprectice/src/cyborg_ant/logbook.py` call sites (FR-018, contracts/session-log.md)
- [X] T051 [US4] Enforce the 10-iteration cap in `hakatonprectice/src/cyborg_ant/loop.py`, comparing the counter **before** each model call so no path loops unbounded, and stating the cap on exit (FR-021, FR-022)
- [X] T052 [US4] Implement the SIGINT handler in `hakatonprectice/src/cyborg_ant/__main__.py` — set a flag, raise `KeyboardInterrupt` in the main thread, `SIGKILL` the `run_bash` process group, and close the log with `stop_reason: "user_exit"`, `via: "sigint"` in a `finally` block so the interrupt case is not the one case with no log (FR-001a, research §R9)
- [X] T053 [US4] Populate `request_end` with `stop_reason`, `iterations_used`, `wall_clock_seconds`, `total_output_tokens`, `max_response_tokens`, `retry_attempts`, and `retry_waits`, and `session_end` with `stop_reason`/`via`/`requests`/`duration_seconds` (FR-024, SC-007)

**Checkpoint**: Every path through the loop terminates with a stated, logged reason.

---

## Phase 7: User Story 5 - Responses stay within budget (Priority: P3)

**Goal**: No single agent response exceeds 6000 tokens, and a truncated answer is never presented as complete.

**Independent Test**: Issue a request inviting a very long answer; confirm the cap holds and truncation is announced (quickstart.md §SC-008).

### Tests for User Story 5

- [X] T054 [P] [US5] Unit tests for the token cap in `hakatonprectice/tests/unit/test_token_cap.py` — a fake response with `stop_reason == "max_tokens"` is reported as cut short and never presented as a complete answer, and `max_response_tokens` lands in `request_end`

### Implementation for User Story 5

- [X] T055 [US5] Confirm `max_tokens=6000` from `Config` is sent on every request in `hakatonprectice/src/cyborg_ant/model_client.py` with no call site able to override it (FR-019)
- [X] T056 [US5] Detect `stop_reason == "max_tokens"` in `hakatonprectice/src/cyborg_ant/loop.py` and state in the conversation that the answer was cut short by the token budget (FR-020) — this fires more often than on a non-thinking model, because Opus 5's default adaptive thinking shares the 6000-token budget with the answer text (research §R6)
- [X] T057 [US5] Set `stop_reason: "token_cap_reached"` with the `usage` payload when the cap prevents an answer entirely, respecting the precedence order from T047 (data-model.md §Stop Reason)
- [X] T058 [US5] Record per-turn `usage` (`input_tokens`, `output_tokens`, cache fields) on every `agent` turn record so SC-008 is checkable from the log alone (contracts/session-log.md)

**Checkpoint**: All five user stories are independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: The evidence machinery the success criteria depend on, plus cleanup

- [X] T059 Implement `hakatonprectice/tests/acceptance/aggregate.py` reading `.agent_runs/*.jsonl` and reporting unattended completion rate, stop-reason histogram, cap violations, wall-clock p50/p95, and boundary refusals by `blocked_by` — ignoring unknown fields, skipping a trailing partial line, and **refusing** to aggregate across differing `schema_version` values (contracts/session-log.md §Aggregation contract)
- [X] T060 [P] Create `hakatonprectice/tests/acceptance/conftest.py` seeding a pristine temp project root per run, and `hakatonprectice/tests/acceptance/test_sc001_sc002.py` marked `@pytest.mark.acceptance` — real paid API calls, never selected by the default suite (research §R10)
- [ ] T061 Run the SC-003 consistency set — 30 runs each of SC-001 and SC-002 from an identical prompt, folder, and starting state — and confirm ≥80% complete unattended from the aggregated logs, not by eye
- [ ] T062 Run the SC-004 generalization set — 30 runs with prompts requesting programs different in nature but still requiring all three tools — and confirm ≥80% complete unattended
- [ ] T063 **Replace SC-009's placeholder budget with a measurement** — compute the p95 `wall_clock_seconds` over the SC-003 run set, update SC-009 in `specs/001-raw-agent-tool-loop/spec.md` and the Performance Goals in `plan.md`, and re-check that the 3-attempt retry policy and the 30 s `run_bash` timeout still fit inside the measured budget (plan.md "Open item carried into implementation" — this is the task plan.md refers to as T012)
- [ ] T064 Run the SC-006 and SC-007 deliberate-failure walkthroughs from `specs/001-raw-agent-tool-loop/quickstart.md` and confirm 100% of runs end within the retry cap with a stated reason, attempt count, and each wait interval
- [X] T065 Run the SC-010 check — confirm stop reason, tool calls, and cap counters are readable from a `.agent_runs/*.jsonl` file alone, without console scrollback
- [X] T066 [P] Run `ruff format` and `ruff check` across `hakatonprectice/src/` and `hakatonprectice/tests/`, and verify no module exceeds the constitution's size ceilings (300 lines/file, 150/class, 30/function)
- [X] T067 [P] Audit for Constitution III compliance — grep `hakatonprectice/src/` for `except Exception`, bare `except:`, and `try` blocks wrapping more than the single line that can fail; confirm every translation uses `raise ... from err`
- [X] T068 [P] Update `specs/001-raw-agent-tool-loop/quickstart.md` with any command that differed in practice, and record the measured `bwrap` version and Python version actually used

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. T005 is a gate: if `bwrap` is unusable, stop and re-plan US3.
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Foundational only
- **US3 (Phase 4)**: Depends on Foundational only — independent of US1, can run in parallel with it
- **US2 (Phase 5)**: Depends on Foundational **and on T029/T030** (sandbox + probe) from US3
- **US4 (Phase 6)**: Depends on Foundational; meaningfully testable once US1 exists
- **US5 (Phase 7)**: Depends on Foundational; needs T047's precedence order for T057
- **Polish (Phase 8)**: Depends on US1–US4 complete. T061–T063 are paid API runs — run them once, after the code is stable.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories
- **US3 (P1)**: No dependencies on other stories
- **US2 (P1)**: Needs `sandbox.py` from US3 (T029, T030). Everything else is independent.
- **US4 (P2)**: Independent, but its independent test needs a working loop from US1
- **US5 (P3)**: Independent; shares only the stop-reason enum

### Within Each User Story

- Tests are written first and must FAIL before implementation
- Entities before tools, tools before the loop, loop before the REPL
- Story complete before moving to the next

### Parallel Opportunities

- **Phase 1**: T003, T004, T005 in parallel after T001/T002
- **Phase 2**: T007, T008 in parallel; then T012, T013, T015 in parallel; then T016, T017 in parallel
- **Phase 3/4**: US1 and US3 can be built by two people simultaneously — they share no source file
- **Phase 5**: T036, T037, T038 in parallel; T039/T040 (read_file) and T041/T042 (run_bash) touch different files
- **Phase 6**: T045, T046, T047 in parallel
- **Phase 8**: T066, T067, T068 in parallel

### Serialization warnings

- T020, T021 both edit `tools/write_file.py` — **not** parallel
- T031, T032, T041, T042 all edit `tools/run_bash.py` — **not** parallel
- T010, T022, T043 all edit `tools/__init__.py` — **not** parallel
- T023, T034, T048, T051, T056 all edit `loop.py` — **not** parallel

---

## Parallel Example: Phase 2 Foundational

```bash
# After T006 (config.py) lands, launch together:
Task: "Define the exception taxonomy in src/cyborg_ant/errors.py"
Task: "Write the system prompt in src/cyborg_ant/prompts.py"

# After T009/T010/T011 land, launch together:
Task: "Implement Logbook in src/cyborg_ant/logbook.py"
Task: "Implement bounded geometric backoff in src/cyborg_ant/retry.py"
Task: "Create shared fixtures in tests/conftest.py"

# Then launch the foundational test pair together:
Task: "Unit tests for the boundary in tests/unit/test_boundary.py"
Task: "Unit tests for the logbook in tests/unit/test_logbook.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup — including the T005 `bwrap` gate
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run the SC-001 walkthrough (T026)
5. At this point the agent writes working programs. Only `write_file` is exposed, so the sandbox gap is not yet a live risk.

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → SC-001 passes → **MVP**
3. US3 → SC-005 passes → the boundary holds, `run_bash` becomes safe to expose
4. US2 → SC-002 passes → **the real P1 deliverable: three tools chained unattended**
5. US4 → SC-006, SC-007 pass → every failure path is bounded and visible
6. US5 → SC-008 passes → responses stay in budget
7. Polish → SC-003, SC-004, SC-009, SC-010 measured from the aggregated logs

### Parallel Team Strategy

1. Everyone completes Setup + Foundational together
2. Then split: Developer A takes US1, Developer B takes US3 (no shared files)
3. Whoever finishes first picks up US2 once T029/T030 have landed
4. US4 and US5 follow once the loop is stable

---

## Notes

- `[P]` = different files, no dependency on an incomplete task. Check the serialization warnings above before parallelizing.
- Tests are mandatory here (Constitution §9), not the template's optional case. The default suite never makes a real API call; only `-m acceptance` does.
- **T063 is the one task that edits the spec.** SC-009's 2-minute budget is an inherited placeholder and plan.md's 240 s is an estimate with low confidence. Both are replaced by a measured p95.
- The acceptance runs in T061–T063 cost real money — 60+ paid sessions. Get the unit suite green first.
- Commit after each task or logical group; PRs stay ≤300 changed lines per the constitution.
- Stop at any checkpoint to validate a story independently.
