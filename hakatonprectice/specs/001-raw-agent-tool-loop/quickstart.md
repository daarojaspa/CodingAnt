# Quickstart: Raw Agent + 3 Basic Tools (P1)

**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

How to set the project up and validate each success criterion end to end. Everything below runs
from `hakatonprectice/` unless stated otherwise.

---

## Prerequisites

| Requirement | Check | Status on this machine |
|---|---|---|
| Python 3.11+ | `python3 -V` | ✅ 3.12.2 |
| `uv` | `uv --version` | ✅ `~/.local/bin/uv` |
| `bubblewrap` | `bwrap --version` | ✅ `/usr/bin/bwrap` |
| Anthropic API key | `grep -q ANTHROPIC_API_KEY ../.env` | ⚠️ verify — `.env` at the repo root currently holds an OpenAI key |

`bwrap` is not optional. Without it the session starts but does **not** offer `run_bash`, and
SC-002, SC-003, SC-004, and SC-005 are all unrunnable. On Debian/Ubuntu: `sudo apt install
bubblewrap`.

### Verify the sandbox works before writing any code

WSL2 needs unprivileged user namespaces enabled. This one-liner proves the whole boundary:

```bash
bwrap --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
      --ro-bind /etc /etc --proc /proc --dev /dev --tmpfs /home --tmpfs /tmp \
      --bind "$PWD" "$PWD" --chdir "$PWD" --unshare-all --die-with-parent \
      -- /bin/sh -c 'echo inside; ls ~ 2>&1 | head -1; echo x > probe.txt && echo wrote'
```

Expected: `inside`, an empty or missing home listing, `wrote`, and `probe.txt` present afterward
in the real directory. If instead you get `bwrap: No permissions to creating new namespace`, user
namespaces are disabled and no amount of application code will fix it.

---

## Setup

```bash
cd hakatonprectice
uv sync                       # creates .venv, installs from uv.lock
uv run ruff check src tests   # lint
uv run ruff format --check .  # format
```

The API key is read from the gitignored `.env` at the repo root (Constitution V). `python-dotenv`
searches upward from the package, so the existing file is reused rather than duplicated.

---

## Run the agent

```bash
cd /path/to/whatever/folder/you/want/the/agent/to/act/on
uv run --project /home/dan/coding_ant/hakatonprectice python -m nocturne
```

**The current working directory becomes the project root** and the boundary of every action.
Start it in a scratch directory the first few times.

Exit with the word `suerte_socio` or Ctrl-C. Either way the session states a stop reason and
finalises its log.

---

## Validating the success criteria

### SC-005 — boundary refusals (no API key, no cost) — run this first

The cheapest, highest-value check. It needs no model call at all.

```bash
uv run pytest tests/unit/test_sandbox.py tests/unit/test_boundary.py -v
```

Must cover at least five escape attempts, including one whose escape is invisible in the command
text (SC-005 requires this explicitly):

| Attempt | Stage that must catch it |
|---|---|
| `read_file("../../etc/passwd")` | text/path resolution |
| `write_file("/tmp/evil", ...)` | text/path resolution |
| `read_file` via a symlink pointing outside the root | resolution-before-check (FR-013) |
| `run_bash("cat ../secrets")` | stage 1, text pre-check |
| `run_bash("eval $(echo Y2F0IH4vLnNzaC9pZF9yc2E= \| base64 -d)")` | **stage 2, the kernel** |

That last row is the criterion's whole point: the path never appears in the command text, so only
the sandbox can catch it. Assert `metadata.blocked_by == "sandbox"` — asserting merely that it
failed would pass even if it failed for an unrelated reason.

### Full unit suite

```bash
uv run pytest                     # acceptance tests are deselected by default
```

Fully mocked: no API calls, no real sleeping (the sleeper and clock are injected), no network.
Should finish in seconds. Per Constitution IV, a test here **never** makes a real API call.

### SC-001 — agent creates a working program

```bash
mkdir -p /tmp/nocturne-sc001 && cd /tmp/nocturne-sc001
uv run --project /home/dan/coding_ant/hakatonprectice python -m nocturne
```

Prompt:

> create a console program that asks for a number `a` and a base `b` and prints log base b of a

Then verify by hand:

```bash
python3 log.py     # enter a=8, b=2 → expect 3.0
```

Pass = `log.py` exists, runs, prints ≈3, and the agent said it created it — with no intervention
beyond the initial request.

### SC-002 — read, modify, verify (the actual P1 deliverable)

