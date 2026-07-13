# Task 9-4: DLQ + Quản trị › Hàng đợi

**Points:** 3đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-1, 7-4 · **FR:** NFR-3
**State file:** [`state/9-4.json`](state/9-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/9-4-dlq-quan-tri-hang-doi` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

> **Sequencing note:** part of Epic 9, started only after Epic 6 (M4) is `done` (ADR-0001, see `tasks/README.md`). Depends on both `9-1` (event bus/DLQ mechanics) and `7-4` (notification channel for the alert) — verify both are `done` before claiming.

## User story
As an Admin, I want thấy message lỗi, hiểu lý do và replay sau khi sửa, so that sự cố hàng đợi xử lý trong phút thay vì mò log container.

## Why
DLQ không có UI = hố đen vận hành. `docs/runbook.md` §3.5 đã viết quy trình — task này cho nó công cụ.

## Scope
**In:** API queue stats (pending/redeliver/DLQ per stream), payload viewer (che secret), replay, xoá (audit); tab Quản trị › Hàng đợi (wireframe); alert DLQ>0 (7-4).
**Out:** replay hàng loạt có filter (v1.1); sửa payload trước replay (nguy hiểm — không cho).

## Business Rules
1. Replay message đã thành công → no-op (idempotency downstream).
2. Xoá message → audit (ai/lúc/payload hash).
3. Payload viewer che field nhạy cảm theo denylist (token/key pattern).
4. Alert DLQ gộp ("DLQ có 3 message") không bắn từng cái.

## Acceptance Criteria
1. **(happy)** Message vào DLQ → alert Telegram (gộp) → xem payload → sửa nguyên nhân → replay → xử lý OK, DLQ trống.
2. **(biên/BR-1)** Replay message đã ok trước đó → no-op không side-effect.
3. **(BR-3)** Payload chứa "api_key=..." → hiển thị che.
4. **(quyền)** Admin only; audit xoá query được.

## Data & API
Endpoints §9 queue/dlq. Contract change: không.

## Decisions already locked
- Không sửa payload trước replay (chống tạo dữ liệu tay ngoài luồng).

## Execution Steps

Work these in order. Update `state/9-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Queue stats API
- **Files:** `backend/app/api/admin/queue.py`, `backend/app/services/queue_stats.py`
- **Do:** New router under the Admin API surface returning pending/redeliver/DLQ counts per stream (RENDER/MEDIA/PUBLISH/EVENTS from `9-1`), reading from NATS JetStream management API via the `9-1` event lib. No business logic in the router — router calls `queue_stats.py` service, per `rules/code-style.md`.
- **Verify:** `pytest backend/tests/unit/api/admin/test_queue.py -k stats` → returns correct counts against a seeded test stream.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/api/admin/queue.py backend/app/services/queue_stats.py && git commit -m "feat(admin): 9-4 queue stats API (pending/redeliver/DLQ per stream)"` → `git push`

### Step 2: DLQ payload viewer with denylist masking (BR-3)
- **Files:** `backend/app/services/dlq.py`, `backend/app/core/denylist.py`
- **Do:** Endpoint to fetch a DLQ message's payload, masking fields matching a token/key pattern denylist before returning (BR-3, AC-3: `"api_key=..."` → masked). Denylist patterns live in one shared module so `9-6`'s trace-sample denylist test (same pattern) can reuse it — don't duplicate the pattern list.
- **Verify:** `pytest backend/tests/unit/services/test_dlq.py -k denylist` → payload with `api_key=`, `token=`, secret-shaped strings comes back masked; non-sensitive fields untouched.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/dlq.py backend/app/core/denylist.py && git commit -m "feat(admin): 9-4 DLQ payload viewer with secret denylist masking (BR-3)"` → `git push`

### Step 3: Replay endpoint — idempotency-safe (BR-1, ties to redelivery rule)
- **Files:** `backend/app/api/admin/queue.py`, `backend/app/services/dlq.py`
- **Do:** Replay re-publishes the DLQ message onto its original subject. This must produce the same "redelivered message must not double-render or double-charge" guarantee as `rules/error-handling.md` already requires of every consumer (render-worker's `cache_key` check from `9-2`, produce's cache check from `9-3`) — replay is just another form of redelivery, not a special case. If the downstream consumer already processed an equivalent job successfully, replay is a no-op (BR-1, AC-2). Do not add payload-editing before replay — explicitly out of scope (Decisions already locked: "Không sửa payload trước replay").
- **Verify:** `pytest backend/tests/integration/admin/test_dlq_replay.py -k noop_on_already_processed` → replaying a message whose job already completed produces no new side effect (asserted via the downstream idempotency check, not a special DLQ-side flag).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/admin/queue.py backend/app/services/dlq.py && git commit -m "feat(admin): 9-4 DLQ replay relies on downstream idempotency (BR-1, no double-processing)"` → `git push`

### Step 4: Delete endpoint with audit log (BR-2)
- **Files:** `backend/app/api/admin/queue.py`, `backend/app/services/audit.py`
- **Do:** Delete a DLQ message permanently removes it from the stream and writes an audit record (who/when/payload hash) — per `rules/security.md` ("Admin actions ... are audit-logged — no silent admin mutation") and BR-2. This is a permanent-delete action; confirm it's gated behind Admin-only RBAC (AC-4), not exposed to other roles.
- **Verify:** `pytest backend/tests/unit/api/admin/test_queue.py -k delete_audit` → delete call produces exactly one queryable audit row with correct actor/timestamp/payload hash.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/admin/queue.py backend/app/services/audit.py && git commit -m "feat(admin): 9-4 DLQ delete with audit trail (BR-2), Admin-only RBAC"` → `git push`

### Step 5: Aggregated DLQ alert (BR-4, via 7-4)
- **Files:** `backend/app/services/queue_stats.py`, `backend/app/services/notifications.py` (7-4 integration point)
- **Do:** Alert on DLQ>0 batches into one notification per polling window ("DLQ có 3 message"), not one alert per message (BR-4). Wire through the existing 7-4 Telegram/email notification channel — don't build a second notification path.
- **Verify:** `pytest backend/tests/unit/services/test_queue_stats.py -k aggregated_alert` → 3 simultaneous DLQ arrivals produce exactly 1 notification call with count 3.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/ && git commit -m "feat(admin): 9-4 aggregated DLQ alert via 7-4 notification channel (BR-4)"` → `git push`

### Step 6: Quản trị › Hàng đợi UI tab
- **Files:** `frontend/src/app/admin/queue/page.tsx`, `frontend/src/components/admin/QueueTable.tsx`
- **Do:** New Admin tab per the wireframe (`docs/design/wireframe.html` "Quản trị › Hàng đợi"), all 5 UI states (default/loading/empty "hàng đợi sạch ✓"/error — NATS unreachable banner/disabled N/A), table caption for a11y, Replay button requires confirm dialog before firing. API types generated from OpenAPI, not hand-written (`rules/code-style.md`).
- **Verify:** `make gen-api-client && npm run build` (frontend) → 0 type errors; manual/browser exercise per `rules/testing.md` ("UI/frontend stories require exercising the feature in a real running browser before being marked complete").
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/app/admin/queue/ frontend/src/components/admin/ && git commit -m "feat(admin-ui): 9-4 Quản trị Hàng đợi tab, 5 UI states, replay confirm"` → `git push`

### Step 7: Seed-DLQ tests + full AC coverage
- **Files:** `backend/tests/integration/admin/test_dlq.py`
- **Do:** Seed the DLQ using a consumer that deliberately fails (per Definition of Done), then exercise the full happy path end-to-end: message → DLQ → aggregated alert → view payload (masked) → replay → DLQ empty (AC-1). Add the standalone denylist permanence test referenced in DoD.
- **Verify:** `pytest backend/tests/integration/admin/test_dlq.py -v` → all AC-tagged tests pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests/ && git commit -m "test(admin): 9-4 seed-DLQ end-to-end + full AC coverage"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + seed DLQ bằng consumer cố tình fail; test denylist che secret giữ vĩnh viễn.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/9-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/9-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
