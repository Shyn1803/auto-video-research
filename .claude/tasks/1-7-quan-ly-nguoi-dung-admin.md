# Task 1-7: Quản lý người dùng (Admin)

**Points:** 2đ · **Epic:** 1 — Nền tảng · **Depends:** 1-2 · **FR:** Personas §3
**State file:** [`state/1-7.json`](state/1-7.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/1-7-user-management-admin` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As an Admin, I want tạo/khoá/đổi vai trò người dùng, so that kiểm soát được ai dùng hệ thống và với quyền gì.

## Why
Persona Admin (SRS §3) có quyền "Quản lý người dùng" nhưng backlog gốc bỏ sót — gap phát hiện khi rà luồng. Không có task này thì thêm thành viên thứ 3 phải sửa DB tay.

## Scope
**In:** CRUD users 🅐 (api-spec §1); tab Quản trị › Người dùng (list, tạo với mật khẩu tạm, đổi role, khoá/mở); audit thao tác; revoke phiên khi khoá (nối 1-2 BR-3).
**Out:** self-service đổi/quên mật khẩu (v1.1); mời qua email (v1.1); nhóm/workspace (ngoài scope v1).

## Business Rules
1. Không tự khoá/hạ quyền chính mình.
2. Khoá user → mọi refresh token revoke ngay.
3. Luôn còn ≥1 admin active — thao tác vi phạm → 409 kèm giải thích.
4. Mật khẩu tạm buộc đổi ở lần đăng nhập đầu (cờ `must_change_password`).

## Acceptance Criteria
1. **(happy)** Tạo creator + mật khẩu tạm → đăng nhập được → bị buộc đổi mật khẩu → vào bình thường.
2. **(biên/BR-2)** Khoá user đang đăng nhập → request kế ≤60s 401.
3. **(lỗi/BR-3)** Khoá admin cuối → 409 giải thích rõ.
4. **(quyền)** Creator không thấy tab; API → 403.
5. **(BR-1)** Nút khoá/đổi role trên dòng chính mình disabled + tooltip.

## Data & API
Bảng: `users` (+cột `must_change_password`); audit vào bảng chung. Contract change: **có** — thêm `must_change_password` flow vào `/auth/login` response → cập nhật api-spec §1.

## UI/UX
Wireframe Quản trị › Người dùng. States: default/loading(skeleton)/empty(hướng dẫn thêm)/error/disabled(BR-1+tooltip). A11y: bảng caption, select role label, confirm dialog.

## Decisions already locked
- ⏳ V1 không email mời — admin đưa mật khẩu tạm trực tiếp (đội nhỏ nội bộ).

## Execution Steps

Work these in order. Update `state/1-7.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: users table extension (must_change_password) + migration
- **Files:** `backend/app/models/user.py`, `backend/alembic/versions/xxxx_users_must_change_password.py`
- **Do:** add `must_change_password: bool` column to the existing `User` model (from task 1-2) per Data & API section (BR-4).
- **Verify:** `cd backend && alembic upgrade head` → exit 0.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/models/user.py backend/alembic && git commit -m "feat(users): 1-7 add must_change_password column"` → `git push`

### Step 2: Admin user CRUD service + last-admin/self-lock guards
- **Files:** `backend/app/services/user_admin_service.py`, `backend/app/api/users.py`
- **Do:** implement admin-only CRUD (create with temp password, list, update role, lock/unlock) per api-spec §1 🅐 routes; enforce BR-1 (cannot lock/demote self — service rejects, not just UI), BR-3 (reject an operation that would leave 0 active admins → 409 with an explanatory message); on lock, immediately revoke all of that user's refresh tokens (BR-2, reuses 1-2's token_service revocation) and write an audit record.
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_user_admin_service.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/user_admin_service.py backend/app/api/users.py && git commit -m "feat(users): 1-7 admin CRUD service + last-admin/self-lock guards"` → `git push`

### Step 3: must_change_password login flow (contract change)
- **Files:** `backend/app/api/auth.py`, `docs/specs/api-spec.md` §1
- **Do:** extend `POST /auth/login` response to include `must_change_password` (BR-4); add a change-password endpoint/flow that clears the flag on success; update `docs/specs/api-spec.md` §1 in this same change per `rules/documentation.md` (contract change, same PR).
- **Verify:** `curl` login with a temp-password user → response includes `must_change_password: true`; change password → subsequent login has it `false`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/auth.py docs/specs/api-spec.md && git commit -m "feat(auth): 1-7 must_change_password login flow (contract change: api-spec §1)"` → `git push`

### Step 4: Admin › Users UI tab
- **Files:** `frontend/src/app/admin/users/page.tsx`, `frontend/src/components/admin/UserTable.tsx`
- **Do:** implement the wireframe per UI/UX section — list, create-with-temp-password dialog, role select, lock/unlock; 5 states (default/loading-skeleton/empty-with-guidance/error/disabled); self-row lock/role controls disabled with a tooltip explaining why (BR-1); a11y: table caption, labeled role select, confirm dialog before lock.
- **Verify:** `cd frontend && npm run build` → exit 0.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/app/admin/users frontend/src/components/admin && git commit -m "feat(frontend): 1-7 Admin Users tab UI"` → `git push`

### Step 5: Wire up tests covering all Acceptance Criteria
- **Files:** `backend/tests/integration/test_user_admin.py`, `frontend/tests/e2e/admin-users.spec.ts`
- **Do:** fixture with 2 users (admin+creator) plus a dedicated single-admin fixture for BR-3; one test per Acceptance Criterion — AC-1 create+temp-password+forced-change happy path, AC-2 lock a logged-in user → next request ≤60s → 401, AC-3 lock the last admin → 409 with explanation, AC-4 creator can't see the tab / API → 403, AC-5 self-row lock/role controls disabled+tooltip; Playwright scenario "khoá → session kia văng" (lock in one session, other session's next request gets 401).
- **Verify:** `cd backend && uv run pytest tests/ -v` → all pass; `cd frontend && npx playwright test admin-users.spec.ts` → pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests frontend/tests && git commit -m "test(users): 1-7 tests covering AC 1-5"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture 2 user + case 1-admin-duy-nhất; Playwright khoá → session kia văng.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/1-7.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/1-7.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
