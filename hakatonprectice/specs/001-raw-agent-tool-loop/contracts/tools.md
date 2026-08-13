# Contract: Tool Interface

**Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md)

The three tool definitions exactly as sent in the `tools` array, and the observation contract
every result obeys. This is the interface between the model and the machine; it is the one place
where a mismatch between description and behaviour cannot be fixed by prompting.

---

## Shared observation contract

Every tool, on every path, returns a `ToolResult` and never raises to the loop (FR-011). The loop
converts it to an API `tool_result` block:

```json
{
  "type": "tool_result",
  "tool_use_id": "<from the tool_use block>",
  "content": "<ToolResult.content>",
  "is_error": true
}
```

`is_error` is `false` only for `outcome: "ok"`. On `error`, `refused`, and `invalid` it is `true`
and `content` describes what happened and why, in terms the agent can act on.

**Refusals name the reason** (FR-014). A boundary refusal says what was refused and that it
resolved outside the project root; a constitution refusal names the rule (VI or VII).

**Every `tool_use` gets exactly one `tool_result`.** Including unknown tool names and malformed
arguments — the API rejects a follow-up where any `tool_use` id lacks a matching result, so
dropping one turns a recoverable observation into a hard failure.

---

## `read_file`

```json
{
  "name": "read_file",
  "description": "Read a text file from the project and return its contents. Accepts either a path relative to the project root or an absolute path inside it. Large files are truncated to a fixed word ceiling and the result says so, including the file's full size. Binary files are refused — use run_bash with a tool like `file` or `head` to inspect those.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Path to the file, relative to the project root or absolute inside it."
      }
    },
    "required": ["path"]
  }
}
```

### Behaviour

| Condition | `outcome` | `content` |
|---|---|---|
| Text file within the ceiling | `ok` | Full contents |
| Text file over the ceiling | `ok` | Leading portion + `[truncated: returned N of M words; file is B bytes]` |
| Binary detected | `refused` | Refusal naming binary detection |
| Path resolves outside root | `refused` | Refusal naming the boundary |
| File does not exist | `error` | The missing path |
| Path is a directory | `error` | States it is a directory |

**Binary detection**: a NUL byte in the first 8 KB, or a UTF-8 decode failure. Cheap, no
dependency, and errs toward refusing — which is the safe direction, since the failure mode being
avoided is corrupting the conversation with unreadable bytes (FR-007b).

**Truncation is reported inside `content`**, not only in metadata. The agent cannot see metadata,
and FR-007a requires *the observation* to state it.

---

## `write_file`

```json
{
  "name": "write_file",
  "description": "Write content to a file in the project, replacing it if it exists. The write is atomic: content is staged in a temporary file and swapped into place, so an interrupted write never leaves a partial file. If the parent folders do not exist, the write pauses and asks the user to confirm creating them; without confirmation it is refused.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Path to write, relative to the project root or absolute inside it."
      },
      "content": {
        "type": "string",
        "description": "The full new contents of the file."
      }
    },
    "required": ["path", "content"]
  }
}
```

### Behaviour

| Condition | `outcome` | Notes |
|---|---|---|
| Parents exist, path inside root | `ok` | Reports bytes written and whether it overwrote |
| Parents missing, user confirms | `ok` | Reports the folders created |
| Parents missing, user declines | `refused` | No folder is created, no file is written |
| Path resolves outside root | `refused` | Nothing is created anywhere (US3 scenario 2) |
| Path under `.agent_runs/` | `refused` | The log is not writable by the agent (research §R5) |
| Target is a directory / permission denied | `error` | Recoverable observation |

### Atomic write sequence (FR-008c)

1. `tempfile.mkstemp(dir=target.parent)` — **the target's own directory**, so the rename stays
   within one filesystem, which is the only condition under which it is atomic.
2. Write, `flush`, `os.fsync` — durable before it becomes visible.
3. `os.replace(tmp, target)` — one atomic rename.
4. `finally`: unlink the temp file if it still exists.

