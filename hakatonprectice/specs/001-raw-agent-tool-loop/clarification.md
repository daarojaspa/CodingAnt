# Clarification Questions: Raw Agent + 3 Basic Tools (P1)

**Spec**: [spec.md](./spec.md)
**Session**: 2026-08-09
**Status**: Answered — integrated into `spec.md` under `## Clarifications` (Session 2026-08-10)

> Note: the SC numbers quoted in the questions below refer to the pre-integration spec. Q4's
> answer split the old SC-003 into a consistency criterion (SC-003) and a generalization
> criterion (SC-004), shifting every later criterion by one.

Answer inline by filling the `**Answer:**` line under each question (option letter, or a short
phrase of ≤5 words). Say "yes"/"recommended" to accept the recommendation. Once answered, re-run
`/speckit-clarify` and the answers will be integrated into `spec.md` under a `## Clarifications`
section and applied to the affected requirements.

---

## Q1 — Shell command boundary enforcement

**Question:** When the agent runs a shell command, how should the system decide whether that
command stays inside the project folder? (FR-012)

**Why it matters:** A shell command is just text — `cat ../../secret` or `python script.py` gives
no reliable list of the files it will touch. Without a chosen enforcement approach, the sandbox
promise in User Story 3 has no testable definition and SC-004 ("100% of escape attempts refused")
cannot be written as a test.

**Recommended:** Option A — the OS enforces the boundary by construction, so no command text has
to be parsed or trusted. Text inspection (B) is trivially bypassed (`eval`, `$HOME`, absolute
paths built at runtime) and gives a false sense of safety.

| Option | Description |
|--------|-------------|
| A | Run every command with the project root as its working directory **and** restrict the process so paths outside the root are unreachable — the OS refuses the access and the resulting error becomes the observation |
| B | Inspect the command string before running: reject commands containing paths that resolve outside the root, otherwise run normally |
| C | Combination — reject obviously-escaping command text first (fast, clear refusal message), then still run under the OS-level restriction as the real boundary |
| D | Run in the project root and rely on the model's judgment plus the refusal rule; only `read_file`/`write_file` get a hard-enforced boundary |

**Answer:**

option C

## Q2 — Writing to a folder that does not exist yet

**Question:** If the agent writes to a path inside the project root whose parent folder does not
exist yet (e.g. `src/utils/helper.py` when `src/utils/` is missing), should the missing folders be
created automatically? (FR-008)

**Why it matters:** The spec currently flags this as "intended behaviour is stated rather than left
to chance" — an open placeholder. It decides whether the agent can lay out a multi-folder project
in one step or has to shell out to `mkdir` first, and it changes the write tool's acceptance tests.

**Recommended:** Option A — creating parent folders is the least surprising behaviour for a coding
agent, keeps the boundary check unchanged (the resolved path is still validated first), and avoids
burning loop iterations on `mkdir` round-trips.

| Option | Description |
|--------|-------------|
| A | Create the missing parent folders automatically, then write; the observation names the folders created |
| B | Refuse the write and return an observation telling the agent the folder does not exist, so it must create it explicitly first |
| C | Create parents only one level deep; deeper nesting is refused |

**Answer:**

Yes ,because we have and max iterations limits, but just parent directories and be a ware that the "none stated directory" is not  a directory that already exists but with a typo. the creation most go inside the project root and  ask for confirmation before creating it.

## Q3 — Reading large or binary files

**Question:** What should `read_file` do when the requested file is very large or is binary rather
than text? (FR-007)

**Why it matters:** The spec says only that it must be handled "without exhausting the context",
which is not testable. An unbounded read can blow the model's context window mid-session and end
the run in a way none of the stated stop reasons cover.

**Recommended:** Option A — a size ceiling plus an explicit truncation notice keeps the failure
recoverable and visible to the agent, matching how every other failure in this spec is surfaced
(as an observation, not a crash).

