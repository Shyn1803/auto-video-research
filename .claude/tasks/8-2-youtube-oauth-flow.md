# Task 8-2: YouTube OAuth flow

**Points:** 5đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-1, 3-4 · **FR:** FR-12, FR-21
**State file:** [`state/8-2.json`](state/8-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/8-2-youtube-oauth-flow` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As an Admin, I want kết nối kênh YouTube qua OAuth ngay trong trang Quản trị, so that hệ thống đăng thay tôi mà tôi không phải đưa mật khẩu Google cho ai.

## Why
YouTube là nền tảng auto-publish chính của v1. Refresh token là secret nhạy cảm nhất hệ thống nắm giữ — BR bảo mật khắt khe tương ứng. See [rules/security.md](../rules/security.md).

## Scope
**In:** Google OAuth (client id/secret env — FR-21): flow connect trong Quản trị › API Keys; refresh token mã hoá (api_keys provider `youtube_oauth`); auto refresh access; revoke/reconnect; đa kênh (default + chọn khi đăng).
**Out:** app verification với Google (việc PO — checklist runbook); OAuth nền tảng khác (10-3 dùng pattern này).

## Business Rules
1. Refresh token chỉ trong DB mã hoá — không log/response/error message.
2. Refresh fail (revoked phía Google) → trạng thái "mất kết nối" + notify + hướng dẫn; hàng YouTube ở màn publish tự chuyển ⚠.
3. State param chống CSRF trong OAuth flow; redirect URI cố định từ env.
4. Ngắt kết nối → xoá token + revoke phía Google (best effort).

## Acceptance Criteria
1. **(happy)** Connect → consent → kênh hiện tên+avatar; token mã hoá trong DB.
2. **(biên/BR-2)** Giả lập 401 refresh → "mất kết nối" + notify; reconnect phục hồi.
3. **(bảo mật/BR-1,3)** Grep log/response không token; callback sai state → 403.
4. **(đa kênh)** 2 kênh → đăng chọn đúng kênh; default hoạt động.
5. **(BR-4)** Ngắt kết nối → token xoá; đăng YouTube → trạng thái "chưa cấu hình".

## Data & API
Bảng: api_keys (provider youtube_oauth, key_encrypted = refresh token). Endpoints: `GET /admin/oauth/youtube/start`, `GET /admin/oauth/youtube/callback` (mới) → cập nhật api-spec §9. Contract change: **có**.

## Decisions already locked
- Privacy video mặc định **unlisted**; đổi qua config.

## Execution Steps

Work these in order. Update `state/8-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit. **Security note (rules/security.md governs every step here):** the refresh token is the most sensitive secret this system holds — never let it reach a log line, an HTTP response body, or an error message at any point in this task, and every admin action taken (connect/reconnect/revoke) must be audit-logged, no silent admin mutation.

### Step 1: OAuth client config + CSRF state param plumbing
- **Files:** `backend/app/adapters/publish/youtube_oauth.py` (or `backend/app/services/oauth/youtube.py` per folder-structure conventions), config additions to `ProviderSettings`
- **Do:** read Google OAuth client id/secret from env only via `ProviderSettings` (never `os.environ` directly, per `rules/code-style.md`); redirect URI fixed from env (BR-3); generate + validate a signed `state` param for CSRF protection on every start/callback round-trip (BR-3).
- **Verify:** `mypy backend/app/adapters/publish/youtube_oauth.py --strict` → 0 errors.
- **On failure:** transient (env/tooling) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/adapters/publish/youtube_oauth.py && git commit -m "feat(publish): 8-2 add YouTube OAuth client config + CSRF state"` → `git push`

### Step 2: `/admin/oauth/youtube/start` + `/admin/oauth/youtube/callback` endpoints
- **Files:** `backend/app/api/routes/admin_oauth.py`, router registration, `docs/specs/api-spec.md` §9 update (đổi contract — same PR per `rules/documentation.md`)
- **Do:** `start` redirects to Google consent screen with the signed state param; `callback` validates `state` (mismatch → 403, per AC3), exchanges code for tokens, encrypts the refresh token with Fernet (master key from env, per `rules/security.md`) and stores it in `api_keys` (provider `youtube_oauth`), fetches channel name+avatar for display. Update `docs/CONFIGURATION.md`/api-spec in the same commit — this is a contract change.
- **Verify:** `pytest backend/tests/integration/api/test_admin_oauth.py -q -k "callback_bad_state"` → 403 test passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/routes/admin_oauth.py docs/specs/api-spec.md && git commit -m "feat(publish): 8-2 add OAuth start/callback endpoints"` → `git push`

### Step 3: Encrypted token storage + auto-refresh
- **Files:** `backend/app/services/oauth_token_service.py`
- **Do:** encrypt-at-rest via Fernet (never plaintext, never logged — grep-able by Step 6); auto-refresh access token using the stored refresh token; on refresh failure (401/revoked), set channel status to "mất kết nối", emit a notify event, and surface guidance (BR-2) — no raw provider error text leaks the token.
- **Verify:** `mypy backend/app/services/oauth_token_service.py --strict` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/oauth_token_service.py && git commit -m "feat(publish): 8-2 add encrypted token storage + auto-refresh"` → `git push`

### Step 4: Multi-channel support (default + per-publish selection)
- **Files:** `backend/app/services/oauth_token_service.py`, `backend/app/schemas/publish.py`
- **Do:** support connecting 2+ channels, one marked default; publish flow lets the caller pick a channel, defaulting when unspecified (AC4).
- **Verify:** `pytest backend/tests/integration/api/test_admin_oauth.py -q -k "multi_channel"` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/oauth_token_service.py backend/app/schemas/publish.py && git commit -m "feat(publish): 8-2 support multi-channel selection"` → `git push`

### Step 5: Revoke/reconnect (BR-4) + audit logging
- **Files:** `backend/app/services/oauth_token_service.py`, `backend/app/api/routes/admin_oauth.py`, audit log integration
- **Do:** disconnect action deletes the encrypted token row and best-effort revokes at Google; every connect/reconnect/revoke admin action writes an audit log entry (per `rules/security.md` "Admin actions ... are audit-logged — no silent admin mutation"); after disconnect, YouTube publish state reads "chưa cấu hình" (AC5).
- **Verify:** `pytest backend/tests/integration/api/test_admin_oauth.py -q -k "revoke"` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/oauth_token_service.py backend/app/api/routes/admin_oauth.py && git commit -m "feat(publish): 8-2 add revoke/reconnect + audit logging"` → `git push`

### Step 6: Admin › API Keys UI — YouTube connect block
- **Files:** frontend under `src/app/admin/` per `rules/folder-structure.md`, matching the YouTube wireframe block
- **Do:** states: chưa kết nối (Connect button) · đang connect (waiting for callback) · đã kết nối (channel name+avatar) · mất kết nối (⚠ + reconnect) · error (translated message); publish-tab row reflects ⚠ automatically per BR-2.
- **Verify:** exercise in a real running browser (per `rules/testing.md`) — screenshot each state; `npm run typecheck` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add src/app/admin/... && git commit -m "feat(publish): 8-2 add Admin API Keys YouTube connect UI"` → `git push`

### Step 7: Wire up tests + verify all Acceptance Criteria (mock Google OAuth server)
- **Files:** `backend/tests/integration/api/test_admin_oauth.py`, `backend/tests/unit/services/test_oauth_token_service.py`
- **Do:** mock Google OAuth server for the full integration suite (per Test Notes); one test per AC (AC1 happy connect, AC2 BR-2 refresh-401, AC3 BR-1/3 security — **grep log/response output asserting no token substring present**, AC4 multi-channel, AC5 BR-4 disconnect); a real end-to-end flow against a real test Google account is checked by hand once and the result noted in the PR description (not automatable in CI).
- **Verify:** `pytest backend/tests/integration/api/test_admin_oauth.py backend/tests/unit/services/test_oauth_token_service.py -q` → all AC-mapped tests pass, including the log-grep assertion.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests/ && git commit -m "test(publish): 8-2 cover all acceptance criteria incl. token-leak grep"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock Google OAuth server trong integration test; flow thật kiểm tay 1 lần (ghi vào PR).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/8-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/8-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
