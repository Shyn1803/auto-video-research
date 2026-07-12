# Developer Guide — Repo Structure & Conventions

**Version:** 1.0 · Đọc trước khi viết dòng code đầu tiên.

---

# 1. Cấu trúc Monorepo

```
auto-video-research/
├── backend/                     # Python 3.12, FastAPI
│   ├── app/
│   │   ├── api/                 # routers theo resource (projects.py, scenes.py, admin/…)
│   │   ├── core/                # config (pydantic-settings), security, deps
│   │   ├── models/              # SQLAlchemy models (1 file / nhóm bảng)
│   │   ├── schemas/             # Pydantic: API DTO + scene.py (Scene JSON) + migrations/
│   │   ├── services/            # business logic (state_machine.py, versioning.py, …)
│   │   ├── pipeline/            # LangGraph: graph.py + nodes/ (research.py, factcheck.py, …)
│   │   ├── adapters/            # ⭐ provider adapters (xem §3)
│   │   │   ├── llm/  tts/  search/  imagegen/  assetstock/  storage/  publish/
│   │   ├── events/              # Pydantic event schemas (event-catalog.md)
│   │   └── workers/             # entrypoint voice_worker.py, asset_worker.py (Phase 2)
│   ├── alembic/                 # migrations
│   ├── tests/                   # unit/ integration/ fixtures/
│   └── pyproject.toml           # uv + ruff + mypy
├── frontend/                    # Next.js 15 (App Router), TypeScript
│   ├── src/app/                 # routes: (auth)/ projects/[id]/ admin/
│   ├── src/components/          # shadcn/ui + domain components
│   ├── src/lib/api/             # client sinh từ OpenAPI (openapi-typescript)
│   └── src/lib/sse.ts
├── packages/
│   └── remotion-templates/      # ⭐ share giữa frontend (Player) và render-worker
│       ├── src/SceneRenderer.tsx    # composition DUY NHẤT — đọc preset, render slots (layout-engine.md §11)
│       ├── src/primitives/          # 1 component / component-kind (Heading, Media, Stat, ChartBar…)
│       ├── src/motion/              # Animated wrapper + presets.ts (bảng kind×theme)
│       ├── src/theme/               # ThemeProvider + themes/*.json
│       ├── src/presets/layouts/     # constraint preset json mỗi class×format — DATA, không code
│       ├── src/schema.ts            # Zod — sinh từ JSON Schema, KHÔNG viết tay
│       └── schema/scene-1.0.0.json  # export từ Pydantic, commit vào repo
├── render-worker/               # Node.js + Remotion CLI + NATS consumer
├── docker/                      # compose files + Dockerfile từng service
│   ├── docker-compose.yml       # base (postgres, minio, ollama, searxng)
│   ├── docker-compose.dev.yml   # hot-reload
│   └── docker-compose.prod.yml  # + nats, workers, monitoring
├── docs/                        # bộ tài liệu này
├── Makefile
└── .env.example                 # copy đầy đủ từ CONFIGURATION.md
```

# 2. Chạy môi trường dev

```bash
cp .env.example .env             # mặc định = chạy 0 API key (local-first)
make up                          # docker compose: postgres, minio, ollama, searxng
make migrate                     # alembic upgrade head + seed (admin, prompts, trusted domains)
make ollama-pull                 # tải qwen2.5:14b-instruct (1 lần)
make backend                     # uvicorn --reload  → http://localhost:8000/docs
make frontend                    # next dev          → http://localhost:3000
make test                        # pytest + vitest
npx skills add remotion-dev/skills   # trong packages/remotion-templates/ — Remotion Agent Skills, xem specs/remotion-integration.md §1
```

## 2.1 Remotion Agent Skills — cơ chế thật & quy ước invoke

**Phạm vi: chỉ dev-time (lúc viết code), không liên quan runtime.** Pipeline chạy thật gọi LLM qua HTTP API + key thuần (FR-18/21) — không có tool access, không đọc được `SKILL.md` dù cấu hình thế nào. Chi tiết ranh giới: [remotion-integration.md](specs/remotion-integration.md) §0.

**Cơ chế:** các skill này là file `SKILL.md` thuần (frontmatter `name`/`description` + nội dung) — không có API, không tự động chạy. Coding agent (Claude Code) tự đọc `description`, so với việc đang làm, nạp nội dung vào context nếu khớp **trước khi viết code**. Đây là quy ước cho *phiên code tương tác*, không phải bước CI — không thể ép một pipeline tự động "gọi skill".

**Bảng trigger — mức task, không phải mức story** (dùng làm checklist khi bắt tay code):