| Option | Description |
|--------|-------------|
| A | Enforce a maximum number of characters per read; beyond it, return the leading portion plus an explicit "truncated, N bytes total" note. Binary files are refused with a stated reason |
| B | Refuse outright any file over the size limit or detected as binary; the agent must use `run_bash` (`head`, `grep`) to inspect it |
| C | Return the whole file regardless of size; rely on the agent not to request huge files |
| D | Size ceiling with truncation (as A), but binary files are returned in a readable encoded form rather than refused |

**Answer:**
A
a size  cealling  an aproximate number of tokens or words  around 1000 words . for now its a fixed number but leatly will be a dynamic value fixed on a porcentage of the remainning context  available. so this value should initialy be a variable not a hard coded. The read of binary files is resticted.

## Q4 — What the session records for later inspection

**Question:** Should the session write a log of the agent's turns, tool calls, and stop reasons to
a file, or is what appears on the console enough? (SC-005, SC-006)

**Why it matters:** SC-003 requires judging "8 of 10 runs complete unattended" and SC-006 requires
verifying every run reported a stop reason. If the only record is console scrollback, those
success criteria are checked by eye and cannot be automated.

**Recommended:** Option B — a structured log file inside the project root is what makes the
success criteria mechanically verifiable, and it costs little at this phase.

| Option | Description |
|--------|-------------|
| A | Console output only — no log file; the developer reads the transcript as it happens |
| B | Console output plus a machine-readable session log file inside the project root recording each turn, each tool call and its result, and the final stop reason |
| C | Console output plus a human-readable plain-text transcript file, not structured |
| D | Log file written only when a run ends abnormally (retries exhausted, iteration cap, refusal) |

**Answer:**

B , in fact this has made realize ,  with sc-003 we will do a concistency check where  the test will be repeted 30 times  same prompt same folder , same started state.
then for sc-004  we will do  generalization test where the prompt will be change sligthly asking for programs that are dirent in nature, but that involve the use of the 3 tools. also 30 times.

## Q5 — How the developer ends a session

**Question:** How does the developer end a console session, and what happens to a request that is
mid-run when they do? (FR-001, FR-006)

**Why it matters:** "Repeats until the user ends the session" never says how ending is triggered,
and the edge case "the user interrupts the session mid-run → it exits cleanly with a stated reason"
depends on the answer. It determines whether an in-flight shell command is killed or allowed to
finish — which affects whether files are left half-written.

**Recommended:** Option A — supporting both an explicit exit word and Ctrl-C covers the two ways
developers actually leave a terminal program, and terminating the running command prevents the
session from hanging on the very timeout case FR-010 exists to bound.

| Option | Description |
|--------|-------------|
| A | Either an explicit exit command typed at the prompt or Ctrl-C ends the session; an interrupt during a run terminates the in-flight tool call and the session exits stating "user exit" |
| B | Explicit exit command only; Ctrl-C is ignored while a request is running so tool calls always finish, and exit takes effect at the next prompt |
| C | Ctrl-C first cancels the current request and returns to the prompt; a second Ctrl-C (or exit command) ends the session |

**Answer:**
suport   crtl c and  the exit word "suerte_socio" have on account that the writing tool most  be atommic  so it creates a temp file  in the same directory where the file  that is going to oveerwritte  exists , writes evrithing in this temp file and then uses the os  idempotency and atomicity of  replacing the old file with the new one . 

All 5 questions were already answered in clarification.md, so I skipped the questioning loop and integrated them. Questions asked: 0 new; answers integrated: 5.

Spec updated: specs/001-raw-agent-tool-loop/spec.md

Sections touched

Why those two were deferred

Both are cases where the spec fixes the guarantee and the plan picks the value. That split is deliberate, and in one case the spec says so explicitly:

▎ "The retry cap and the backoff ratio are fixed configuration values chosen during planning; the requirement is that they are bounded, geometric, and reported — not that they take particular values."

Same logic for the log: FR-023/FR-024 and SC-010 say what must be recoverable from the file (stop reason, tool calls, retry counts, each wait, iteration count, token totals). "JSONL at .agent_runs/<id>.jsonl" is a file-format decision — it would also trip the checklist's "no implementation details" item, and it's the kind of thing you'd want to change once without re-clarifying the spec.

