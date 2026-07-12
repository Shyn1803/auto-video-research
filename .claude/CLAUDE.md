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
3. [context/](context/) — the specific context doc(s) matching your task (architecture, tech-stack, business-domain, glossary...).
4. [rules/](rules/) — the specific rule file(s) that govern the code/doc you're about to touch.
5. The matching [workflows/](workflows/) file if your task fits a known workflow (feature, bug fix, migration, release...).
6. The real source doc in `docs/` (SRS.md, ARCHITECTURE.md, backlog/*, specs/*) — `.claude/context/` summarizes and points at these; `docs/` is authoritative for detail.
7. [patterns/](patterns/) and [anti-patterns/](anti-patterns/) relevant to the component you're building.
8. [templates/](templates/) and [checklists/](checklists/) at the point you produce an artifact (PR, ADR, postmortem, story).

## 3. Priority Rules (conflict resolution)

1. **User's explicit instruction in the current conversation** — always wins.
2. **`docs/` normative specs** (SRS.md, ARCHITECTURE.md, CONFIGURATION.md, specs/*) — the contract. If `.claude/` contradicts `docs/`, `docs/` wins and `.claude/` is stale — fix it (see §9).
3. **`.claude/rules/`** — engineering conventions not yet codified in `docs/` (naming, git, PR hygiene).
4. **`.claude/patterns/`** — how, not what; adapt to context.
5. Never invent a fact `docs/` doesn't state. If unknown, say `Unknown — TODO` rather than guessing.

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

## 9. Known Gaps (honest state, not guessed)

- No code, no `package.json`/`pyproject.toml`, no CI workflow, no test suite exist. Everything in `context/build-process.md`, `context/testing-strategy.md`, `rules/*` about actual tooling behavior is **intent from `docs/dev-guide.md` and `docs/test-plan.md`, not yet verified against a real build.** Update these files with real findings once Phase 1 week 1 code lands.
- `docs/specs/remotion-integration.md` has a cosmetic section-numbering gap (§3 renumbered to §5, no standalone §3) — not fixed, not user-flagged, low priority.
- This `.claude/` scaffold was generated in one bootstrap pass from `docs/` — treat initial content as a first draft, not settled law. Sanity-check against `docs/` before relying on any specific number.
