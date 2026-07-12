# Context: Coding Style

**Full detail:** `docs/dev-guide.md` §4. **Status: intent, not yet verified against real code — no source files exist yet.** Update this file with actual findings (real lint config, actual patterns that emerged) once Phase 1 week 1-2 code lands; don't let it stay theoretical.

**Python (backend):**
- ruff for lint + format; mypy strict for new `app/` code.
- async by default.
- SQLAlchemy 2.0 style — `select()`, never the legacy `.query()` API.
- No business logic in routers — routers call services, services contain logic.

**TypeScript (frontend + render-worker + packages/remotion-templates):**
- eslint + prettier.
- API types generated from OpenAPI (`make gen-api-client`) — never hand-write an interface that duplicates a backend Pydantic schema.
- shadcn/ui components keep shadcn's own convention (don't restyle the primitive, compose around it).

**Cross-cutting:**
- Adapter pattern for every external capability — see [patterns/provider-adapter.md](../patterns/provider-adapter.md). An adapter never reads env directly (receives `ProviderSettings`) and never logs usage (router's job).
- Scene JSON schema is single-sourced: edit `app/schemas/scene.py` → `make gen-scene-schema` regenerates JSON Schema + Zod. CI should fail if this is forgotten (once CI exists).
- Story ID referenced in commit subject: `feat(scene): S1.3-04 validate layout constraints`.

See [rules/code-style.md](../rules/code-style.md), [rules/type-safety.md](../rules/type-safety.md) for enforceable rules derived from this.
