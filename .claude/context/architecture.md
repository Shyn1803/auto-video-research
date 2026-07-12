# Context: Architecture

**Full detail:** `docs/ARCHITECTURE.md` (component diagram, event bus, data model, storage layout, deployment, 8 ADRs), `docs/specs/layout-engine.md`, `docs/specs/remotion-integration.md`.

**Shape:** modular monolith → split by measured load (ADR #1). Phase 1 = FastAPI process running everything (API, LangGraph pipeline, Scheduler); Phase 2 splits Render/Voice/Asset workers onto NATS JetStream; Phase 3 splits further only if a specific component is measurably bottlenecked.

**Pipeline (LangGraph):** `research → fact_check → write(outline→script) → storyboard → produce → render → publish`. Every node checkpoints to PostgreSQL (`langgraph-checkpoint-postgres`) — resumes at the right node after a crash. Mode 2 pauses at every node for human approval (LangGraph interrupt); Mode 1 runs straight through except the Fact Check gate.

**The one rule that shapes everything downstream — Layout Engine:** the `storyboard` node is internally layered, and **AI touches only the first layer**:

```
[AI, LLM call]      Semantic Storyboard — content + intent, NO layout
        ↓
[deterministic]     Scene Tree → Semantic Analysis → Layout Classifier (rule table)
                     → Constraint Resolver (flex presets) → Responsive Solver (9:16/16:9)
                     → Theme Engine → Motion Planner → Scene JSON (resolved)
```

Everything after the AI step is a pure function — changing format/theme/layout never calls the LLM again. This is ADR #8 in ARCHITECTURE.md. See [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md) and [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md) — this boundary has already been violated and fixed once during design (stale `layout` field in a prompt spec), so treat it as actively guarded, not assumed.

**Event bus (Phase 2+):** NATS JetStream, WorkQueue streams for render/TTS/asset/publish jobs, dedupe via `Nats-Msg-Id`, DLQ + replay from Admin UI.

**Data model:** PostgreSQL+pgvector. Central tables: `projects`, `step_versions` (JSONB content, never overwritten), `scenes` (Scene JSON + `content_hash` dirty flag), `sources`/`claims` (fact-check), `renders` (cache_key-based), `llm_usage`/`api_keys` (cost + provider tracking). Full DDL: `docs/specs/database-schema.md`.

**Deployment:** docker-compose (Phase 1-2) → optional multi-host compose or Kubernetes+KEDA (Phase 3, load-driven only).

See also: [tech-stack.md](tech-stack.md), [folder-structure.md](folder-structure.md), `.claude/decisions/` for individual ADRs.
