# Phase 0 Research: Raw Agent + 3 Basic Tools (P1)

**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md) | **Date**: 2026-08-12

Each entry resolves one unknown carried into planning. Decisions marked **verified** were
executed against this machine during planning; decisions marked **estimated** are stated
assumptions to be confirmed by measurement during implementation.

---

## R1 — OS-level boundary for `run_bash` (FR-012a, SC-005) — **verified**

**Decision**: Enforce the second stage with **bubblewrap (`bwrap`)**, invoking each command as
`bwrap <policy> -- /bin/sh -c "<command>"` with the project root as the only writable path.

**Policy** (verified working on this machine, Linux 5.15 WSL2, `/usr/bin/bwrap` present):

```
bwrap --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
      --ro-bind /etc /etc --proc /proc --dev /dev --tmpfs /home --tmpfs /tmp \
      --bind <PROJECT_ROOT> <PROJECT_ROOT> --chdir <PROJECT_ROOT> \
      --unshare-all --die-with-parent -- /bin/sh -c "<command>"
```

Verified behaviour of this exact policy:

| Probe | Result |
|---|---|
| `cat ~/.ssh/testkey` (file existed outside root) | `No such file or directory` — `/home` is a tmpfs, so the path is not merely unreadable, it is *absent* |
| `touch /home/dan/evil` | `Read-only file system` |
| `echo ok > probe.txt` inside root | Wrote through to the real filesystem |
| `ls ..` | Shows only the project directory itself |

**Rationale**: SC-005 requires at least one escape whose route is invisible in the command text
(`eval`, `$HOME`, a path assembled at runtime). Only a kernel-enforced boundary catches that.
`bwrap` is a system binary already installed here, not a Python dependency, so Constitution's
"no new dependency without justification" applies only weakly — but it is still an external
binary, so the session **probes for it at startup** and refuses to expose `run_bash` if absent,
rather than silently degrading to text inspection alone.

**Alternatives considered**:

- **Landlock LSM via `ctypes` syscalls** — no external binary, kernel 5.15 supports it. Rejected
  for this phase: hand-rolled `ctypes` syscall plumbing is substantially more code than the
  whole tool layer it protects, and a bug there fails open silently.
- **`unshare` + manual mount namespace** — this is what `bwrap` already is, minus the hardening.
- **`chroot`** — needs root. Rejected.
- **No OS layer, text inspection only** — explicitly rejected by the Q1 clarification (Option C).

**Consequence for the spec**: `--unshare-all` also removes network access. The two acceptance
tasks need none. This is recorded as a new assumption; a task needing network is out of scope
for P1.

---

## R2 — Retry policy: bounds, ratio, and the retryable set (FR-016–FR-018) — **estimated**

**Decision**: 3 attempts total (1 initial + 2 retries), base wait **1 s**, geometric ratio **2**,
no jitter. Waits: 1 s, 2 s. Worst-case added latency per failing call: **3 s**.

**Rationale**: `clarification.md:156` is right that retry time competes with the wall-clock
budget, and the numbers there (base 1 × ratio 2 × 3 = 7 s) were the sane end of the range. The
chosen policy is tighter still because of R3 below: only fast-failing transport errors retry, so
a long base wait buys nothing.

**Retryable set — enumerated, because Constitution III forbids `except Exception:`**:

| Retryable (transient) | Not retryable (permanent) |
|---|---|
| `anthropic.RateLimitError` (429) | `anthropic.AuthenticationError` (401) |
| `anthropic.InternalServerError` (≥500) | `anthropic.PermissionDeniedError` (403) |
| `anthropic.APIConnectionError` | `anthropic.NotFoundError` (404 — bad model id) |
| `anthropic.APITimeoutError` | `anthropic.BadRequestError` (400 — malformed request) |
| `OSError` from a tool call | `FileNotFoundError`, `IsADirectoryError`, `PermissionError` |

A safety refusal is a final answer and is never retried (spec Assumptions). A `run_bash` timeout
is **not** retried either — see R3.

**Alternatives considered**: jitter (adds nondeterminism to a 2-value wait sequence for no
contention benefit at 1 concurrent session); base 5 s (burns 15 s of a ~4 min budget on a case
that usually resolves in one attempt).

---

## R3 — `run_bash` timeout, and why timeouts are not retried (FR-010) — **estimated**

**Decision**: **30 s** wall-clock per command. A timeout is returned to the agent as an ordinary
observation and is **never** retried by the retry layer.

