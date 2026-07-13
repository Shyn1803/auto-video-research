# AGENTS.md — Agent Entry Point (AVR)

**Project:** AI Content Research & Video Automation Platform ("AVR"). Vietnamese-language system: research a topic → fact-check claims (PASS/WARN/FAIL) → write a script → build a storyboard → render a short video with **Remotion**. Two modes: **Mode 1** (Daily AI News, scheduled, full-auto with a publish gate) and **Mode 2** (interactive, user-driven, step-by-step). Local-first — runs with **0 API keys** (Ollama, edge-tts, SearXNG, local Stable Diffusion); paid providers only activate via an env key + `ALLOW_PAID=true`.

**Status:** Pre-code. `docs/` (~30 files) is a complete BA/architecture handoff. No `backend/`, `frontend/`, `packages/`, `render-worker/` exist yet. First tasks: `1-1` (repo scaffold) and `2-1` (Scene JSON schema).

This file is the tool-agnostic counterpart to [.claude/CLAUDE.md](.claude/CLAUDE.md), which is the full, authoritative operating doc for this project (loading order, priority rules, coding principles, autonomy policy, known gaps). **Read `.claude/CLAUDE.md` in full before doing any non-trivial work here** — this file only orients you and gives the "run everything" procedure; it does not duplicate the detail.

## Non-negotiable rule

**AI never chooses layout.** AI output is a *Semantic Storyboard* (content + intent only — no position/font/animation/camera fields). A deterministic, non-LLM Layout Engine decides bố cục/position/motion. See [.claude/context/architecture.md](.claude/context/architecture.md) and [docs/specs/layout-engine.md](docs/specs/layout-engine.md). Any AI-produced JSON containing a layout/position/font/animation/camera field is a bug, not a style choice.

## Project structure (target — not yet scaffolded)

```
auto-video-research/
├── backend/app/{api,core,models,schemas,services,pipeline,adapters,events,workers}/  # FastAPI, Python 3.12
├── backend/{alembic,tests}/                                    # tests/{unit,integration,fixtures}/
├── frontend/src/{app,components,lib/api,lib/sse.ts}            # Next.js 15 App Router, TypeScript
├── packages/remotion-templates/src/{SceneRenderer.tsx,primitives,motion,theme,presets/layouts,schema.ts}
├── render-worker/                                               # Node.js + Remotion CLI + NATS consumer
├── docker/                                                      # compose files + per-service Dockerfiles
├── docs/                                                        # normative spec — SRS, ARCHITECTURE, CONFIGURATION, dev-guide, backlog/, specs/
└── .claude/                                                     # AI operating knowledge — agents, rules, patterns, tasks, workflows, memory
```

Full detail: [docs/dev-guide.md](docs/dev-guide.md) §1, [.claude/context/folder-structure.md](.claude/context/folder-structure.md).

## Priority order when sources disagree

1. The user's explicit instruction in the current conversation.
2. `docs/` normative specs (SRS.md, ARCHITECTURE.md, CONFIGURATION.md, specs/*) — the contract.
3. `.claude/rules/` — engineering conventions.
4. `.claude/patterns/` — how, not what.
5. Never invent a fact `docs/` doesn't state — say `Unknown — TODO`.

Full detail incl. escalation criteria: [.claude/rules/autonomy-policy.md](.claude/rules/autonomy-policy.md).

## Running the full backlog ("run all tasks")

When told to run the whole backlog, work continuously, or execute all tasks — not just one — this is the procedure. Full detail lives in [.claude/CLAUDE.md §10](.claude/CLAUDE.md) and [.claude/tasks/README.md](.claude/tasks/README.md); this is the short version:

1. Read `.claude/CLAUDE.md`, then `.claude/memory/project-memory.md` (current state + Open Questions), then `.claude/tasks/README.md` (dependency graph, task→agent ownership, full 65-task index).
2. Read `.claude/rules/autonomy-policy.md` and `.claude/workflows/autonomous-task-execution.md` once, at the start — they define the claim → branch → execute → retry → commit/push → retrospective → next-task loop.
3. Check `.claude/tasks/state/RUN-STATUS.md` for current status before picking work; resume any `in-progress`/`blocked` task via its `.claude/tasks/state/{id}.json` instead of restarting it.
4. Work tasks in dependency order (`Depends:` line per task file). Multiple unblocked tasks may run in parallel.
5. **Do not stop between tasks to ask for confirmation.** Decide and continue on anything reversible/locally-scoped. A blocked task gets flagged (state file `blocked_reason` + `project-memory.md` Open Questions) and the run moves to a different unblocked task — it never halts the whole run.
6. Git checkout/commit/push to `feat/*` branches is durably pre-authorized — no per-action confirmation needed. Push to `main`, force-push, and opening a PR remain gated (ask first).
7. Only stop the entire run for: a product/business decision (PO-owned), a contract change with no precedent in `docs/specs/`, or every remaining task being genuinely blocked. Otherwise: claim next unblocked task, repeat from step 4, until all 65 tasks (10 epics, 230 points) are `done` or blocked.

## Coding principles (once code exists)

- Python: ruff, mypy strict on new `app/` code, async by default, SQLAlchemy 2.0 `select()`, no business logic in routers.
- TypeScript: eslint + prettier, API types generated from OpenAPI — never hand-write duplicate interfaces.
- No adapter reads env directly — config flows through `ProviderSettings`. No direct provider calls from business logic — always through an adapter ([.claude/patterns/provider-adapter.md](.claude/patterns/provider-adapter.md)).
- Trunk-based git, Conventional Commits, story ID in the commit subject (`feat(scene): S1.3-04 ...`), branches `feat/{story-id}-mo-ta`.
- Default to no comments; only add one when the WHY is non-obvious.

## Where to look for more

| Need | File |
|---|---|
| Full operating doc, loading order, priority rules | [.claude/CLAUDE.md](.claude/CLAUDE.md) |
| Current state, known issues, open questions (check every session) | [.claude/memory/project-memory.md](.claude/memory/project-memory.md) |
| The 65-task work queue + dependency graph | [.claude/tasks/README.md](.claude/tasks/README.md) |
| Task execution mechanics (retry, resume, git automation) | [.claude/workflows/autonomous-task-execution.md](.claude/workflows/autonomous-task-execution.md) |
| Agent roles (backend/frontend/security/etc.) | [.claude/agents/](.claude/agents/) |
| Engineering rules (naming, git, testing, security...) | [.claude/rules/](.claude/rules/) |
| Normative product/architecture spec | [docs/](docs/) (SRS.md, ARCHITECTURE.md, CONFIGURATION.md, dev-guide.md, backlog/, specs/) |
