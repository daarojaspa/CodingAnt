# Project Constitution — No-Framework Coding Agent

> These are the durable, non-negotiable rules for this project. They hold true
> across every phase. The phase roadmap (P0–P2…) is **not** part of this
> document — it belongs in the spec, because it changes as the project moves.

## 1. Purpose & Learning Goal
- This project builds a coding agent **from primitives, with no agent frameworks** (no LangGraph, LlamaIndex, etc.). The point is to understand
  what those frameworks hide.
- The learning goal is met, per phase, only when the phase's own "done when" gate passes — e.g. being able to explain the `messages` array and turn
  structure from memory. Understanding is verified by that gate, not assumed.

## 2. Stack & Dependencies
- **Python 3.11+.**
- **The official Anthropic API SDK** (the `anthropic` package, using an API
  key). No agent frameworks of any kind.
  <!-- Note: "Claude Pro" is a subscription plan, not an SDK. Claude Code is
       itself a framework and is out of scope by rule 1. -->
- Use a **`src/` layout**.
- **`uv`** manages Python versions, virtual environments, and dependencies.
  The lock file is **always committed**.
- **`ruff`** for formatting and linting.
- **PEP 8** conventions. **SOLID** principles. Design patterns only where they
  measurably improve readability or efficiency — never applied for their own sake.
- No new dependency is added without a one-line written justification (in the plan or commit message) explaining why the standard library is insufficient.

## 3. Version Control & CI/CD
- **Git** for version control.
- GitHub best practices: feature branches, pull requests, issue management.
- CI/CD via **GitHub Actions**.

## 4. Change Size Limits
- File: **≤ 300 lines.**
- Class: **≤ 150 lines.**
- Function: **≤ 30 lines.**
- No single pull request changes more than **300 lines.**
- Every class and module most have a single clearly namable responsability . if you cna not state it's reason to exist in one line it should not be a separate class or module, inline or merge it .
## 5. Secrets & Confidential Data
- API keys, security tokens, and any confidential information that represents a
  security risk MUST live in `.env` files or files listed in `.gitignore`.
  They are never committed.

## 6. Safety — Absolute Prohibitions
Under no circumstance may the agent write or run software that performs:
- **Data erasure or ransom:** deleting critical OS files, or encrypting
  personal files to lock the user out (ransomware).
- **Hardware degradation:** overclocking, disabling cooling, or sustained loops
  that push CPU/GPU to thermal limits.
- **Firmware corruption:** rewriting BIOS/UEFI or "bricking" hardware.
- **Resource hijacking:** using network bandwidth for botnet/DDoS, or maxing
  hardware to mine cryptocurrency.
- **Identity & financial theft:** stealing session cookies, saved passwords,
  credit card data, or crypto wallet keys.
- **Surveillance:** activating webcam or microphone without consent, or
  keylogging.
- **Extortion or psychological distress:** exfiltrating private files to
  blackmail, or triggering flashing patterns/sounds meant to cause harm
  (e.g. seizures).

## 7. Safety — Consent-Gated Actions
These require explicit user consent, sandboxing, or OS permission gates
(e.g. Windows UAC, macOS Permissions). The agent must never do them silently:
- **Elevated/admin privileges:** a program must never grant itself root/admin.
- **Unfiltered outbound connections:** connecting to unknown external IPs to
  send data or download hidden payloads.
- **Persistent installation:** adding itself to startup registries, background
  services, or cron jobs.
- **Hardware device access:** camera, microphone, location, external storage.
- **Filesystem access outside the project folder:** no reading, writing, or
  deleting outside this project directory (e.g. Documents, Downloads, `.ssh`).
- **Inter-process inspection:** reaching into another running app's memory.

## 8. Credentials & Human Gates
- The human controls all GitHub credentials.
- Every push and every pull-request merge must be reviewed and approved by the
  human before it happens.

## 9. Testing
- Unit tests in **pytest**, covering failure paths and edge cases, and verifying the code raises the correct exceptions.
- **Strict mocking boundaries:** use `pytest-mock` / `unittest.mock` to isolate
  network requests, database queries, and system clocks. A test never makes a
  real API call.

## 10. Error Handling
- **Never catch generic exceptions.** `except Exception:` or a bare `except:`
  is forbidden — it swallows bugs and breaks debugging.
- **Catch specific exceptions** only (e.g. `except KeyError:`,
  `except FileNotFoundError:`).
- **Rethrow with context:** when catching to log or translate, use
  `raise NewException from err` to preserve the original traceback.
- **Keep `try` blocks minimal:** wrap only the single line that can fail, never
  a whole function.