**Rationale**: `clarification.md:156` warns that a 30 s timeout retried 3× is 90 s on its own.
That compounding is avoided by making the timeout a *tool result*, not a *retryable failure* —
which is also what FR-010 already says ("report a timeout as an ordinary observation"). The agent
decides whether to try something different; the loop does not silently burn the budget. This
matches `notes.md`'s "ambiguous" category: the *agent* handles it, not the retry layer.

30 s is generous for the acceptance tasks (a two-line Python script runs in <1 s) and still leaves
the budget in R4 intact.

---

## R4 — SC-009 wall-clock budget: estimated from known latencies — **estimated**

The spec now requires this value to be derived rather than inherited. It is estimated here from
component latencies and marked for confirmation against real runs.

**Per-component estimates** (Claude Opus 5, adaptive thinking on, `effort: "medium"`,
`max_tokens: 6000`):

| Component | Median | p95 |
|---|---:|---:|
| One model turn (thinking + text + tool_use block) | 12 s | 25 s |
| `read_file` / `write_file` | <0.05 s | <0.1 s |
| `run_bash` on a small script (incl. `bwrap` setup) | 0.4 s | 1.0 s |
| Retry overhead (R2), when it fires at all | 0 s | 3 s |

**Per-task rollup**:

| Task | Model turns | Median | p95 |
|---|---:|---:|---:|
| SC-001 (write `log.py`) | 2–3 | ~30 s | ~75 s |
| SC-002 (read → rewrite → run → report) | 4–5 | ~55 s | ~130 s |

**Proposed budget: 240 s (4 minutes) per unattended acceptance run, at the 95th percentile.**

**Rationale**: SC-002 is the binding case at ~130 s p95. 240 s is roughly 1.8× that — enough
headroom that ordinary variance does not fail the criterion, tight enough that a genuinely stuck
run trips it. The inherited 2-minute placeholder sits *below* the p95 estimate for SC-002 and
would have failed on healthy runs.

**Confidence: low.** Model latency dominates and is the least certain term here. T012 in tasks
will replace this with measured values; the retry and timeout numbers above are deliberately
small enough that they do not need re-derivation if the budget moves.

---

## R5 — Session log format and location (FR-023, FR-024, SC-010) — **decision**

**Decision**: **JSON Lines**, one object per event, appended and flushed per event, at
`<project_root>/.agent_runs/<run_id>.jsonl` where `run_id` is
`<UTC ISO8601 compact>-<8 hex chars>`. Every record carries `schema_version: 1`.

**Rationale**: 60 acceptance runs are aggregated by a script, not by eye. JSONL survives a crash
mid-run (a partial final line is discardable; a partial JSON array is not) and streams into an
aggregator. `schema_version` is present from day one because the schema will change while runs
accumulate and comparability must be checkable.

**The log lives inside the sandbox it audits.** `.agent_runs/` is inside the project root, which
is exactly where all three tools are permitted to act. Decision: **`.agent_runs/` is a deny-listed
carve-out inside the allow-list** — `write_file` refuses any path under it, and `run_bash`'s text
pre-check refuses commands naming it. `read_file` is *allowed* (the agent inspecting its own log
is harmless and occasionally useful). This is enforced in `boundary.py`, one rule, one place.

**Consequences to handle in the harness, not the agent**:

- SC-003 requires an identical starting state across 30 runs. A log written into that folder
  changes it. The acceptance harness copies a pristine fixture to a fresh temp directory per run
  and collects `.agent_runs/` afterwards.
- Logs contain file contents, prompts, and command output. `.agent_runs/` is gitignored, same
  reasoning as Constitution V.
- Tool results are stored **whole up to 8 KB, then truncated with `content_truncated: true` and
  `content_full_bytes: N`** so nothing is silently lost.

