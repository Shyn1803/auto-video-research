# Rule: Type Safety

- Scene JSON has exactly one schema source: `app/schemas/scene.py` (Pydantic) → exported JSON Schema → Zod (`packages/remotion-templates/src/schema.ts`). Never hand-edit the generated Zod file; run `make gen-scene-schema`.
- API request/response types on the frontend are generated from OpenAPI (`make gen-api-client`) — a hand-written duplicate type is a bug waiting to drift.
- mypy strict for all new backend code under `app/`.
- Any LLM output that gets parsed into a typed model must fail loudly (not silently coerce) if it contains a field outside the Semantic Storyboard schema — a stray `layout`/`position`/`animation` field is a parse failure by design (glossary.md rule 3), not something to `.get()` around.
- Event payloads (NATS, Phase 2+) are Pydantic schemas with `schema_version` — same semver discipline as Scene JSON.
