# Task 1-1: Khởi tạo monorepo & môi trường dev

**Points:** 3đ · **Epic:** 1 — Nền tảng · **Depends:** — (starting task, parallel with 2-1) · **FR:** AR-1, AR-8
**State file:** [`state/1-1.json`](state/1-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/1-1-khoi-tao-monorepo` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

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

## Execution Steps

Work these in order. Update `state/1-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Scaffold monorepo directory structure
- **Files:** `backend/app/{api,core,models,schemas,services,pipeline/nodes,adapters/{llm,tts,search,imagegen,assetstock,storage,publish},events,workers}/`, `frontend/src/`, `packages/remotion-templates/`, `render-worker/`, `docker/`
- **Do:** create the directory skeleton exactly per [context/folder-structure.md](../context/folder-structure.md) / dev-guide §1; add `.gitkeep` (or minimal `__init__.py`) placeholders for currently-empty dirs so the structure is committed even before other tasks populate it.
- **Verify:** `ls backend/app frontend/src packages/remotion-templates render-worker docker` → all directories exist, no "No such file" errors.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend frontend packages render-worker docker && git commit -m "chore(repo): 1-1 scaffold monorepo directory structure"` → `git push`

### Step 2: Backend FastAPI skeleton
- **Files:** `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/api/health.py`, `backend/alembic/`
- **Do:** `uv init` in `backend/` with ruff+mypy+pytest+fastapi+pydantic-settings deps; implement `Settings(BaseSettings)` in `backend/app/core/config.py` reading env; implement `GET /health` in `backend/app/api/health.py` returning `{status, version, db: ok}` exactly per the Data & API section above; run `alembic init alembic` inside `backend/`, wire `alembic.ini`/`env.py` to `Settings.DATABASE_URL`.
- **Verify:** `cd backend && uv run uvicorn app.main:app --port 8000 &` then `curl localhost:8000/health` → HTTP 200 JSON with `status`, `version`, `db` keys.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend && git commit -m "feat(backend): 1-1 FastAPI skeleton + /health endpoint"` → `git push`

### Step 3: Next.js + Tailwind + shadcn init
- **Files:** `frontend/package.json`, `frontend/tailwind.config.ts`, `frontend/src/app/(auth)/login/page.tsx`
- **Do:** `npx create-next-app@latest frontend --typescript --tailwind --app`; `npx shadcn@latest init`; add a placeholder Login route under `src/app/(auth)/` matching the folder-structure.md route convention (real Login UI lands in 1-2).
- **Verify:** `cd frontend && npm run build` → exit 0.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend && git commit -m "feat(frontend): 1-1 Next.js + Tailwind + shadcn scaffold"` → `git push`

### Step 4: Docker compose base + dev, Makefile
- **Files:** `docker/docker-compose.base.yml`, `docker/docker-compose.dev.yml`, `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`, `Makefile`
- **Do:** compose services postgres16+pgvector, minio, searxng, ollama (profile `gpu`, opt-in per BR-1); only `api`/`frontend` expose host ports, everything else stays on the internal network (BR-2); Makefile targets `up/migrate/backend/frontend/test/gen-scene-schema/gen-api-client` (the schema/client-gen targets can be thin stubs with a `# TODO: implemented by 2-1 / gen-api-client tooling` comment — don't fabricate the underlying generators here).
- **Verify:** `make up` → `docker compose ps` shows all base services healthy/running; running `make up` without `--profile gpu` still brings up api/frontend/postgres/minio/searxng (BR-1, AC-2).
- **On failure:** if this fails because port 5432 is already bound, that's expected input for Step 6 (error messaging), not a step failure — otherwise apply the standard retry policy.
- **Commit:** `git add docker Makefile && git commit -m "feat(infra): 1-1 docker-compose dev stack + Makefile"` → `git push`

### Step 5: Remotion Agent Skills install
- **Files:** `packages/remotion-templates/package.json`, `packages/remotion-templates/` (skills output)
- **Do:** `cd packages/remotion-templates && npx skills add remotion-dev/skills` per `docs/specs/remotion-integration.md` §1 — this is required groundwork for every later Remotion task (2.x).
- **Verify:** skills directory/files present under `packages/remotion-templates` after the install; `package.json` is valid JSON (`node -e "require('./package.json')"` exits 0).
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates && git commit -m "chore(remotion): 1-1 install Remotion Agent Skills"` → `git push`

### Step 6: CI pipeline + .env.example + env-sync gate (BR-4)
- **Files:** `.github/workflows/ci.yml`, `.env.example`, `scripts/check_env_sync.py`
- **Do:** CI job running ruff+mypy (backend), eslint (frontend), pytest, and a schema-gate stub step (real gate lands with 2-1); write `.env.example` as a complete superset of every variable in `docs/CONFIGURATION.md`; write `scripts/check_env_sync.py` that diffs `Settings` fields against `.env.example` keys and fails non-zero with a clear message on mismatch (BR-4); also make the Postgres-port-in-use case (AC-3) surface a friendly "change POSTGRES_PORT in .env" message instead of a raw stack trace — wire this into the `make up`/`make migrate` wrapper.
- **Verify:** locally run `ruff check backend && cd frontend && npm run lint && cd ../backend && uv run mypy app && uv run pytest`; then add one setting to `Settings` without adding it to `.env.example` and confirm `python scripts/check_env_sync.py` exits non-zero with the mismatch named (AC-4) — then revert the deliberate break.
- **On failure:** same policy as Step 1.
- **Commit:** `git add .github .env.example scripts && git commit -m "chore(ci): 1-1 CI pipeline + .env.example + env-sync gate"` → `git push`

### Step 7: make verify-dev smoke script + README GPU note
- **Files:** `Makefile` (`verify-dev` target), `README.md`
- **Do:** implement `make verify-dev` = up → wait-for-healthy → `curl /health` → down, per Test Notes/DoD; document in `README.md` that GPU-less machines still run the full stack except `ollama` (AC-2).
- **Verify:** `make verify-dev` → exit 0, prints a health-check success line then tears the stack down.
- **On failure:** same policy as Step 1.
- **Commit:** `git add Makefile README.md && git commit -m "chore(ci): 1-1 make verify-dev smoke script + README GPU note"` → `git push`

### Step 8: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/test_health.py`, `backend/tests/integration/test_env_sync.py`
- **Do:** one test per Acceptance Criterion tagged above — AC-1 happy-path health check, AC-2 GPU-less profile note (document as a manual/CI-runner check if genuinely untestable without Docker-in-Docker, and say so explicitly rather than silently skipping), AC-3 port-conflict friendly error, AC-4 env-sync CI gate; mock HTTP with `respx` for any adapter-shaped code per `rules/testing.md` (none expected in this task).
- **Verify:** `cd backend && uv run pytest tests/ -v` → all pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests && git commit -m "test(repo): 1-1 tests covering AC 1-4"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + smoke script `make verify-dev` (up → health → down) green in CI.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/1-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/1-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
