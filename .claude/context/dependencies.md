# Context: Dependencies

**Status: Unknown / TODO.** No `pyproject.toml`, `package.json`, or lockfile exists in the repo yet — there is nothing to enumerate. This file should be populated with real dependency lists once Phase 1 scaffolding (story 1.1) lands.

**What we know from `docs/` (intent, not yet pinned versions):**
- Backend: FastAPI, SQLAlchemy 2.0, Pydantic v2 (implied by "Pydantic model"), Alembic, LangGraph + `langgraph-checkpoint-postgres`, `respx` (test HTTP mocking).
- Frontend: Next.js 15, Tailwind CSS, shadcn/ui, `@remotion/player`, React Query (server state).
- render-worker: Node.js, Remotion CLI (`@remotion/renderer` family — `bundle`, `selectComposition`, `renderMedia`), NATS client.
- Shared: `packages/remotion-templates` — Zod (schema validation, generated not hand-written).
- Infra: PostgreSQL+pgvector, MinIO, NATS JetStream, Ollama, SearXNG, Prometheus/Grafana, Langfuse, Sentry/GlitchTip — all self-hostable, all free.

**External API dependencies (all env-activated, all optional per CONFIGURATION.md):** Gemini, Groq, OpenRouter, Mistral (LLM); FPT.AI, Zalo, Google Cloud TTS (paid TTS); Tavily, Brave, SerpAPI (paid search); Pexels/Pixabay/Unsplash (free-tier assets); YouTube/TikTok/Facebook/LinkedIn (publish).

**Rule:** no dependency is added to satisfy a paid-only path without a free/local alternative already wired into the same chain (see [rules/dependency-management.md](../rules/dependency-management.md)).

Update this file with real `pyproject.toml`/`package.json` contents once they exist — don't let it stay aspirational.
