# Context: Folder Structure

**Full detail:** `docs/dev-guide.md` §1. **Status: this is the planned structure — none of it has been scaffolded yet** (no `backend/`, `frontend/`, `packages/`, `render-worker/` directories exist in the repo as of this writing; only `docs/` and `.claude/`).

```
auto-video-research/
├── backend/                     # Python 3.12, FastAPI
│   ├── app/
│   │   ├── api/                 # routers by resource
│   │   ├── core/                # config (pydantic-settings), security, deps
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic DTOs + scene.py (Scene JSON contract) + migrations/
│   │   ├── services/             # business logic (state_machine.py, versioning.py...)
│   │   ├── pipeline/              # LangGraph: graph.py + nodes/
│   │   ├── adapters/              # provider adapters: llm/ tts/ search/ imagegen/ assetstock/ storage/ publish/
│   │   ├── events/                # Pydantic event schemas
│   │   └── workers/               # voice_worker.py, asset_worker.py (Phase 2)
│   ├── alembic/
│   ├── tests/                     # unit/ integration/ fixtures/
│   └── pyproject.toml             # uv + ruff + mypy
├── frontend/                     # Next.js 15 App Router, TypeScript
│   ├── src/app/                  # routes: (auth)/ projects/[id]/ admin/
│   ├── src/components/           # shadcn/ui + domain components
│   ├── src/lib/api/              # OpenAPI-generated client
│   └── src/lib/sse.ts
├── packages/remotion-templates/   # shared between frontend Player and render-worker
│   ├── src/SceneRenderer.tsx      # the ONE composition, reads preset + renders slots
│   ├── src/primitives/            # 1 component per component-kind
│   ├── src/motion/                # Animated wrapper + presets.ts
│   ├── src/theme/                 # ThemeProvider + themes/*.json
│   ├── src/presets/layouts/       # constraint preset JSON per class×format — DATA not code
│   ├── src/schema.ts              # Zod, generated from JSON Schema — never hand-written
│   └── schema/scene-1.0.0.json    # exported from Pydantic, committed
├── render-worker/                 # Node.js + Remotion CLI + NATS consumer
├── docker/                        # compose files + per-service Dockerfiles
├── docs/                          # this handoff package (exists today)
└── .env.example
```

**Key convention:** `packages/remotion-templates/` is intentionally shared source between the browser `<Player>` (preview) and the server `render-worker` (`renderMedia()`) — same code renders what you previewed. Don't fork a second template implementation for either side.

See [rules/folder-structure.md](../rules/folder-structure.md) for naming/placement rules once code exists.
