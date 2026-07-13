# Task 1-2: Auth JWT + RBAC

**Points:** 3đ · **Epic:** 1 — Nền tảng · **Depends:** 1-1 · **FR:** NFR-4
**State file:** [`state/1-2.json`](state/1-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/1-2-auth-jwt-rbac` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a user, I want đăng nhập an toàn với vai trò admin/creator, so that dữ liệu và thao tác được bảo vệ đúng người.

## Why
Nền của mọi kiểm soát quyền. Làm sai ở đây thì audit, RBAC, publish đều mất giá trị; refresh-rotate chống chiếm phiên là yêu cầu NFR-4.

## Scope
**In:** bảng `users`, `refresh_tokens` (docs/specs/database-schema.md §2.1); argon2id; seed admin từ `ADMIN_EMAIL/PASSWORD`; endpoints `/auth/login|refresh|logout|me` (api-spec §1); refresh cookie httpOnly + rotate; dependency `require_role()`; rate limit login (slowapi); FE trang Login + AuthProvider + interceptor auto-refresh.
**Out:** CRUD user (1-7); quên mật khẩu qua email (v1.1); SSO (ngoài scope v1).

## Business Rules
1. Access 15' / refresh 7d rotate; refresh token cũ bị dùng lại → revoke **cả chuỗi** (phát hiện token bị đánh cắp) + ghi audit.
2. 5 lần sai/15' theo cặp email+IP → 429 kèm `retry_after`.
3. User `is_active=false` → 401 ngay cả khi token còn hạn (check mỗi request qua cache 60s).
4. Mật khẩu tối thiểu 10 ký tự; hash argon2id tham số chuẩn OWASP.

## Acceptance Criteria
1. **(happy)** Login đúng → access + cookie; `GET /auth/me` trả user; refresh rotate hoạt động.
2. **(biên/BR-1)** Dùng lại refresh đã rotate → 401 + cả chuỗi revoke; đăng nhập lại bình thường.
3. **(lỗi/BR-2)** Sai 5 lần → 429 + retry_after; UI hiện đếm ngược.
4. **(quyền)** Creator gọi route 🅐 → 403 error body chuẩn; admin 200.
5. **(biên/BR-3)** Khoá user đang có token sống → request kế ≤60s bị 401.

## Data & API
Bảng: `users`, `refresh_tokens`. Endpoints: api-spec §1 nguyên trạng. Events/audit: login fail vượt ngưỡng → log security; revoke chuỗi → audit record. Contract change: không.

## UI/UX
Màn Login (wireframe). States: default/loading/error(aria-live+countdown)/empty N/A/disabled N/A. A11y: Enter submit, labels, screen-reader errors.

## Decisions already locked
- ⏳ Không "remember me" v1 (refresh 7d là đủ).

## Execution Steps

Work these in order. Update `state/1-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: DB models + migration — users, refresh_tokens
- **Files:** `backend/app/models/user.py`, `backend/app/models/refresh_token.py`, `backend/alembic/versions/xxxx_create_users_refresh_tokens.py`
- **Do:** implement `User` and `RefreshToken` SQLAlchemy 2.0 models exactly per `docs/specs/database-schema.md` §2.1 (columns, indexes) — don't invent columns not in that spec.
- **Verify:** `cd backend && alembic upgrade head` → exit 0; inspect resulting schema (`psql -c '\d users'` or a migration test) matches §2.1.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/models backend/alembic && git commit -m "feat(auth): 1-2 users + refresh_tokens tables"` → `git push`

### Step 2: Password hashing + admin seed
- **Files:** `backend/app/core/security.py`, `backend/app/core/seed.py`
- **Do:** implement argon2id hashing with OWASP-recommended parameters in `security.py` (`hash_password`/`verify_password`), min-length-10 validation (BR-4); implement idempotent `seed_admin()` reading `ADMIN_EMAIL`/`ADMIN_PASSWORD` from `Settings`, creating (or leaving alone if present) the admin user.
- **Verify:** `cd backend && uv run python -m app.core.seed` → admin row exists with `is_active=true`, `role=admin`, and `verify_password` succeeds against the seeded password.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/core/security.py backend/app/core/seed.py && git commit -m "feat(auth): 1-2 argon2id hashing + admin seed"` → `git push`

### Step 3: Token service (access/refresh, rotate, reuse-detection)
- **Files:** `backend/app/services/token_service.py`, `backend/app/core/security.py`
- **Do:** issue access token (15 min exp) + refresh token (7d, stored hashed, rotated on every use); on reuse of an already-rotated refresh token, revoke the **entire token chain** and write an audit record (BR-1) — never store a refresh token in plaintext.
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_token_service.py -v` → covers rotate/reuse/expire branches.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/token_service.py backend/app/core/security.py && git commit -m "feat(auth): 1-2 token service rotate + reuse detection"` → `git push`

### Step 4: Auth endpoints + require_role + rate limiting
- **Files:** `backend/app/api/auth.py`, `backend/app/core/deps.py`, `backend/app/core/rate_limit.py`
- **Do:** implement `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` exactly per api-spec §1; set refresh token as an httpOnly cookie; add `require_role()` FastAPI dependency used on every 🅐 route; wire `slowapi` to rate-limit 5 failed attempts / 15 min per (email, IP) pair → 429 + `retry_after` (BR-2); check `is_active` on every request via a 60s cache (BR-3), returning 401 immediately when false even with a still-valid token.
- **Verify:** `curl -X POST localhost:8000/auth/login -d '{"email":...,"password":...}'` → 200 with access token + `Set-Cookie` refresh; `GET /auth/me` with the bearer token → 200 user object.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/auth.py backend/app/core/deps.py backend/app/core/rate_limit.py && git commit -m "feat(auth): 1-2 login/refresh/logout/me endpoints + RBAC + rate limit"` → `git push`

### Step 5: Frontend Login page + AuthProvider + auto-refresh interceptor
- **Files:** `frontend/src/app/(auth)/login/page.tsx`, `frontend/src/lib/auth/AuthProvider.tsx`, `frontend/src/lib/api/interceptor.ts`
- **Do:** implement the Login form per the UI/UX section above (default/loading/error states, `aria-live` error text + 429 countdown, Enter-to-submit, labeled inputs); `AuthProvider` context holding the access token in memory (not localStorage); a fetch/axios interceptor that auto-calls `/auth/refresh` once on a 401 and retries the original request.
- **Verify:** `cd frontend && npm run build` → exit 0.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src && git commit -m "feat(frontend): 1-2 Login page + AuthProvider + auto-refresh"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/test_token_service.py`, `backend/tests/integration/test_auth_flow.py`, `backend/tests/integration/test_rbac.py`, `frontend/tests/e2e/login.spec.ts`
- **Do:** one test per Acceptance Criterion — AC-1 happy login+refresh, AC-2 reuse-detection revokes the chain, AC-3 5x-wrong → 429+`retry_after` (UI countdown via Playwright), AC-4 creator on a 🅐 route → 403 vs admin → 200, AC-5 locking a user with a live token → 401 within 60s; fixture 2 users (admin/creator) shared across the suite per Test Notes; mock HTTP with `respx` where relevant, no live network calls per `rules/testing.md`.
- **Verify:** `cd backend && uv run pytest tests/ -v` → all pass; `cd frontend && npx playwright test login.spec.ts` → pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests frontend/tests && git commit -m "test(auth): 1-2 tests covering AC 1-5"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + unit đủ nhánh token service (rotate/reuse/expire) + integration login flow, no external network calls in tests.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/1-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/1-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
