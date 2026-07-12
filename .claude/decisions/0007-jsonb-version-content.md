# ADR-0007: JSONB for Version Content

**Status:** Accepted · **Date:** design phase (docs v1.0)

## Context
Content structure at each pipeline step (outline, script, scene set) changes shape over the project's lifetime as the schema evolves — a rigid relational schema per step would require a migration for every content-shape change.

## Decision
`step_versions.content_jsonb` (and `scenes.scene_json`) store content as JSONB; structural validation happens at the Pydantic layer, not the database layer.

## Alternatives Considered
1. Fully normalized relational schema per step type — rejected: every content-shape iteration would require a migration, too slow for an actively-evolving AI-output schema.
2. Plain unstructured text/blob — rejected: loses queryability and type safety that JSONB + Pydantic together provide.

## Tradeoffs
Gain: content structure can evolve without a DB migration per change. Give up: deep queries into content fields are slower than dedicated columns — acceptable since content is read/written whole, not deeply queried.

## Consequences
Pydantic is the actual schema enforcement point — a JSONB column with no application-layer validation would silently accept malformed content. Never bypass the Pydantic model when writing to these columns.

## Future Considerations
If a specific content field needs to be queried/filtered at scale (e.g., analytics on script length), consider a generated/indexed column for that field specifically — not a wholesale move away from JSONB.
