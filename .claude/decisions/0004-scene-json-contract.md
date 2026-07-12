# ADR-0004: Scene JSON + schema_version as Central Contract

**Status:** Accepted · **Date:** design phase (docs v1.0)

## Context
Preview, render, caching, and versioning all need a single stable data shape to key off — without one, preview and render risk drifting apart, and cache invalidation becomes guesswork.

## Decision
Scene JSON, defined once in Pydantic (`app/schemas/scene.py`), exported to JSON Schema, consumed as Zod on the frontend/Remotion side — one source, two generated targets. Every Scene JSON carries `schema_version` (semver); breaking changes bump major + ship a migration script.

## Alternatives Considered
1. Separate frontend/backend schemas kept manually in sync — rejected: guaranteed drift over time.
2. No explicit versioning, just "latest shape" — rejected: breaks the ability to render old projects or migrate incrementally.

## Tradeoffs
Gain: preview/render/cache/versioning all consistent by construction. Give up: schema design investment must happen early and changes require the full "đổi contract" review discipline.

## Consequences
Any schema edit requires `make gen-scene-schema` + review of every consumer (Player, render-worker, editor forms) for compatibility.

## Future Considerations
Schema v2+ roadmap already anticipates: chart line/pie, embedded video, lower-third, Gallery/Timeline layout classes, karaoke subtitles, general constraint solver — planned additive/major-version changes, not surprises.