An interrupt at any point before step 3 leaves the original file untouched.

### Confirmation gate (FR-008a, FR-008b)

Before asking, the deepest existing ancestor is listed and the missing segment is compared against
its entries with `difflib.get_close_matches(cutoff=0.75)`. Any near match is surfaced *first*:

```
The folder 'src/utilz/' does not exist.
  Did you mean 'src/utils/'?  (existing, close match)
Create 'src/utilz/' and write helper.py into it?  [y/N]
```

The default is **no**. Only the parent folders needed for the target are created, never more, and
never outside the root.

**This gate is why the acceptance tasks are "unattended".** Both write to the project root
directly, so the gate is never reached — the spec's assumption holds by construction. A task
needing a new folder is attended by definition.

---

## `run_bash`

```json
{
  "name": "run_bash",
  "description": "Run one shell command inside the project folder and return its standard output, standard error, and exit status. The command runs with the project folder as its working directory and cannot read or write anything outside it — paths outside the project simply do not exist from the command's point of view. There is no network access. Commands are cut off after a time limit and the timeout is reported as an ordinary result.",
  "input_schema": {
    "type": "object",
    "properties": {
      "command": {
        "type": "string",
        "description": "The shell command to run, executed with /bin/sh -c inside the project folder."
      }
    },
    "required": ["command"]
  }
}
```

### Two-stage enforcement (FR-012a)

**Stage 1 — text pre-check.** Extract path-like tokens from the command; if any resolves outside
the project root, refuse *before* executing, with a clear reason. Fast, legible feedback for the
common honest mistake (`cat ../secrets`).

**Stage 2 — the real boundary.** Every command that survives stage 1 runs under `bwrap`:

```
bwrap --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
      --ro-bind /etc /etc --proc /proc --dev /dev --tmpfs /home --tmpfs /tmp \
      --bind <PROJECT_ROOT> <PROJECT_ROOT> --chdir <PROJECT_ROOT> \
      --unshare-all --die-with-parent -- /bin/sh -c "<command>"
```

Stage 1 is a convenience. **Stage 2 is the boundary.** Stage 1 is trivially bypassed by `eval`,
`$HOME`, or a path built at runtime, and the design assumes it will be — which is exactly the
case SC-005 requires evidence for. When the kernel denies an access, the resulting error is
returned as an ordinary observation (FR-012b) with `metadata.blocked_by = "sandbox"`.

**Startup probe**: at session start, `bwrap --version` plus one throwaway sandboxed command must
succeed. If either fails, `run_bash` is **not offered as a tool at all** and the session says so.
Degrading to text-inspection-only would leave a tool advertised as sandboxed that is not.

**Network**: `--unshare-all` removes it. The acceptance tasks need none; this also satisfies
Constitution VII's prohibition on unfiltered outbound connections by construction.

### Behaviour

| Condition | `outcome` | `content` |
|---|---|---|
| Exit code 0 | `ok` | stdout, stderr, exit status |
| Non-zero exit | `error` | stdout, stderr, exit status — all three reach the agent |
| Timeout | `error` | States the timeout and its limit; `metadata.timed_out = true` |
| Stage 1 refusal | `refused` | Names the offending path; `blocked_by = "text"` |
| Kernel denial | `error` | The command's own error text; `blocked_by = "sandbox"` |
| Path names `.agent_runs/` | `refused` | The log is not writable by the agent |
| `bwrap` unavailable | — | Tool is not offered; session states why at startup |

**A timeout is not retried** (research §R3). FR-010 calls it an ordinary observation; the agent
decides what to do. Retrying a 30 s timeout three times would spend 90 s of the wall-clock budget
on a command that was already declared stuck.

**Output caps**: stdout and stderr are each capped at 8 KB in the observation, with the true
length stated. Prevents one runaway command from consuming the context window.

**Process group**: the child runs in its own process group so an interrupt kills the whole tree,
not just `/bin/sh`. `--die-with-parent` is the backstop if the signal path fails.
