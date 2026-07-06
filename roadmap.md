# Nocturne — Build-an-Agent Roadmap (0 → expert)

One repo that evolves across 8 phases. Each phase ends in a **deliverable** that becomes the **input** to the next. You're done with a phase when the "Done when" test passes — not when it "feels" done.

**The spine:** model → tool call → observation → next decision. Everything you build is control around that loop. No framework until **P6**. Local, raw Python, raw Anthropic API, SQLite.

**Pairing rule:** through **P3 you write the loop and tool dispatch by hand** — use Claude to explain/review/debug, never to generate the orchestration. From P4 on, let it write boilerplate, because by then you know what the boilerplate does.

**Project name:** `nocturne` (it runs at night). Pick your own if you like.

---

## Prereqs (only if rusty — you have ~2 yrs software, so probably skip most)
- [ ] **Git y GitHub** (you're at 58%) — finish it. You'll version `nocturne` from commit one.
- [ ] **Python Intermedio (venv, PEP8)** — just the virtualenv part, so your repo is clean.
- *Skip:* Pensamiento Lógico, Fundamentos de Python, Python OOP, Estadística (done, and it's for the master's not this).

---

## P0 — The raw loop (no tools)
- **Goal:** understand the `messages` array and the turn structure. Nothing else.
- **Build:** `p0_loop.py` — one API call inside a `while` loop. You print the model's reply, type a fake "observation" back, it continues.
- **Deliverable:** a script that holds a coherent multi-turn conversation where *you* are manually feeding observations.
- **Done when:** you can explain, with no notes, what's in `messages` at each turn and why the reply depends on the full history.
- **Feeds forward:** this loop becomes the agent's heartbeat — every later phase wraps it.
- **Courses that fit:** *Configuración de APIs de LLMs* (auth + calling), *Fundamentos de LLMs* (mental model, you're at 63%). Skim *OpenAI API* only if curious — concepts transfer, but you're on Anthropic.
- **Time:** ~1 day.

## P1 — Tool calling by hand
- **Goal:** the model acts on the real world. This is the core frameworks hide.
- **Build:** add `read_file`, `write_file`, `run_bash`. Parse the model's tool-use request, dispatch to your real Python function, return the result as the observation.
- **Deliverable:** agent that, told "create hello.py that prints hello, then run it," actually does both.
- **Done when:** it completes a 2-tool task end-to-end with zero intervention from you.
- **Feeds forward:** tools are the hands; P2–P7 are all about controlling them.
- **Courses that fit:** *none.* Do not start the *Agentes AI* course here — it teaches framework agents and will re-hide the loop you're trying to see. Build this by hand.
- **Time:** ~2–3 days.

## P2 — Control flow & failure handling
- **Goal:** make it survive things going wrong (prerequisite for unattended running).
- **Build:** max-iteration cap, an explicit stop condition (how does it *know* it's done?), `try/except` around every tool, retries, a token/turn budget. Then deliberately break a tool and watch it.
- **Deliverable:** agent that recovers from a thrown tool error and exits *cleanly with a stated reason* on a task it can't finish (instead of looping forever / burning tokens).
- **Done when:** you kill a tool mid-run and it either recovers or stops gracefully — never spins.
- **Feeds forward:** robustness is what lets P5 run overnight without supervision.
- **Courses that fit:** *Unit Testing en Python* (start it — you'll lean on it hard next).
- **Time:** ~2–3 days.

## P3 — Coding agent with ground truth (this opens your black box)
- **Goal:** turn it into a coding agent *and* see the full software-dev loop, with objective feedback.
- **Build:** a task = a **failing pytest suite**. The agent reads the tests, writes code, runs pytest, reads the failures, iterates until green or budget runs out. This is plan → work → review in miniature.
- **Deliverable:** 3 toy "katas" (failing tests); the agent makes ≥2 pass unattended.
- **Done when:** a *fresh* kata it's never seen goes red → green with no help from you.
- **Feeds forward:** the test suite **is** your eval; pass-rate is your first real metric (this matters for SPAR/your thesis). The pytest loop is the SDLC you said felt opaque — now you've built it.
- **Courses that fit:** *Unit Testing en Python* (finish). For the *theory* of SDLC, cherry-pick the **Requirements + Testing** modules of the Reykjavik playlist — don't watch all 75; the build teaches the rest.
- **Time:** ~4–6 days. **You're "competent" here.**

## P4 — Memory & observability
- **Goal:** be able to inspect what it did while you slept. (This is also literal agent interpretability — your research line.)
- **Build:** log every step (prompt, tool, args, result, tokens, cost, timestamp) to **SQLite**. Write `inspect.py` that renders a run as a readable timeline. Optional: session memory so it can resume.
- **Deliverable:** a SQLite DB of runs + a script that prints "what happened last night."
- **Done when:** you can reconstruct a full run from the DB alone, without re-running it.
- **Feeds forward:** this is the "read results in the morning" capability, and the data layer P5 schedules against.
- **Courses that fit:** *Fundamentos de Bases de Datos y SQL*. *Observabilidad de Agentes AI con LangSmith* (you're at 9%) — watch it here to see how pros visualize traces, then build your own simple version. Supabase is a fine swap for SQLite once you outgrow it.
- **Time:** ~3–4 days.

## P5 — Autonomy (the overnight run)
- **Goal:** the actual goal you stated — queue tasks at night, read the report at breakfast.
- **Build:** a task queue (a folder or a table of pending tasks), a runner that pulls one, executes, logs, moves to the next. Schedule with cron. Add a **cost ceiling** and a **hard guardrail** (no `rm -rf`, no network beyond the API, $ cap).
- **Deliverable:** queue 3 tasks at night → wake up to a morning report (pass/fail + cost per task).
- **Done when:** it ran unattended ≥6 hours, cleared the queue, stayed under budget, broke nothing.
- **Feeds forward:** you now own a *platform*, not a script.
- **Courses that fit:** *none core.* (*RPA e Hiperautomatización* is optional and framework-heavy — skip unless curious.) Cron + your own code is the lesson.
- **Time:** ~3–5 days.

## P6 — Lift the curtain (kill the "hidden behind the interface" feeling)
- **Goal:** see exactly what the frameworks were doing for you — by comparison, not faith.
- **Build:** re-implement **one** component (the loop, or tool routing) with **LangGraph** or the **Claude Agent SDK**. Diff it against your hand-built version. Then install the **compound-engineering plugin** and watch its plan→work→review→compound loop run on `nocturne` itself.
- **Deliverable:** a branch with the framework version + a 1-page note: what it abstracted, what it hid, what you'd keep DIY.
- **Done when:** you can name 3 specific things the framework did for you and say whether each was worth it.
- **Feeds forward:** frameworks become a *choice*, not a mystery. This unlocks the rest of your courses.
- **Courses that fit (finally!):** *LangChain*, *LangChain para Documentos*, *Agentes AI*, *RAG con Azure* (the one that frustrated you — it'll click now), *MCP con Azure*, *Cursor AI*, *Claude Code* (you're at 23%). Watch the ones you'll actually use; skip the rest.
- **Time:** ~1 week. **You understand the whole stack here.**

## P7 — Expert: safety artifact + portfolio
- **Goal:** a genuine AI-safety contribution that doubles as your portfolio + SPAR/BAISH/thesis material.
- **Build:** add an **oversight monitor** — a second model pass (or rule layer) that reviews each action and flags unsafe/off-task behavior before it runs. Inject a few "bad" tasks and measure how often the monitor catches them.
- **Deliverable:** monitored agent + a public repo + a paragraph reporting your "monitor catch rate" on a handful of red-team tasks.
- **Done when:** you have a repo README + a results paragraph you could paste into a SPAR or BAISH application.
- **Feeds forward:** straight into your thesis method section (agent interpretability/oversight) and your safety applications.
- **Courses that fit:** *Prompt Engineering* (for the monitor's prompt). The safety framing itself isn't on Platzi — that's BlueDot/SPAR.
- **Time:** ~1 week.

---

## The compound layer (don't build it separately — bolt it on from P4)
The every.to idea: each task's lessons get **codified** so the next task is easier. Once you have logging (P4) + a queue (P5), add a `LESSONS.md` (or `CLAUDE.md`) that the agent reads each run and appends to when something breaks or works. That single file is the difference between a script and a system that gets smarter. Install the official plugin at P6 *after* you've felt the loop by hand — otherwise it's just another black box.

## Courses to SKIP (friction reduction — these don't serve this project)
- Chatbots con OpenAI / Chatbots con AzureOpenAI / ChatBot con WhatsApp API — product-builder courses, not agent internals.
- The n8n 30-day challenge (Tribu IA) — pure frameworks-first; it's the exact trap you're escaping. Maybe peek at P6 to see n8n, not before.
- Herramientas de AI para Developers, the basic "Conoce Claude AI" intros — usage, not building.
- The full 75-video Reykjavik playlist — cherry-pick Requirements + Testing only.

## One-line summary
P0–P3 by hand = you understand agents and SDLC. P4–P5 = it runs overnight. P6 = frameworks stop being magic. P7 = you have a safety portfolio piece. Courses slot in *after* you've built the thing they explain, not before.
### Practical ways to automate the emulation

#### 1) Define agent roles
Create separate “virtual agents” with specific responsibilities, for example:
- **Product/requirements agent**: clarifies the task and acceptance criteria
- **Architect agent**: proposes design and interfaces
- **Coder agent**: writes implementation
- **Reviewer agent**: checks correctness, style, edge cases
- **QA/test agent**: generates and runs tests
- **DevOps agent**: checks packaging, env vars, deployment concerns

This makes the process feel like a real team instead of one monolithic assistant.

#### 2) Use a shared workspace/state
Store:
- task description
- assumptions
- design decisions
- code diffs
- test results
- open questions

Use a shared JSON/YAML file or a lightweight database so each agent can read and update context.

#### 3) Build a pipeline or orchestration layer
Automate the sequence:
1. intake task
2. clarify requirements
3. design proposal
4. implementation
5. review
6. test
7. fix
8. finalize

This can be done with:
- a simple script
- a workflow engine
- an agent framework
- CI/CD integration

#### 4) Add automated feedback loops
Make agents critique each other:
- coder writes code
- reviewer finds issues
- tester generates failing cases
- coder fixes
- reviewer rechecks

This is the best way to simulate real team collaboration.

#### 5) Keep a “decision log”
Production teams leave breadcrumbs. Save:
- why a design was chosen
- tradeoffs
- known limitations
- follow-up work

This helps the emulation feel realistic and helps future tasks.

#### 6) Integrate with real dev tools
To make it feel like production:
- Git for branching and commits
- CI for tests/lint/build
- issue tracker style task files
- code formatting and static analysis
- containerized dev environment

#### 7) Use templates for common task types
For example:
- bug fix template
- feature template
- refactor template
- test-only task template
- incident/debug template

Templates can automatically generate the right agent workflow.

#### 8) Simulate async communication
Instead of one prompt, have agents send messages:
- “I need clarification”
- “I found a race condition”
- “Tests failed on edge case X”
- “Approved with minor changes”

This mirrors Slack/Jira/PR comments.

---

### A simple automation architecture
A good lightweight setup could be:

- **Task file**: `task.md`
- **State file**: `state.json`
- **Agent scripts**:
  - `planner.py`
  - `coder.py`
  - `reviewer.py`
  - `tester.py`
- **Runner**:
  - executes agents in order
  - stores outputs
  - loops on failures

---

### Best starting point
If you want something practical and not too complex:
1. Use **Git + local scripts**
2. Define **3 agents** first: planner, coder, reviewer
3. Add **tester** later
4. Save all outputs in a structured folder per task
5. Add CI once the workflow works

---

### Extra realism ideas
- Make each agent have different “style” or priorities
- Force them to disagree sometimes
- Require the reviewer to block merges
- Track “meeting notes” and “PR comments”
- Run tasks as if they were separate teammates with partial context

---