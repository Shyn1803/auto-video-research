# CLAUDE.md — AI Workspace Entry Point

**Project:** AI Content Research & Video Automation Platform ("AVR")
**Status:** Pre-code. `docs/` is a complete BA/architecture handoff package (~30 files). No source code, no `package.json`/`pyproject.toml`, no CI, no tests exist yet. First commits will implement stories 1.1 and 2.1 from `docs/backlog/epics.md`.

This file orchestrates every other file in `.claude/`. Read it first, every session.

---

## 1. Project Overview (30 seconds)

A Vietnamese-language system that researches a topic, fact-checks claims (PASS/WARN/FAIL per claim), writes a script, turns it into a storyboard, and renders a short video via **Remotion** — either on a schedule (Mode 1: Daily AI News) or interactively (Mode 2: user-driven). Local-first: runs with **0 API keys** (Ollama, edge-tts, SearXNG, local Stable Diffusion); paid providers activate only via env API key + `ALLOW_PAID=true`. Full production scope — Phases are delivery order, not scope cuts.

Non-negotiable architectural rule, repeated everywhere for a reason: **AI never chooses layout.** AI produces a Semantic Storyboard (content + intent only). A deterministic, non-LLM Layout Engine (Classifier → Constraint Resolver → Theme → Motion Planner) decides bố cục/position/motion. See [context/architecture.md](context/architecture.md) and `docs/specs/layout-engine.md`.

## 2. Document Loading Order

When you start a task, load in this order — stop as soon as you have enough:

