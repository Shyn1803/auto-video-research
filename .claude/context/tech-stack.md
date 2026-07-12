# Context: Tech Stack

**Full detail:** `docs/SRS.md` §9 (table below is a direct summary), `docs/CONFIGURATION.md` for provider activation.

| Layer | Technology | Local-first default |
|---|---|---|
| Frontend | React, Next.js (App Router), Tailwind, shadcn/ui, Remotion Player | — |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic | — |
| Workflow orchestration | LangGraph (PostgreSQL checkpoint) | — |
| Messaging | NATS JetStream (Phase 2+) | self-host |
| Database | PostgreSQL + pgvector | self-host |
| Object storage | MinIO ↔ S3 (same adapter) | MinIO default |
| Video rendering | Remotion (check company license before commercializing) | — |
| LLM | Ollama (Qwen2.5) ↔ Gemini/Groq/OpenRouter/Mistral | local default, cloud when key present |
| Embeddings | BGE-M3 local | local default |
| TTS | edge-tts / viXTTS / F5-TTS ↔ FPT.AI / Zalo / Google | free default |
| Subtitle alignment | faster-whisper / PhoWhisper | local |
| Image generation | Stable Diffusion / FLUX.1-schnell ↔ API | local default |
| Web search | SearXNG ↔ Tavily / Brave / SerpAPI | self-host default |
| Crawling | trafilatura / crawl4ai | — |
| OCR | Marker, OpenDataLoader PDF | local |
| Scheduling | APScheduler → NATS-based (Phase 3) | — |
| Monitoring | Prometheus, Grafana, Langfuse, Sentry/GlitchTip | self-host |
| Deployment | Docker Compose → Kubernetes (Phase 3, load-driven) | — |

**Package management (per dev-guide.md, not yet verified against real files — no `pyproject.toml`/`package.json` committed yet):** Python via `uv`, linted with `ruff`, typed with `mypy --strict` on new `app/` code. TypeScript via `eslint` + `prettier`, API types generated via `openapi-typescript` (`make gen-api-client`) — never hand-written duplicates of backend schemas.

**Remotion Agent Skills (dev-time only, not runtime):** `npx skills add remotion-dev/skills` inside `packages/remotion-templates/`. Trigger table lives in `docs/dev-guide.md` §2.1 — don't duplicate it here, it drifts. Runtime LLM calls go through plain HTTP API + key and have no tool access to these skills — see [context/architecture.md](architecture.md) and `docs/specs/remotion-integration.md` §0 for the dev-time/runtime boundary.

See [dependencies.md](dependencies.md), [build-process.md](build-process.md).
