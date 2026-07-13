# Task 8-5: Analytics collector

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-3, 7-1 · **FR:** FR-13
**State file:** [`state/8-5.json`](state/8-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/8-5-analytics-collector` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want số liệu video tự động cập nhật hàng ngày từ YouTube, so that biết nội dung nào hiệu quả mà không phải mở từng nền tảng chép tay.

## Why
FR-13 phần thu thập. Thiết kế "api + manual cùng schema" cho phép nền tảng chưa có API (TikTok chờ duyệt) vẫn có mặt trong dashboard từ ngày 1.

## Scope
**In:** job daily (7-1) YouTube Analytics API → metrics (views/likes/comments/watch_time/avg%); dedupe (unique index + upsert); backfill 28 ngày khi video mới connect; form nhập tay (§8 api-spec).
**Out:** dashboard (8-6); realtime metrics; nền tảng khác qua API (10-3+/v1.1).

## Business Rules
1. Chạy lại không nhân đôi (upsert theo publish/metric/ngày/source).
2. Video bị xoá trên YouTube → đánh dấu, ngừng thu, job vẫn xanh.
3. Nhập tay source=manual — job API không ghi đè manual (2 dòng song song, dashboard ưu tiên api khi cả hai).
4. Quota Analytics API riêng với upload quota — đếm riêng.

## Acceptance Criteria
1. **(happy)** Video đăng 3 ngày → 3 ngày metrics; re-run job → số dòng không đổi.
2. **(biên/BR-3)** Nhập tay TikTok views → lưu manual; job sau không đè.
3. **(lỗi/BR-2)** Video deleted (mock 404) → cờ + job xanh + các video khác thu bình thường.
4. **(backfill)** Video cũ 30 ngày mới connect → backfill 28 ngày.

## Data & API
Bảng: metrics partition. Endpoint manual entry §8. Contract change: không.

## Decisions already locked
- ⏳ Thu 06:00 hàng ngày (trước giờ PO xem 07:00+).

## Execution Steps

Work these in order. Update `state/8-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Daily collector job (06:00) on the 7-1 scheduler
- **Files:** `backend/app/pipeline/jobs/analytics_collector_job.py`, registration in the 7-1 job scheduler
- **Do:** register a daily job (fires 06:00, per locked decision) that pulls YouTube Analytics API metrics (views/likes/comments/watch_time/avg%) for every active published video; Analytics API quota counted separately from upload quota (BR-4) — do not share the `quota_used_today` counter from 8-3.
- **Verify:** `mypy backend/app/pipeline/jobs/analytics_collector_job.py --strict` → 0 errors.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/pipeline/jobs/analytics_collector_job.py && git commit -m "feat(analytics): 8-5 add daily YouTube analytics collector job"` → `git push`

### Step 2: Upsert with dedupe (BR-1)
- **Files:** `backend/app/services/metrics_service.py`, unique index migration on `metrics` (publish_id, metric, date, source)
- **Do:** add a unique index on `(publish_id, metric_key, date, source)` in the `metrics` partitioned table; write collector inserts as upsert-on-conflict so re-running the job never duplicates rows (BR-1, AC1's "re-run job → row count unchanged"). High-volume table already partitioned by month per `rules/performance.md` — don't retrofit partitioning later, confirm it's present from this migration.
- **Verify:** run migration against scratch DB → applies cleanly; `pytest backend/tests/unit/services/test_metrics_service.py -q -k "upsert_idempotent"` → passes (asserts 3x same-day run produces same row count).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/metrics_service.py alembic/ && git commit -m "feat(analytics): 8-5 add upsert dedupe on metrics"` → `git push`

### Step 3: Deleted-video handling (BR-2)
- **Files:** `backend/app/pipeline/jobs/analytics_collector_job.py`, `backend/app/services/metrics_service.py`
- **Do:** on a 404 from YouTube for a given video, flag it (e.g. `publishes.deleted_on_platform`) and stop collecting for that video going forward, while the job itself still completes green and continues collecting for the remaining videos (BR-2) — per `rules/error-handling.md`, one video's failure must not abort the whole run.
- **Verify:** `pytest backend/tests/unit/adapters/... -q -k "deleted_video"` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/pipeline/jobs/analytics_collector_job.py backend/app/services/metrics_service.py && git commit -m "feat(analytics): 8-5 handle deleted-video 404 gracefully"` → `git push`

### Step 4: Backfill 28 days on new connect
- **Files:** `backend/app/services/metrics_service.py`
- **Do:** when a video is newly connected/discovered by the collector, backfill the trailing 28 days of available metrics in one pass, not just going forward from today.
- **Verify:** `pytest backend/tests/unit/services/test_metrics_service.py -q -k "backfill"` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/metrics_service.py && git commit -m "feat(analytics): 8-5 add 28-day backfill on new video connect"` → `git push`

### Step 5: Manual metric entry endpoint (BR-3)
- **Files:** `backend/app/api/routes/analytics.py` (per §8 api-spec)
- **Do:** implement the manual entry endpoint so metrics without an API (e.g. TikTok) can be recorded with `source=manual`; the API-sourced job must never overwrite a manual row (BR-3) — both rows persist in parallel and the dashboard (8-6) picks `api` over `manual` when both exist for the same metric/date. Router calls `metrics_service` only, no business logic in the route.
- **Verify:** `pytest backend/tests/integration/api/test_analytics_manual_entry.py -q` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/routes/analytics.py && git commit -m "feat(analytics): 8-5 add manual metric entry endpoint"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/services/test_metrics_service.py`, `backend/tests/integration/api/test_analytics_manual_entry.py`, `tests/fixtures/analytics/`
- **Do:** mock Analytics API responses per day (Test Notes); one test per AC (AC1 happy 3-day-collection + idempotent re-run, AC2 BR-3 manual-not-overwritten-by-api + source shown correctly, AC3 BR-2 deleted-video-flag-and-job-still-green, AC4 backfill-28-days).
- **Verify:** `pytest backend/tests/unit/services/test_metrics_service.py backend/tests/integration/api/test_analytics_manual_entry.py -q` → all AC-mapped tests pass, including running the upsert test 3x against identical fixture data.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests/ && git commit -m "test(analytics): 8-5 cover all acceptance criteria"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock Analytics API responses theo ngày; test upsert kỹ (chạy 3 lần cùng dữ liệu).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/8-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/8-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
