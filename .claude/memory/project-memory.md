# Project Memory

**Last updated:** 2026-07-12. Keep this concise — archive obsolete entries rather than letting this file grow unbounded. This is the one file every session should check first (see `CLAUDE.md` §2).

## Current State

Pre-code. `docs/` (~30 files) is a complete BA/architecture/design handoff package — SRS, ARCHITECTURE, CONFIGURATION, dev-guide, plan (18-week continuous timeline), 10 backlog epics (~55 stories), design system + interactive wireframe, full spec set (Scene JSON schema, Layout Engine, video-taste, Remotion integration, database schema, API spec, event catalog, prompts, test plan, runbook). `.claude/` operating system (this bootstrap) was generated 2026-07-12 in one pass from `docs/`.

**No source code, no `package.json`/`pyproject.toml`, no CI, no tests exist yet.** First real work: story 1.1 (repo scaffold) and 2.1 (Scene JSON schema), designed to run in parallel across 2 devs. Week 1 DoD: 30s 9:16 video from hand-written Scene JSON, Vietnamese voice, synced subtitle.

## Known Issues

- `docs/specs/remotion-integration.md` has a cosmetic section-numbering gap (§4 was inserted before the old §3, which got renumbered to §5 — no standalone §3 exists). Not user-flagged, not fixed, low priority.
- `.claude/` content was generated from `docs/` in a single bootstrap pass — treat as first draft; cross-check specific numbers against `docs/` before relying on them, per [context/architecture.md](../context/architecture.md) staleness note in CLAUDE.md §9.

## Technical Debt

None yet — no code exists to accrue debt in. Watch for: Constraint Resolver v1 uses fixed presets per layout class (not a general solver) — explicitly deferred to v1.1+ per ADR-0008, revisit only if the 11-class catalog becomes a demonstrated bottleneck.

## Lessons Learned (see full detail in postmortems/ and mistakes/)

- A principle stated in one prominent doc location isn't automatically propagated everywhere it's referenced — verify via exhaustive search, not memory (M-001).
- An ambiguous sentence in a spec is often a symptom of an undefined concept — fix the concept, not just the wording (M-002).
- Skill/process guidance needs to be task-level with a verification mechanism (PR DoD tie-in), not vague story-level notes (M-004).

## Future Improvements

- Once Phase 1 code lands: replace all "intent, not yet verified" notes in `.claude/context/build-process.md`, `coding-style.md`, `testing-strategy.md` with real findings.
- Populate `.claude/context/dependencies.md` with real `pyproject.toml`/`package.json` contents once they exist.
- Revisit `.claude/` for duplication/drift after the first few real PRs — this bootstrap was generated without real code to validate against.

## Completed Milestones

- 2026-07-10: `docs/` handoff package complete (SRS v3.0, ARCHITECTURE, CONFIGURATION, full backlog, design system + wireframe).
- 2026-07-11 to 12: Layout Engine architecture pivot (Gamma-style, AI-never-chooses-layout) designed, self-audited, and fully propagated across docs. Remotion runtime-integration deep-dive completed (dev-time skills vs. runtime boundary, Scene/Video composition split).
- 2026-07-12: `.claude/` AI workspace bootstrapped (agents, context, rules, workflows, prompts, templates, checklists, patterns, anti-patterns, decisions, postmortems, reviews, mistakes, memory).

## Open Questions

- No CI provider chosen yet (GitHub Actions implied by `docs/` structure but not confirmed).
- Actual `Makefile` target names, exact `pyproject.toml`/`package.json` dependency versions — all TODO until Phase 1 scaffolding.
- Remotion company license review (needed before commercialization, per SRS §12 risk table) — not yet done, no urgency until monetization is active.

## Unknown Areas

Everything about actual runtime behavior, actual performance numbers (render latency, cache hit rates), actual CI/lint configuration, and actual test coverage — none of this can be known until code exists. Do not fill these in with guessed values; mark Unknown/TODO until measured.