| Trước khi viết… | Invoke skill |
|---|---|
| Composition/primitive/preset mới (`SceneRenderer`, `primitives/*`, `presets/layouts/*`) | `/remotion-markup` |
| Thuật toán/component subtitle | `/remotion-captions` (kiểm tra `@remotion/captions` trước khi tự viết) |
| Render worker (`bundle/selectComposition/renderMedia`, queue, retry) | `/remotion-saas` + `/remotion-render` |
| Tích hợp `<Player>` / làm SceneForm editable | `/remotion-interactivity` |
| Scaffold package/composition mới lần đầu | `/remotion-create` |
| Không chắc cần skill nào | `/remotion-best-practices` (bao toàn bộ) |

**Definition of Done bổ sung cho story chạm `packages/remotion-templates/` hoặc `render-worker/`:** PR description ghi rõ skill nào đã invoke cho phần nào — reviewer kiểm bằng cách đối chiếu code có theo đúng pattern skill hướng dẫn không (ví dụ: dùng `calculateMetadata` thay vì tự tính duration tay — dấu hiệu skill được dùng thật, không phải ghi cho có).

Không có GPU: đặt `OLLAMA_MODEL_CHEAP=qwen2.5:7b-instruct` hoặc cấu hình `GEMINI_API_KEY` để dev nhanh hơn. Mọi test unit phải chạy được **không cần** Ollama/GPU (dùng mock — xem test-plan).

# 3. Pattern Adapter — quy trình thêm provider (việc lặp lại nhiều nhất)

Mỗi capability có 1 abstract base + registry. Ví dụ thêm TTS provider mới:

```python
# app/adapters/tts/base.py  (đã có sẵn)
class TTSAdapter(ABC):
    name: str
    is_paid: bool = False
    @abstractmethod
    async def available(self) -> bool: ...        # key tồn tại / service reachable
    @abstractmethod
    async def synthesize(self, req: TTSRequest) -> TTSResult: ...  # raise ProviderError

# app/adapters/tts/fpt.py  (file mới — chỉ cần thế này)
@register_tts("fpt")
class FptTTS(TTSAdapter):
    name, is_paid = "fpt", True
    async def available(self): return bool(await get_key("fpt"))
    async def synthesize(self, req): ...
```

Quy tắc bắt buộc:
1. Adapter **không đọc env trực tiếp** — nhận config qua `ProviderSettings` (core/config).
2. Mọi exception ngoài → wrap thành `ProviderError(retryable: bool)`; router quyết định failover.
3. Ghi usage (`llm_usage` cho LLM; counter cho key) trong router, **không** trong adapter.
4. Kèm unit test: `available()` các trường hợp, `synthesize` với HTTP mock (respx).
5. Thêm tên vào bảng provider trong [CONFIGURATION.md](CONFIGURATION.md) — doc là một phần của PR.

# 4. Conventions

**Python:** ruff (lint+format), mypy strict cho `app/` mới; async mặc định; SQLAlchemy 2.0 style (select(), không query()); không business logic trong router — router gọi service.

**TypeScript:** eslint + prettier; API types sinh từ OpenAPI (`make gen-api-client`) — không viết tay interface trùng backend; component shadcn giữ nguyên convention của shadcn.

**Scene schema:** sửa `app/schemas/scene.py` → chạy `make gen-scene-schema` (export JSON Schema + regenerate Zod). CI fail nếu quên.

**Git:** trunk-based; branch `feat/{story-id}-mo-ta`, `fix/…`; Conventional Commits (`feat:`, `fix:`, `docs:`…); PR bắt buộc: CI xanh + 1 review + cập nhật docs nếu đổi contract (API/schema/event/env).

**ID story trong commit:** `feat(scene): S1.3-04 validate layout constraints`.

# 5. Định nghĩa "đổi contract" (cần cẩn trọng + review kỹ)

Bất kỳ thay đổi nào tại: `app/schemas/scene.py`, `app/events/`, API request/response schema, bảng DB, biến env. Các thay đổi này yêu cầu: semver bump nếu breaking, migration nếu DB/scene, cập nhật doc specs tương ứng, thông báo trong PR description mục **Contract changes**.

# 6. Debug nhanh

| Vấn đề | Xem ở đâu |
|---|---|
| Pipeline đứng ở node nào | bảng `langgraph_checkpoints` / GET `/projects/{id}/runs/{run_id}` |
| LLM trả gì, prompt version nào | Langfuse (nếu bật) hoặc `llm_usage` + log level DEBUG |
| Provider nào đang active | GET `/admin/providers` |
| Render fail | bảng `renders.error` + log render-worker + giữ lại props JSON trong `renders/` debug folder |
| Event kẹt | `nats stream info` / GET `/admin/queue` — check DLQ |