Neither is a gap. They're the plan's job.

What to have on account for retry count + backoff ratio

1. The 2-minute budget (SC-009) is the real constraint on your numbers. Worst-case retry time has to fit alongside actual work. Base 1s × ratio 2 × 3 attempts = 7s, fine. Base 5s × ratio 3 = 65s, half your budget gone. And it compounds with the run_bash timeout (FR-010): a 30s command timeout retried 3× is 90s on its own. Pick the command timeout and the retry policy together, not separately.

2. The Anthropic SDK already retries internally. It has its own max_retries with backoff. If you leave it on, you get two nested geometric backoffs and FR-018's report ("number of retries and the wait used before each") becomes a lie — you'd report your layer's 3 attempts while the SDK silently made 6. Decide explicitly: set max_retries=0 and own the loop, which is also what Principle I ("understand what frameworks hide") points at.

3. You must enumerate the retryable set, not catch broadly. Constitution III forbids except Exception:, so the policy has to name types: overloaded/rate-limit/5xx/connection errors are retryable; auth and malformed-request errors are not; and per the spec's own assumption, a safety refusal is a final answer and is never retried. Write that list in plan.md — it's a design artifact, not an implementation detail.

4. Decide whether a retry consumes a loop iteration. FR-021 caps iterations at 10, FR-016 caps retries separately, and the edge cases demand that hitting either ends the run with one stated reason, not two. That needs a stated precedence rule (e.g. retries are internal to an iteration and don't increment it; if both trip in the same step, the retry-exhaustion reason wins). Otherwise you get contradictory stop reasons in the logs and SC-007 fails on ambiguity.

5. Sleep and the clock must be injectable. Constitution IV mocks system clocks and forbids real API calls in tests. If the backoff calls time.sleep directly, your failure-path tests really sleep 7s each. Pass the sleeper in.

6. If you add jitter, report actual waits, not nominal ones. FR-018 says report the wait used before each attempt. Record the measured values.

What to have on account for log format + location

1. Format follows from the aggregation you just committed to. 30 consistency runs + 30 generalization runs at 80% thresholds means a script computes those numbers, not you. One JSON object per event, appended per line, is the shape that survives a crash mid-run and streams into an aggregator; a single JSON array means rewriting the closing bracket on every write. Put a schema_version field in from day one — you will change the schema while runs accumulate, and you'll want to know which runs are comparable.

2. The log lives inside the sandbox it's auditing. FR-023 puts it in the project root, which is exactly where read_file/write_file/run_bash are allowed to act. So the agent can read its own log, and can overwrite it. Decide whether the log path is a deny-list carved out inside the allow-list. This is a real decision, not a hypothetical.

3. It breaks "identical starting state" (SC-003). The consistency test requires the same folder and start state 30 times. A log written into that folder changes it between runs — and if runs are numbered per-folder, run 2 sees run 1's artifacts. The harness needs to relocate or clean logs between runs, and you need a run identifier so 60 runs don't collide.

4. Logs will contain file contents, prompts, and bash output. That's the point, but it means they must be gitignored — the same reasoning as Principle V, since anything the agent read can land in there.

5. It has to be written on the abnormal exits, which are the ones you care about. Ctrl-C, retry exhaustion, and crashes are precisely when SC-006/SC-007 are checked. Flush per event rather than at exit, and have the SIGINT handler close the record with user exit — otherwise the interrupt case, which Q5 exists to cover, is the one case with no log.

6. Decide whether tool results are stored whole or truncated. A truncated 1000-word read plus bash output on 60 runs adds up; if you truncate in the log, store the true length alongside so nothing is silently lost.

One thing that isn't in either row but bites in planning

60 acceptance runs are 60 real API sessions — real cost, real wall-clock. Constitution IV says tests never make real API calls, so these can't be pytest unit tests. Plan them as a separate marked harness with its own budget, and keep the unit suite fully mocked.