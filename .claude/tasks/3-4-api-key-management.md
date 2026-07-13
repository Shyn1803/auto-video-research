# Task 3-4: API Key management + mã hoá + xoay key

**Points:** 3đ · **Epic:** 3 — Provider framework · **Depends:** 3-2 · **FR:** FR-15
**State file:** [`state/3-4.json`](state/3-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/3-4-api-key-management` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As an Admin, I want quản lý key an toàn với xoay vòng tự động, so that tận dụng nhiều free tier mà không lộ secret và không phải canh quota tay.

## Why
FR-15. Free tier là chiến lược chi phí của dự án — xoay key tự động biến "quota hết" từ sự cố thành non-event.

## Scope
**In:** bảng `api_keys` Fernet; CRUD 🅐 (masked response); validate key thật trước lưu (test call nhẹ); round-robin nhiều key/provider; 429 → `exhausted_until` → tự re-activate; tab Quản trị › API Keys.
**Out:** YouTube OAuth (8-2 — flow riêng cùng bảng); Fernet rotation script (10-4).

## Business Rules
1. Key plaintext không xuất hiện trong response/log sau lưu — chỉ masked `AIza…x4Kq`. See [rules/security.md](../rules/security.md).
2. Xoá key cuối của provider đang trong chain active → cảnh báo hệ quả trước khi xoá.
3. env key + DB key cùng provider → cả hai vào vòng xoay, env đứng trước.
4. `exhausted_until` mặc định = reset time provider (config/provider; không rõ → 00:00 UTC).

## Acceptance Criteria
1. **(happy)** 2 key gemini, key1 mock 429 → tự sang key2; key1 hiện "⚠ hết hạn mức → 00:00"; 00:00 tự active.
2. **(biên/BR-3)** Env + DB key → thứ tự đúng, cả hai được dùng.
3. **(lỗi)** POST key sai → 400 "key không hợp lệ", không lưu.
4. **(bảo mật/BR-1)** Test tự động grep log+response sau lưu → không plaintext.
5. **(biên/BR-2)** Xoá key cuối gemini khi gemini trong LLM_CHAIN → dialog nêu hệ quả.

## Data & API
Bảng: api_keys. Endpoints §9 CRUD. Contract change: không.

## UI/UX
Wireframe Quản trị › API Keys. States: default(bảng)/loading/empty(link CONFIGURATION)/error/disabled N/A.

## Decisions already locked
- Validate key bằng call nhẹ nhất của từng provider (models.list tương đương).

## Execution Steps

Work these in order. Update `state/3-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: `api_keys` table with Fernet encryption at rest
- **Files:** `backend/app/models/api_key.py`, `backend/alembic/versions/{ts}_add_api_keys.py`
- **Do:** SQLAlchemy 2.0 model matching `docs/specs/database-schema.md` §2.7 exactly (snake_case columns, per [rules/naming.md](../rules/naming.md)) with the key value Fernet-encrypted at rest; master key sourced from env per [rules/security.md](../rules/security.md) ("API keys encrypted at rest with Fernet; master key from env, KMS when on cloud"). Never store a plaintext key anywhere.
- **Verify:** `alembic upgrade head` against a test DB → table created; unit test for Fernet encrypt/decrypt roundtrip.
- **On failure:** transient (DB not up) → retry 3×; logic error → `systematic-debugging` skill; still failing → mark step/task `blocked`, log in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/models/api_key.py backend/alembic/ && git commit -m "feat(keys): 3-4 api_keys table with Fernet encryption at rest" && git push`

### Step 2: CRUD endpoints with masked response (BR-1)
- **Files:** `backend/app/api/admin/api_keys.py`, `backend/app/services/api_key_service.py`
- **Do:** Router calls service, no business logic in the router (per [rules/code-style.md](../rules/code-style.md)). Response never includes plaintext — only masked form (`AIza…x4Kq`) per BR-1. RBAC-gated as an Admin route per [rules/security.md](../rules/security.md) ("RBAC middleware on every route, not opt-in").
- **Verify:** integration test: POST a key, GET it back → response body contains only masked value, never plaintext.
- **On failure:** same policy.
- **Commit:** `git add backend/app/api/admin/api_keys.py backend/app/services/api_key_service.py && git commit -m "feat(keys): 3-4 CRUD endpoints with masked responses" && git push`

### Step 3: Validate-before-save via lightweight provider call
- **Files:** `backend/app/services/api_key_service.py`, `backend/app/config/provider_validation.yaml` (or equivalent per-provider "lightest call" table)
- **Do:** Before persisting a new key, perform the provider's lightest validation call (e.g. `models.list`-equivalent, decision already locked). Invalid key → `400` with message "key không hợp lệ", nothing persisted (AC3).
- **Verify:** integration test: POST an invalid key (mocked 401 from provider) → `400`, `api_keys` table row count unchanged.
- **On failure:** same policy.
- **Commit:** `git add backend/app/services/api_key_service.py backend/app/config/provider_validation.yaml && git commit -m "feat(keys): 3-4 validate key via lightweight provider call before save" && git push`

### Step 4: Round-robin multi-key + env-key-first ordering (BR-3)
- **Files:** `backend/app/services/api_key_service.py`, `backend/app/core/router.py` (integration point with 3-2)
- **Do:** When a provider has multiple active keys (env + DB), the router's key-rotation (stubbed in 3-2 Step 3) resolves to: env-sourced key(s) first in rotation order, then DB keys, all participating in round-robin (BR-3). This is the concrete implementation of the "rotate key" branch 3-2 left as a placeholder.
- **Verify:** unit test: 1 env key + 1 DB key for the same provider → both counters increment across repeated calls, env key used first.
- **On failure:** same policy.
- **Commit:** `git add backend/app/services/api_key_service.py backend/app/core/router.py && git commit -m "feat(keys): 3-4 round-robin rotation, env keys ordered before DB keys" && git push`

### Step 5: 429 → `exhausted_until` → auto re-activation (BR-4)
- **Files:** `backend/app/services/api_key_service.py`
- **Do:** On a `QuotaError`/429 from a key, set `exhausted_until` per the provider's known reset time (config/provider table); if unknown, default to 00:00 UTC (BR-4). A background check (or lazy check on next use) re-activates the key once `exhausted_until` has passed.
- **Verify:** unit test (AC1): key1 mocked 429 → router moves to key2; key1 shows exhausted state; after simulated clock past `exhausted_until` → key1 active again.
- **On failure:** same policy.
- **Commit:** `git add backend/app/services/api_key_service.py && git commit -m "feat(keys): 3-4 429 exhausted_until tracking + auto re-activation" && git push`

### Step 6: Delete-last-active-key consequence warning (BR-2)
- **Files:** `backend/app/api/admin/api_keys.py`, `frontend/src/app/admin/api-keys/page.tsx`
- **Do:** Backend: DELETE endpoint returns a consequence payload (which capability/chain loses a provider) when deleting the last key of a provider that's in an active chain, rather than deleting silently. Frontend: confirmation dialog surfaces that consequence before the delete is submitted (BR-2, AC5).
- **Verify:** integration test: delete the only gemini key while `gemini` is in `LLM_CHAIN_*` → response/dialog states the consequence; a follow-up confirmed DELETE actually removes it.
- **On failure:** same policy.
- **Commit:** `git add backend/app/api/admin/api_keys.py frontend/src/app/admin/api-keys/page.tsx && git commit -m "feat(keys): 3-4 delete-last-active-key consequence warning" && git push`

### Step 7: Admin › API Keys tab UI
- **Files:** `frontend/src/app/admin/api-keys/page.tsx`, `frontend/src/components/admin/ApiKeysTable.tsx`
- **Do:** Implement per the wireframe **Quản trị › API Keys**: default (table), loading skeleton, empty state ("chưa có key — hệ thống đang chạy local" + link to CONFIGURATION docs), error banner. A11y: revoke button requires confirm, table has a caption (per Scope UI/UX notes). API types generated from OpenAPI, never hand-written (per [rules/code-style.md](../rules/code-style.md)).
- **Verify:** exercise the page in a real running browser per [rules/testing.md](../rules/testing.md) ("UI/frontend stories require exercising the feature in a real running browser") — confirm all 4 states render correctly.
- **On failure:** same policy.
- **Commit:** `git add frontend/src/app/admin/api-keys/ frontend/src/components/admin/ApiKeysTable.tsx && git commit -m "feat(keys): 3-4 Admin API Keys tab UI" && git push`

### Step 8: Security regression test — plaintext never surfaces (BR-1, permanent)
- **Files:** `backend/tests/security/test_api_key_plaintext.py`
- **Do:** Automated test that saves a key, then greps captured logs + all response bodies from the save/list/get flows for the plaintext value — must find zero occurrences (AC4). Per [rules/testing.md](../rules/testing.md) and [rules/security.md](../rules/security.md), this test is kept permanently as a regression guard, never removed or weakened.
- **Verify:** `pytest backend/tests/security/test_api_key_plaintext.py -v` → passes.
- **On failure:** same policy — this test failing is a security regression, treat as non-transient by default (invoke `systematic-debugging`).
- **Commit:** `git add backend/tests/security/test_api_key_plaintext.py && git commit -m "test(keys): 3-4 permanent regression test — plaintext key never in log/response" && git push`

### Step 9: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/services/test_api_key_service.py`, `backend/tests/integration/test_api_keys_api.py`
- **Do:** Fernet roundtrip unit test (if not already covered in Step 1); one test per remaining AC (1, 2, 3, 5); validate-call mocked per provider per Test Notes.
- **Verify:** `pytest backend/tests/unit/services/test_api_key_service.py backend/tests/integration/test_api_keys_api.py backend/tests/security/test_api_key_plaintext.py -v` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** `git add backend/tests/unit/services/test_api_key_service.py backend/tests/integration/test_api_keys_api.py && git commit -m "test(keys): 3-4 full AC coverage for API key management" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + Fernet roundtrip unit; test bảo mật BR-1 giữ vĩnh viễn (regression).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/3-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/3-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
