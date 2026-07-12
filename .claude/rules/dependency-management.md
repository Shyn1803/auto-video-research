# Rule: Dependency Management

- Every new external dependency (SDK, API, library) that represents a "capability" (LLM, TTS, search, image-gen, asset, storage, publish) must have a free/local option already in its chain, or explicit user sign-off that it's paid-only for a stated reason.
- Adding a paid-only dependency without a fallback violates SRS FR-21 rule 1 (system must run fully with 0 keys) — this is a hard constraint, not a preference.
- New provider addition follows the adapter skeleton in dev-guide.md §3 exactly: base class + `@register_{capability}("{provider}")` decorator, `available()` + capability method, unit test with HTTP mock, entry added to `docs/CONFIGURATION.md`'s provider table in the same PR.
- Library upgrades that touch the Scene JSON schema, LangGraph checkpointing, or Remotion version require checking the "đổi contract" review path before merging.
