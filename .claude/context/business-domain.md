# Context: Business Domain

**Full detail:** `docs/glossary.md` (authoritative — code identifiers must match this table exactly; UI shows the Vietnamese column).

**Core domain objects:** `project` (a video from topic→publish, owns versioning/state) → has `step_version`s per `step` (research, outline, script, storyboard, scene_set, produce, render, publish) → a storyboard version owns a `scene_set` → each `scene` is independently previewed/cached/rendered, identified by immutable `scene_id`.

**Fact-checking is quantitative, not vibes-based:** each `claim` gets a `verdict` — `PASS` (≥2 independent trusted sources), `WARN` (1 source / untrusted domain / from `partial_content`), `FAIL` (≥2 contradicting sources → project → `NEED_REVIEW`). Project-level verdict = worst of its claims (FAIL > WARN > PASS).

**Layout vocabulary (the part most likely to be gotten wrong — see [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md)):**
- `semantic storyboard` / `scene tree` — AI's output: content + intent only (`purpose`, `components` by `kind`). No layout, position, font, or animation.
- `layout class` — one of 11 PascalCase classes (Hero, TextFocus, MediaFull, MediaText, Comparison, BigNumber, Chart, VersusTable, List, Quote, Code), **chosen by the Layout Classifier, never the AI.**
- `classifier` — deterministic rule table mapping a semantic profile → layout class.
- `constraint preset` — a class's layout defined as flex data (slots/gap/padding), not pixel coordinates.
- `layout_override` — user manually picks a different class than the classifier chose; sticky across regenerate-same-content, reset on content-nature change.
- `motion preset` — animation keyed by component-kind × theme, not per-element config.

**Project lifecycle state machine** (`docs/SRS.md` FR-17): `DRAFT → RESEARCHING → NEED_REVIEW ⇄ REVISING → APPROVED → PRODUCING → RENDERING → READY → PUBLISHING → PUBLISHED`, any state → `FAILED` (resumable), any terminal state → `ARCHIVED`.

**Domain rules that get violated if you don't know them** (glossary.md, verbatim — memorize these):
1. Never overwrite a version — every edit is a new version; restore creates new state, doesn't delete.
2. `scene_id` is immutable — reordering only changes `scene_number`.
3. AI never produces Scene JSON or chooses layout — a `layout` field in AI output is a parse failure.
4. Render Worker never fetches an external URL — only resolved, licensed MinIO assets.
5. Adapters don't read env or log usage — that's config layer / router's job.
6. A FAIL verdict doesn't block forever — human override is allowed, with reason + audit.

See also: [glossary.md](glossary.md) (pointer), [architecture.md](architecture.md).
