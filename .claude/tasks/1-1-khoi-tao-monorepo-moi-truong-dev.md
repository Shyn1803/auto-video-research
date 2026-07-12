# Task 1-1: Khởi tạo monorepo & môi trường dev

**Points:** 3đ · **Epic:** 1 — Nền tảng · **Depends:** — (starting task, parallel with 2-1) · **FR:** AR-1, AR-8

## User story
As a developer, I want repo scaffold + docker-compose dev chạy bằng 1 lệnh, so that cả team bắt đầu trên cùng nền từ ngày 1.

## Why
Mọi task khác build trên task này. Chuẩn hoá từ đầu (cấu trúc, lint, CI) rẻ hơn 10 lần so với retrofit.

## Scope
**In:** cấu trúc monorepo đúng [context/folder-structure.md](../context/folder-structure.md) / dev-guide §1; compose base + dev (postgres16+pgvector, minio, searxng, ollama profile `gpu`); Makefile (`up/migrate/backend/frontend/test/gen-scene-schema/gen-api-client`); FastAPI skeleton (pydantic-settings, alembic init, `/health`); Next.js + Tailwind + shadcn init; cài Remotion Agent Skills (`npx skills add remotion-dev/skills` trong `packages/remotion-templates/` — dev-guide.md §2.1); CI (ruff/eslint/mypy + test + schema-gate stub); `.env.example` đầy đủ theo `docs/CONFIGURATION.md`.
**Out:** compose prod + monitoring (9-5); seed nghiệp vụ (1-2 admin, 4-2 prompts); NATS (9-1).

## Business Rules
1. `make up` không yêu cầu GPU — profile gpu opt-in; máy không GPU stack vẫn lên đủ (trừ ollama).
2. Chỉ api/frontend expose port; postgres/minio/searxng/ollama trong network nội bộ.
3. CI chạy được trên runner không GPU/không Docker-GPU.
4. `.env.example` là nguồn tham chiếu env duy nhất — thêm env mới ở code mà thiếu trong example → CI fail (script so khớp pydantic-settings ↔ example).

## Acceptance Criteria
1. **(happy)** Máy mới có Docker+git → clone → `cp .env.example .env` → `make up && make migrate` → services healthy, `/health` 200 kèm db ok, `next dev` hiện trang login.
2. **(biên/BR-1)** Chạy máy không GPU → stack lên đủ (ollama skip), README ghi hạn chế.
3. **(lỗi)** Port 5432 bận → lỗi in hướng dẫn đổi `POSTGRES_PORT` (không stack trace trần).
4. **(CI/BR-4)** PR đầu: lint+test pass; thêm 1 setting vào code thiếu example → CI fail đúng thông điệp.

## Data & API
Bảng: chưa (alembic init rỗng). Endpoint: `GET /health` → `{status, version, db: ok}`. Contract change: khởi tạo — file OpenAPI đầu tiên.

## Decisions already locked
- ⏳ Python 3.12 + uv, Node 20 LTS (BA proposal per dev-guide, affects base image) — apply as default unless overridden.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + smoke script `make verify-dev` (up → health → down) green in CI.
