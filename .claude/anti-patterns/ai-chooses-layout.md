# Anti-pattern: AI Chooses Layout

**Problem:** letting an LLM output layout/position/font/camera/transition/animation fields directly. It seems convenient short-term (one prompt does everything) but makes output non-deterministic, expensive to regenerate for format/theme changes (re-burns tokens for a purely visual change), untestable (can't unit-test an LLM's layout choice), and prone to repetitive "AI slop" (same 2-3 layouts every time, no engine-level anti-repetition possible if the AI is the one deciding).

**Symptoms**
- A prompt spec or schema has a `layout` field the AI is asked to fill.
- Code path that `.get("layout")` on LLM output and uses it directly.
- Storyboard prompt instructing the AI to "vary the layout" or "choose an interesting visual arrangement."
- Old snake_case layout names (`title_card`, `full_text`, `image_full`, `image_text`, `split_compare`, `big_number`, `chart_bar`, `versus_table`, `bullet_list`, `code_snippet`) appearing anywhere — these predate the PascalCase Layout Classifier convention and signal this anti-pattern's residue.

**Impact:** breaks the entire Layout Engine cost/determinism/testability model (`docs/specs/layout-engine.md`); makes format/theme changes expensive; produces mass-produced-feeling content that risks platform reach penalties (SRS §12 risk table explicitly names this).

**Correct Solution:** see [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md). AI produces a Semantic Storyboard (`purpose`, `narration`, `components` by `kind`, plus the `beat`/`narration_anchor` signal fields) only. A deterministic Classifier/Constraint Resolver/Theme Engine/Motion Planner — code, not an LLM call — decides everything visual.

**Detection:** grep prompt specs and Pydantic schemas for `layout`, `position`, `font`, `camera`, `transition`, `animation` fields on any AI-output-facing type. A `layout` field in parsed AI output should raise a parse error, not be silently accepted.

**How to Avoid:** Reviewer agent rejects any PR where an LLM-facing schema gains one of these fields (see [rules/code-review.md](../rules/code-review.md)). Prompt Engineer agent owns keeping `docs/specs/prompts.md` free of layout-diversity instructions to the AI — that's the Classifier's post-pass job (§5.1 layout-engine.md), never the prompt's.

**Real incident:** this exact drift happened during this project's own design phase — 9 locations across docs still had snake_case layout names and one FR literally listed "Camera, Transition, Animation" as AI-decided fields, caught and fixed in a self-audit. Treat this as an actively-recurring risk, not a hypothetical.
