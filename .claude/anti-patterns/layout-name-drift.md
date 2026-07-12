# Anti-pattern: Layout Name Drift

**Problem:** layout class names get referenced inconsistently across code/docs/UI — snake_case in one place, PascalCase in another, or an entirely different synonym — silently breaking the Classifier's mapping table and any code that string-matches a class name.

**Symptoms**
- A layout name doesn't match one of the 11 canonical PascalCase classes exactly: `Hero, TextFocus, MediaFull, MediaText, Comparison, BigNumber, Chart, VersusTable, List, Quote, Code`.
- A new doc/component introduces a synonym for an existing class instead of using the canonical name from `docs/glossary.md`.
- UI displays a class name that doesn't map cleanly back to the Classifier's output enum.

**Impact:** layout preset lookups fail or silently no-op; the anti-repetition post-pass (§5.1 layout-engine.md) can't correctly count "same class" if names don't match exactly; docs/code disagree, confusing every future contributor.

**Correct Solution:** the 11 names are fixed and canonical in `docs/glossary.md` and `docs/specs/scene-json-schema.md`. Any new layout class proposal goes through Architect + Documentation Engineer review before use, added to the glossary first.

**Detection:** grep for the 10 known-retired snake_case names (`title_card`, `full_text`, `image_full`, `image_text`, `split_compare`, `big_number`, `chart_bar`, `versus_table`, `bullet_list`, `code_snippet`) — any hit is drift.

**How to Avoid:** a single shared TypeScript/Python enum generated from one source (the schema), never a hand-typed string literal for a layout class name in application code.

**Real incident:** exactly this drift was found and fixed across 9 locations in this project's docs during a self-audit — see [postmortems/2026-07-pascalcase-layout-drift.md](../postmortems/2026-07-pascalcase-layout-drift.md).
