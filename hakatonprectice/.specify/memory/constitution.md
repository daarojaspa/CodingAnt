<!--
Sync Impact Report
==================
Version change: (unfilled template) → 1.0.0
Bump rationale: Initial ratification. All placeholder tokens replaced with concrete,
enforceable rules supplied by the project owner.

Modified principles:
- [PRINCIPLE_1_NAME] → I. Primitives Over Frameworks (NON-NEGOTIABLE)
- [PRINCIPLE_2_NAME] → II. Single Responsibility & Size Limits
- [PRINCIPLE_3_NAME] → III. Explicit Error Handling (NON-NEGOTIABLE)
- [PRINCIPLE_4_NAME] → IV. Isolated Tests Covering Failure Paths
- [PRINCIPLE_5_NAME] → V. Secrets Never Enter Version Control (NON-NEGOTIABLE)

Added sections:
- VI. Absolute Safety Prohibitions (NON-NEGOTIABLE)  [new principle beyond template's 5]
- VII. Consent-Gated Actions (NON-NEGOTIABLE)        [new principle beyond template's 5]
- [SECTION_2_NAME] → Stack & Dependency Constraints
- [SECTION_3_NAME] → Development Workflow & Human Gates

Removed sections: none

Deferred items / TODOs: none
Scope note: The phase roadmap (P0–P2…) is deliberately excluded from this document and
lives in the spec, because it changes as the project moves.
-->

# No-Framework Coding Agent Constitution

## Core Principles

### I. Primitives Over Frameworks (NON-NEGOTIABLE)

This project builds a coding agent from primitives. Agent frameworks (LangGraph, LlamaIndex,
or any equivalent) MUST NOT be introduced at any layer. Claude Code is itself a framework and
is therefore out of scope as a runtime dependency. The purpose of the constraint is to
understand what those frameworks hide.

The learning goal is met, per phase, only when that phase's own "done when" gate passes — for
example, being able to explain the `messages` array and turn structure from memory.
Understanding MUST be verified by that gate; it is never assumed from working code.

### II. Single Responsibility & Size Limits

Every module and class MUST have one responsibility that can be stated in a single line. If
that line cannot be written, the unit MUST be inlined or merged rather than kept separate.

Hard ceilings, enforced at review:

- File: ≤ 300 lines
- Class: ≤ 150 lines
- Function: ≤ 30 lines
- Pull request: ≤ 300 changed lines

SOLID principles and PEP 8 apply. Design patterns are used only where they measurably improve
readability or efficiency — never for their own sake.

### III. Explicit Error Handling (NON-NEGOTIABLE)

- `except Exception:` and bare `except:` are forbidden. They swallow bugs and break debugging.
- Only specific exceptions may be caught (e.g. `except KeyError:`, `except FileNotFoundError:`).
- When catching to log or translate, rethrow with `raise NewException from err` so the original
  traceback is preserved.
- `try` blocks MUST wrap only the single line that can fail, never a whole function.

### IV. Isolated Tests Covering Failure Paths

Unit tests use pytest and MUST cover failure paths and edge cases, including assertions that the
correct exception type is raised.

Mocking boundaries are strict: network requests, database queries, and system clocks MUST be
isolated with `pytest-mock` / `unittest.mock`. A test NEVER makes a real API call.

### V. Secrets Never Enter Version Control (NON-NEGOTIABLE)

API keys, security tokens, and any confidential information that represents a security risk MUST
live in `.env` files or other files listed in `.gitignore`. They are never committed.

### VI. Absolute Safety Prohibitions (NON-NEGOTIABLE)

Under no circumstance may the agent write or run software that performs:

- **Data erasure or ransom:** deleting critical OS files, or encrypting personal files to lock
  the user out (ransomware).
- **Hardware degradation:** overclocking, disabling cooling, or sustained loops that push
  CPU/GPU to thermal limits.
- **Firmware corruption:** rewriting BIOS/UEFI or "bricking" hardware.
- **Resource hijacking:** using network bandwidth for botnet/DDoS activity, or maxing hardware
  to mine cryptocurrency.
- **Identity & financial theft:** stealing session cookies, saved passwords, credit card data,
  or crypto wallet keys.
- **Surveillance:** activating webcam or microphone without consent, or keylogging.
- **Extortion or psychological distress:** exfiltrating private files to blackmail, or
  triggering flashing patterns or sounds meant to cause harm (e.g. seizures).

This principle has no exception clause and cannot be waived by any workflow, review, or human
approval described elsewhere in this document.

### VII. Consent-Gated Actions (NON-NEGOTIABLE)

The following require explicit user consent, sandboxing, or an OS permission gate (e.g. Windows
UAC, macOS Permissions). The agent MUST NEVER perform them silently:

- **Elevated/admin privileges:** a program must never grant itself root or admin.
- **Unfiltered outbound connections:** connecting to unknown external IPs to send data or
  download hidden payloads.
- **Persistent installation:** adding itself to startup registries, background services, or
  cron jobs.
- **Hardware device access:** camera, microphone, location, external storage.
- **Filesystem access outside the project folder:** no reading, writing, or deleting outside
  this project directory (e.g. Documents, Downloads, `.ssh`).
- **Inter-process inspection:** reaching into another running application's memory.

## Stack & Dependency Constraints

- **Python 3.11+.**
- **The official Anthropic API SDK** (the `anthropic` package, authenticated with an API key) is
  the only supported model interface. "Claude Pro" is a subscription plan, not an SDK, and is
  not a substitute. No agent frameworks of any kind (see Principle I).
- **`src/` layout** is mandatory.
- **`uv`** manages Python versions, virtual environments, and dependencies. The lock file is
  ALWAYS committed.
- **`ruff`** performs formatting and linting.
- No new dependency is added without a one-line written justification — in the plan or the
  commit message — explaining why the standard library is insufficient.

## Development Workflow & Human Gates

- **Git** is the version control system, following GitHub best practices: feature branches,
  pull requests, and issue management.
- **CI/CD runs on GitHub Actions.**
- **The human controls all GitHub credentials.**
- **Every push and every pull-request merge MUST be reviewed and approved by the human before
  it happens.** The agent never pushes or merges on its own authority.

## Governance

This constitution supersedes all other practices, conventions, and agent instructions in this
repository. Where a plan, spec, or prompt conflicts with it, this document wins.

- **Scope:** These rules are durable and hold across every phase. The phase roadmap (P0–P2…) is
  NOT part of this document; it belongs in the spec, because it changes as the project moves.
- **Amendment procedure:** Amendments are proposed as a pull request that modifies this file,
  states the version bump and its rationale, and is approved by the human owner before merge.
  Principles marked NON-NEGOTIABLE may be clarified but not weakened or removed without an
  explicit MAJOR version bump.
- **Versioning policy:** Semantic versioning.
  - MAJOR — backward-incompatible governance or principle removals/redefinitions.
  - MINOR — a new principle or section is added, or guidance is materially expanded.
  - PATCH — clarifications, wording, typo fixes, non-semantic refinements.
- **Compliance review:** Every pull request review MUST verify compliance with the size limits
  (Principle II), error-handling rules (Principle III), test isolation (Principle IV), and
  secret handling (Principle V). Any added complexity or new dependency MUST be justified in
  writing. Violations block merge.

**Version**: 1.0.0 | **Ratified**: 2026-08-06 | **Last Amended**: 2026-08-06