In the same folder, same session:

> also make it calculate a raised to the power b

Pass requires all four, checkable from the log:

1. A `read_file` on `log.py` **before** the rewrite.
2. A `write_file` on `log.py`.
3. A `run_bash` that executes it.
4. The agent reporting the observed output as evidence — not claiming success without running it.

```bash
uv run python -c "
import json,sys,pathlib
p=sorted(pathlib.Path('.agent_runs').glob('*.jsonl'))[-1]
names=[json.loads(l)['name'] for l in p.open() if json.loads(l)['event']=='tool_call']
print(names)  # expect read_file before write_file, then run_bash
"
```

### SC-006, SC-007 — bounded, visible failure

```bash
ANTHROPIC_BASE_URL=http://127.0.0.1:9 uv run --project /home/dan/coding_ant/hakatonprectice python -m nocturne
```

Port 9 refuses connections, so every model call fails with a retryable `APIConnectionError`.
Expected: the session ends within about 3 seconds with `retries_exhausted`, and the final message
names the attempt count and each wait. It must not spin or hang.

```bash
uv run python -c "
import json,pathlib
p=sorted(pathlib.Path('.agent_runs').glob('*.jsonl'))[-1]
r=[json.loads(l) for l in p.open() if json.loads(l)['event']=='request_end'][-1]
print(r['stop_reason'], r['retry_attempts'], r['retry_waits'])
"
```

Expect `retries_exhausted 3 [1.0…, 2.0…]` — two waits for three attempts, measured not nominal.

### SC-008 — caps hold

Checked from every log in the aggregator: no `iterations_used > 10`, no
`max_response_tokens > 6000`. Note that on Opus 5 thinking shares the 6000-token budget with the
answer, so `stop_reason: "max_tokens"` will appear sometimes — FR-020 requires it be reported as
truncated rather than presented as complete.

### SC-003, SC-004, SC-009 — the paid runs

**These make 60 real API calls and cost real money.** They are deselected by default and must
never run in CI-on-push.

```bash
uv run pytest -m acceptance --runs 30          # SC-003 consistency
uv run pytest -m acceptance --generalize --runs 30   # SC-004 generalization
uv run python tests/acceptance/aggregate.py .agent_runs/
```

Each run gets a fresh temp project root seeded from a pristine fixture — a log written into a
shared folder would break SC-003's "identical starting state" and let run 2 see run 1's artifacts.

Report shape:

```
runs: 30   unattended: 27 (90.0%)   threshold: 80%  PASS
stop reasons: answered 27, iteration_cap_reached 2, retries_exhausted 1
wall clock: p50 52.1s  p95 121.4s   budget 240s  PASS
cap violations: none
```

### SC-009 — replace the estimated budget with a measured one

The 240 s budget in the spec is **an estimate derived from component latencies**
(research §R4), not a measurement. After the first successful SC-003 run:

1. Read `wall clock p95` from the aggregator output.
2. Set the budget to roughly 1.8× that, rounded sensibly.
3. Update SC-009 in [spec.md](./spec.md) — replacing the pending-measurement note with the
   measured value and the date.
4. Re-check the retry policy and `run_bash` timeout against the new number. They were chosen
   small enough (3 s worst-case retry, 30 s per command) that they should not need to move.

### SC-010 — the log is sufficient on its own

```bash
uv run python tests/acceptance/aggregate.py .agent_runs/
```

The test is whether every criterion above can be answered from the files alone, with the console
scrollback closed. If any of them needs the terminal, FR-024 is not met.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Startup says `run_bash` unavailable | `bwrap` missing or user namespaces disabled | Run the sandbox one-liner above; install `bubblewrap` |
| `AuthenticationError` immediately | `.env` has no `ANTHROPIC_API_KEY` (it currently holds an OpenAI key) | Add the Anthropic key; it is gitignored |
| Answers truncated mid-sentence | `stop_reason: "max_tokens"` — thinking is sharing the 6000-token budget | Expected; FR-020 requires it be *reported*, not hidden. Lower `effort` to `low` if it is frequent |
| Retries take longer than ~3 s total | The SDK's own retry loop is still on | `max_retries=0` on the client (research §R6) — two nested backoffs also make FR-018's report wrong |
| Runs bleed into each other | Acceptance harness reusing a folder | Each run needs a fresh temp root seeded from the fixture |
| Agent tries to write to `.agent_runs/` | Expected | Refused by design; reads are allowed |
