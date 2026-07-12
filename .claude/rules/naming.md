# Rule: Naming

- Domain terms in code must match `docs/glossary.md` exactly, in English (the "code" column) — the Vietnamese column is UI-display only, never an identifier.
- Layout class names are PascalCase canonical: `Hero, TextFocus, MediaFull, MediaText, Comparison, BigNumber, Chart, VersusTable, List, Quote, Code`. Never reintroduce the old snake_case names (`title_card`, `full_text`, `image_full`, `image_text`, `split_compare`, `big_number`, `chart_bar`, `versus_table`, `bullet_list`, `code_snippet`) — this drift already happened once and was fixed across 9 locations (see [postmortems/2026-07-pascalcase-layout-drift.md](../postmortems/2026-07-pascalcase-layout-drift.md)).
- Component-kinds (Semantic Storyboard) are snake_case: `heading, body, media_intent, stat, bullet, chart_data, table_data, quote, code, group`.
- Env vars: `SCREAMING_SNAKE_CASE`, capability chains suffixed `_CHAIN` (`LLM_CHAIN_CHEAP`, `TTS_CHAIN`...).
- Story IDs in commits/branches: `feat/{story-id}-mo-ta`, e.g. `feat(scene): S1.3-04 validate layout constraints`.
- Provider adapter files: one file per provider under `app/adapters/{capability}/{provider}.py`, class `{Provider}{Capability}` e.g. `FptTTS`.
- Database tables/columns: snake_case, matches `docs/specs/database-schema.md` exactly — don't invent a synonym for an existing column.