1. This file (`CLAUDE.md`) — orchestration + priority rules.
2. [memory/project-memory.md](memory/project-memory.md) — current state, known issues, open questions. **Always check this — it changes between sessions.**
3. [tasks/](tasks/) + [docs/backlog/stories/sprint-status.yaml](../docs/backlog/stories/sprint-status.yaml) — **the actual work queue for an agent team**: 65 self-contained, dev-ready task files across 10 epics, dependency graph, task→agent ownership. Claim a task by setting it `in-progress` in `sprint-status.yaml` before starting — see [tasks/README.md](tasks/README.md). This is where a multi-agent run should start after reading this file and memory. **If told to run/execute the whole backlog (not just one task), go to §10 below instead of picking a single task manually.**
4. [context/](context/) — the specific context doc(s) matching your task (architecture, tech-stack, business-domain, glossary...).
5. [rules/](rules/) — the specific rule file(s) that govern the code/doc you're about to touch.
6. The matching [workflows/](workflows/) file if your task fits a known workflow (feature, bug fix, migration, release...). Executing anything from `tasks/` → always load [workflows/autonomous-task-execution.md](workflows/autonomous-task-execution.md) first (claim/branch/retry/git/retrospective mechanics, not repeated per task).
7. The real source doc in `docs/` (SRS.md, ARCHITECTURE.md, backlog/*, specs/*) — `.claude/context/` summarizes and points at these; `docs/` is authoritative for detail. `.claude/tasks/` is a derived execution view of `docs/backlog/` — if they disagree, `docs/backlog/` wins, fix the task file.
8. [patterns/](patterns/) and [anti-patterns/](anti-patterns/) relevant to the component you're building.
9. [templates/](templates/) and [checklists/](checklists/) at the point you produce an artifact (PR, ADR, postmortem, story).

## 3. Priority Rules (conflict resolution)

1. **User's explicit instruction in the current conversation** — always wins.
2. **`docs/` normative specs** (SRS.md, ARCHITECTURE.md, CONFIGURATION.md, specs/*) — the contract. If `.claude/` contradicts `docs/`, `docs/` wins and `.claude/` is stale — fix it (see §9).
3. **`.claude/rules/`** — engineering conventions not yet codified in `docs/` (naming, git, PR hygiene).
4. **`.claude/patterns/`** — how, not what; adapt to context.
5. Never invent a fact `docs/` doesn't state. If unknown, say `Unknown — TODO` rather than guessing.

**Don't stop the workflow to ask unless you have to.** Every "Escalation" line in `.claude/agents/*.md` is governed by [rules/autonomy-policy.md](rules/autonomy-policy.md) — default is decide-and-continue for anything reversible and locally-scoped; only genuinely irreversible, contract-novel, scope-ambiguous, product-owned, or conflicting-instruction situations warrant stopping to ask, and even then prefer flagging + continuing other work over a hard block. `.claude/settings.json` pre-authorizes the routine, reversible tool calls (build/test/lint/git-read/git-commit/edit) so the harness itself doesn't interrupt for those.

**Git push to a feature branch is durably pre-authorized** (user decision, 2026-07-13): auto branch-checkout, auto-commit, and auto-`push origin feat/*` happen with no per-action confirmation during task execution — see [workflows/autonomous-task-execution.md](workflows/autonomous-task-execution.md) "Git automation scope" and the scoped allow-rules in `.claude/settings.json`. Push to `main`, force-push, and opening a PR remain gated — this authorization does not extend to those.

## 4. Reasoning Strategy

- **Before writing code**: identify which epic/story (`docs/backlog/epic-XX-*.md`) this work maps to. If none exists, flag it — don't silently expand scope.
- **Before touching `app/schemas/scene.py` or anything under "đổi contract"** (see `docs/dev-guide.md` §5): treat as high-blast-radius — check [rules/architecture.md](rules/architecture.md) and the Scene JSON contract rules first.
- **Before writing a Remotion composition/primitive/preset**: this is dev-time work — invoke the matching Remotion Agent Skill per `docs/dev-guide.md` §2.1 (`/remotion-markup`, `/remotion-captions`, `/remotion-saas`, `/remotion-interactivity`, `/remotion-create`, `/remotion-best-practices`). This project's own skill-selection table lives there, not duplicated here.
- **When something is ambiguous or contradicts `docs/`**: stop and report the inconsistency rather than resolving it silently. Real example this project already hit: an ambiguous line in `remotion-integration.md` implied merge might use `renderMedia()` — caught and fixed before it became code. See [postmortems/](postmortems/).

## 5. Coding Principles (apply once code exists)

Since no code exists yet, these are commitments extracted from `docs/dev-guide.md` §4, to be enforced from the first PR:

- Python: ruff, mypy strict on new `app/` code, async by default, SQLAlchemy 2.0 `select()` style, no business logic in routers.
- TypeScript: eslint + prettier, API types generated from OpenAPI — never hand-write duplicate interfaces.
- No adapter reads env directly — config flows through `ProviderSettings`.
- No direct provider calls from business logic — always through an adapter (see [patterns/provider-adapter.md](patterns/provider-adapter.md)).
- Trunk-based git, Conventional Commits, story ID in commit subject (`feat(scene): S1.3-04 ...`).

## 6. Update Policy

- **Docs are not append-only.** When you learn something that changes a prior doc, edit that doc — don't leave two conflicting versions.
- **Never duplicate** — if `docs/` already states a fact, `.claude/` should link to it (`docs/glossary.md`), not restate it.
- **Version-sensitive facts** (env defaults, schema fields, chain order) live in exactly one place: `docs/CONFIGURATION.md` / `docs/specs/scene-json-schema.md`. `.claude/` references, never copies, these tables.

## 7. Documentation Policy

- `docs/` = product/architecture handoff, owned by BA/PO process, changes on explicit user (Product Owner) decision.
- `.claude/` = AI operating knowledge — engineering process, agent behavior, accumulated lessons. Claude may update `.claude/` autonomously as part of the continuous learning loop below; `docs/` changes still require the workflow used throughout this project (propose → user confirms, since decisions are marked "PO <date>").

## 8. Continuous Learning Policy

After every completed task, run the retrospective in [memory/project-memory.md](memory/project-memory.md) header. Concretely:

1. What changed? (one line)
2. What did I learn that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Does it belong in a rule, pattern, anti-pattern, ADR, postmortem, or memory entry? Pick the narrowest fitting type — see [knowledge-curator agent](agents/knowledge-curator.md) for the decision rule.
4. Write it. Don't leave it only in chat history.

Bugs fixed (once code exists) → propose a postmortem using [templates/postmortem.md](templates/postmortem.md). Architectural decisions → an ADR using [templates/adr.md](templates/adr.md) in [decisions/](decisions/).

For work done via [tasks/](tasks/), this retrospective is not optional — it's a required step in [tasks/TASK-TEMPLATE.md](tasks/TASK-TEMPLATE.md) and [workflows/autonomous-task-execution.md](workflows/autonomous-task-execution.md), gated by DoD passing and required before a task's state file can be set to `done`.

## 9. Project Structure (target — not yet scaffolded)

No `backend/`, `frontend/`, `packages/`, `render-worker/` directories exist yet — only `docs/` and `.claude/`. Task `1-1` creates this structure; every later task assumes it exists. Full detail: `docs/dev-guide.md` §1 and [context/folder-structure.md](context/folder-structure.md) (do not restate it a third time here).

```
auto-video-research/
├── backend/app/{api,core,models,schemas,services,pipeline,adapters,events,workers}/  # FastAPI, Python 3.12
├── backend/{alembic,tests}/
├── frontend/src/{app,components,lib/api,lib/sse.ts}          # Next.js 15 App Router, TypeScript
├── packages/remotion-templates/src/{SceneRenderer.tsx,primitives,motion,theme,presets/layouts,schema.ts}
├── render-worker/                                             # Node.js + Remotion CLI + NATS consumer
├── docker/
├── docs/                                                      # normative spec, exists today
└── .claude/                                                   # AI operating knowledge, exists today
```

`app/schemas/scene.py` (Pydantic) is the one Scene JSON source of truth, exported to JSON Schema then Zod — never hand-edit the generated Zod file. `packages/remotion-templates/` is shared source between the frontend `<Player>` and `render-worker`'s `renderMedia()` — one implementation, not a fork per side.

## 10. Running the Full Backlog ("chạy toàn bộ task" / run all tasks)

When told to run the whole backlog, run continuously, or work through all tasks (not just one), this is the entry point — an agent should not need to ask what to do next:

1. Read this file, then [memory/project-memory.md](memory/project-memory.md) (current state + Open Questions), then [tasks/README.md](tasks/README.md) in full — it has the dependency graph, task→agent ownership table, and per-task DoD.
2. Read [rules/autonomy-policy.md](rules/autonomy-policy.md) and [workflows/autonomous-task-execution.md](workflows/autonomous-task-execution.md) **once**, at the start of the run — they define the claim → branch → execute → retry → commit/push → retrospective → next-task loop and are not repeated per task.
3. Check [tasks/state/RUN-STATUS.md](tasks/state/RUN-STATUS.md) for a one-glance rollup of every task's status before picking work — resume `in-progress`/`blocked` tasks via their `tasks/state/{id}.json` rather than restarting them.
4. Work tasks in dependency order (`Depends:` line in each task file; the two parallel tracks and full index are in `tasks/README.md`). Multiple unblocked tasks may run in parallel across sub-agents, dispatched per the task→agent ownership table in `tasks/README.md`.
5. **Do not stop between tasks to ask for confirmation.** Per `rules/autonomy-policy.md`: decide and continue on anything reversible/locally-scoped; a blocked task gets flagged (state file `blocked_reason` + `memory/project-memory.md` Open Questions) and the run moves to a different unblocked task — it never halts the whole run. Git checkout/commit/push to `feat/*` is durably pre-authorized (§3 above) — no per-action confirmation needed for that either.
6. Only genuinely stop the whole run for: a product/business decision (PO-owned), a contract change with no precedent in `docs/specs/`, or literally every remaining task being blocked with nothing else to work on. Otherwise: claim next unblocked task → repeat from step 4.
7. This loop has no fixed end condition other than the backlog — 65 tasks across 10 epics, 230 points, per `tasks/README.md`'s full index. Stop only when every task is `done` or every remaining task is `blocked`.

## 11. Known Gaps (honest state, not guessed)

- No code, no `package.json`/`pyproject.toml`, no CI workflow, no test suite exist. Everything in `context/build-process.md`, `context/testing-strategy.md`, `rules/*` about actual tooling behavior is **intent from `docs/dev-guide.md` and `docs/test-plan.md`, not yet verified against a real build.** Update these files with real findings once Phase 1 week 1 code lands.
- `docs/specs/remotion-integration.md` has a cosmetic section-numbering gap (§3 renumbered to §5, no standalone §3) — not fixed, not user-flagged, low priority.
- This `.claude/` scaffold was generated in one bootstrap pass from `docs/` — treat initial content as a first draft, not settled law. Sanity-check against `docs/` before relying on any specific number.

## 12. Shell environment

- Operating system: Windows 11
- Default shell: PowerShell 7
- All generated shell commands must be valid PowerShell.
- Never use Bash heredoc syntax such as `<<EOF`.
- Never use Bash command substitution such as `$(cat ...)`.
- For multiline strings, use PowerShell here-strings: `@"..."@`.
- Prefer simple single-line Git commit messages.