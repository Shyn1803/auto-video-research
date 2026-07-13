# Task 7-4: Notification — Telegram + email

**Points:** 3đ · **Epic:** 7 — Automation · **Depends:** 7-2 · **FR:** Reliability
**State file:** [`state/7-4.json`](state/7-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/7-4-notification-telegram-email` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a PO/Admin, I want nhận thông báo qua Telegram khi có việc cần tôi hoặc có sự cố, so that không phải mở dashboard canh chừng hệ thống chạy đêm.

## Why
Mode 1 chạy không người trông — notification là "giác quan" duy nhất. Deep-link mở đúng màn (BR-3) biến thông báo thành hành động 1 chạm (nối 7-5).

## Scope
**In:** notification adapter (telegram bot / SMTP) theo khung 3-1, env-activated; sự kiện: factcheck FAIL, pipeline FAILED/timeout, video READY (deep-link), cost cap, provider exhausted, DLQ>0 (nối 9-4); template tiếng Việt ngắn; chống spam gộp 5'.
**Out:** in-app notification center (v1.1); digest tuần; phân kênh theo loại (v1 mọi thứ 1 kênh).

## Business Rules
1. Không token → skip lặng (log debug 1 lần), không lỗi.
2. Cùng loại + cùng project trong 5' → gộp 1 tin.
3. Deep-link mở đúng màn cần thao tác; link hoạt động trên mobile browser.
4. Gửi fire-and-forget — Telegram/SMTP chết không ảnh hưởng pipeline.

## Acceptance Criteria
1. **(happy)** Video READY → tin có tiêu đề video + link mở đúng tab Xuất bản (test mobile viewport).
2. **(biên/BR-2)** 3 lỗi liên tiếp 1 run → 1 tin gộp "3 lỗi".
3. **(lỗi/BR-4)** Telegram 500 → pipeline không ảnh hưởng; log warning.
4. **(BR-1)** Không token → không lỗi, không spam log.

## Data & API
Env: TELEGRAM_*, SMTP_URL. Contract change: không.

## Decisions already locked
- ⏳ 1 kênh Telegram chung v1 (không phân admin/creator) — đội nhỏ.

## Execution Steps

Work these in order. Update `state/7-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Notification adapter base + Telegram/SMTP providers
- **Files:** `backend/app/adapters/notification/base.py`, `backend/app/adapters/notification/telegram.py`, `backend/app/adapters/notification/smtp.py`
- **Do:** follow the adapter skeleton in `docs/dev-guide.md` §3 and [patterns/provider-adapter.md](../patterns/provider-adapter.md) exactly: base class + `@register_notification("telegram"/"smtp")`, `available()` + send method, config via `ProviderSettings` (env `TELEGRAM_*`, `SMTP_URL`) — never `os.environ` read directly inside the adapter (`rules/code-style.md`). Missing token/config → `available()` returns false, adapter skips silently, logs debug once (BR-1) — never raises.
- **Verify:** `cd backend && pytest backend/tests/unit/adapters/notification/ -v` → mocked HTTP via `respx` (no live network per `rules/testing.md`); no-token case logs exactly once at debug level, no exception. Covers AC4/BR-1.
- **On failure:** transient → retry 3×; adapter-pattern violation or logic bug → `systematic-debugging` skill; still failing → `blocked`.
- **Commit:** `git add backend/app/adapters/notification && git commit -m "feat(notify): 7-4 telegram + smtp notification adapters"` → `git push`

### Step 2: Event wiring — factcheck FAIL, pipeline FAILED/timeout, READY, cost cap, provider exhausted, DLQ>0
- **Files:** `backend/app/services/notifications.py`, hook points in `backend/app/pipeline/graph.py`, `backend/app/services/cost_tracking.py` (3-5), DLQ handling (9-4, may be a stub call if 9-4 not yet merged — coordinate via `sprint-status.yaml`)
- **Do:** dispatch a notification through the Step 1 adapter for each of the 6 listed events; call is fire-and-forget (async task / background job, not awaited inline in the pipeline critical path) so a Telegram/SMTP outage never blocks or fails the pipeline (BR-4).
- **Verify:** `cd backend && pytest backend/tests/unit/services/test_notifications.py -k fire_and_forget` → adapter raises/times out → pipeline node completes normally, only a warning logged. Covers AC3/BR-4.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(notify): 7-4 wire pipeline/cost/dlq events to notifications"` → `git push`

### Step 3: Vietnamese templates + deep-links
- **Files:** `backend/app/services/notification_templates.py`
- **Do:** short Vietnamese templates per event type, consistent status emoji (✓⚠✗) per UI/UX note; every actionable event includes a deep-link to the exact screen needing action (e.g. video READY → link opens the Xuất bản tab directly, per BR-3) and the link must resolve correctly from a mobile browser (no desktop-only routing assumptions).
- **Verify:** `cd backend && pytest backend/tests/unit/services/test_notification_templates.py -v` → snapshot test per event type (per Test Notes) confirms template shape; a manual/E2E check that the READY deep-link opens the correct tab is exercised via the 7-5 dashboard once that task lands (cross-reference, not duplicated here).
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(notify): 7-4 vietnamese templates + deep-links"` → `git push`

### Step 4: 5-minute spam coalescing (BR-2)
- **Files:** `backend/app/services/notifications.py` (extend)
- **Do:** same event type + same project within a 5-minute window → coalesce into a single message (e.g. "3 lỗi") instead of 3 separate sends.
- **Verify:** `cd backend && pytest backend/tests/unit/services/test_notifications.py -k coalesce` → 3 errors fired within 5' for one project → exactly 1 outbound send with a "3 lỗi" summary. Covers AC2/BR-2.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(notify): 7-4 5-minute spam coalescing"` → `git push`

### Step 5: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/adapters/notification/`, `backend/tests/unit/services/`
- **Do:** one test per AC (already covered incrementally above); this step is the consolidation pass — confirm the READY-event mobile deep-link test (AC1) exists explicitly (mobile viewport assertion may live with 7-5's Playwright suite if that task is available, otherwise assert URL shape here).
- **Verify:** `cd backend && pytest tests/ -k notif -v` → all AC-mapped tests pass.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "test(notify): 7-4 full AC coverage"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock Telegram API; test template render đủ loại sự kiện (snapshot).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/7-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/7-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