**Alternatives considered**: SQLite (that is P4's deliverable per the roadmap; premature here),
single JSON array (rewrites the closing bracket every append), plain-text transcript (not
mechanically aggregatable — the exact failure Q4 was asked to avoid).

---

## R6 — Anthropic SDK configuration — **decision**

**Decision**: `anthropic.Anthropic(api_key=..., max_retries=0, timeout=60.0)`.

**Rationale**: `max_retries=0` is non-negotiable here. The SDK retries 429/5xx twice by default
with its own backoff; leaving that on nests two geometric backoffs and makes FR-018's report
("the number of retries attempted and the wait used before each") a lie — we would report our 3
attempts while the SDK silently made 6. Owning the loop is also the point of Constitution I.

**Model and request shape**:

| Parameter | Value | Reason |
|---|---|---|
| `model` | `claude-opus-5` | Current Opus; config value, swappable to `claude-sonnet-5` |
| `max_tokens` | `6000` | FR-019 |
| `output_config` | `{"effort": "medium"}` | Cost/latency lever; the tasks are not intelligence-bound |
| `thinking` | omitted | On Opus 5 this **is** adaptive thinking — see the trap below |
| `tools` | 3 definitions | `read_file`, `write_file`, `run_bash` |

**Trap worth stating explicitly**: on Claude Opus 5 thinking is **on by default** when the
`thinking` field is omitted, and `max_tokens` caps thinking *plus* response text together. Our
`max_tokens` is 6000 — a hard requirement, not a tuning knob — so thinking competes with the
answer for that budget. FR-020 ("state when a response was cut short by the token cap") is
therefore load-bearing: `stop_reason == "max_tokens"` must be detected and reported, and it will
fire more often than it would on a non-thinking model.

**Alternatives considered**: `thinking: {"type": "disabled"}` — rejected. On Opus 5, disabled
thinking has two documented failure modes that are actively hostile to this feature: tool calls
can be emitted as **plain text** (the turn succeeds, the call silently never runs, and the bogus
text pollutes the conversation — which would corrupt SC-003's pass/fail judgement), and
`<thinking>` tags can leak into visible output.

**Credentials**: `.env` at the git root already holds keys and is gitignored (Constitution V).
`python-dotenv` loads it, searching upward from the package so the existing file is reused.

---

## R7 — Atomic `write_file` (FR-008c) — **decision**

**Decision**: `tempfile.mkstemp(dir=<target's own directory>)` → write → `os.fsync` → `os.replace`.

**Rationale**: `os.replace` is atomic **only within a filesystem**, which is why the temp file
must be created in the target's own directory rather than `/tmp`. `fsync` before the rename
ensures the content is durable before it becomes visible. On the interrupt path (FR-001a) the
original is untouched because the rename never happened; the orphaned temp file is cleaned by a
`try/finally`.

---

## R8 — Typo detection for missing parent folders (FR-008b) — **decision**

**Decision**: `difflib.get_close_matches(missing_name, siblings, n=3, cutoff=0.75)` against the
existing entries of the deepest parent that *does* exist.

**Rationale**: stdlib, no dependency, and the cutoff is a configurable value rather than a
literal. This is a prompt-shaping aid for the human confirmation gate, not a security control —
it only reorders what the confirmation prompt shows.

---

## R9 — Interrupt handling and the two stop reasons (FR-001a, edge case) — **decision**

**Decision**: a `signal.SIGINT` handler sets a flag and raises `KeyboardInterrupt` in the main
thread; `run_bash`'s subprocess is started in its own process group and killed with `SIGKILL` to
the group on interrupt (`--die-with-parent` on `bwrap` is the backstop). The session log record
is closed with `stop_reason: "user exit"` in a `finally`, so the interrupt case — the one Q5
exists to cover — is not the one case with no log.

**Stop-reason precedence** (the spec's edge case demands one reason, not two):

1. `refused` — a safety refusal ends the request immediately and outranks everything.
2. `user exit`.
3. `retries exhausted` — beats the iteration cap when both trip on the same step.
4. `iteration cap reached`.
5. `token cap reached` — recorded per response; only terminal if it prevents an answer.
6. `answered`.

**Retries do not consume a loop iteration.** They are internal to one iteration. Without this
rule the two caps interact nondeterministically and SC-007 fails on ambiguity.

---

## R10 — Testing strategy under Constitution IV — **decision**

**Decision**: two suites, separately marked.

- **Unit (`pytest`, fully mocked)** — the default suite. The Anthropic client, `time.sleep`, and
  the clock are all injected, so backoff tests assert on a recorded wait sequence and finish in
  milliseconds instead of really sleeping 3 s each. Constitution IV forbids real API calls here.
- **Acceptance harness (`pytest -m acceptance`, deselected by default)** — the 60 runs behind
  SC-003/SC-004. These are real, paid API sessions; they are not unit tests and must never run in
  the default suite or in CI-on-push. Each run gets a fresh temp project root seeded from a
  fixture, and the harness aggregates the JSONL logs into a pass-rate report.

**Sandbox tests need no API key**: `run_bash` and the boundary checks are exercised directly, so
SC-005's five escape attempts run in the unit suite.
