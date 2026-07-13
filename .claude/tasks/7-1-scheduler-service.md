# Task 7-1: Scheduler service

**Points:** 5đ · **Epic:** 7 — Automation · **Depends:** 6-2 · **FR:** FR-16
**State file:** [`state/7-1.json`](state/7-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/7-1-scheduler-service` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As an Admin, I want đặt lịch các việc chạy định kỳ và xem lịch sử từng lần chạy, so that hệ thống tự vận hành và tôi biết đêm qua nó đã làm gì, tốn bao nhiêu.

## Why
FR-16 — hạ tầng của Mode 1, analytics collector, publish hẹn giờ, cleanup. Advisory lock chống double-run là điều kiện an toàn khi scale API instance sau này.

## Scope
**In:** APScheduler + advisory lock Postgres; bảng schedules/schedule_runs; 4 loại job (mode1_pipeline / analytics_collect / publish / cleanup); API CRUD + enable/disable + run-now + history; tab Quản trị › Lịch chạy; cleanup job (cache render TTL + partition mới + backup trigger).
**Out:** NATS-based scheduler; cron editor trực quan (nhập cron + preview mô tả chữ).

## Business Rules
1. 2 instance API → mỗi lần nổ lịch đúng 1 job chạy (advisory lock — test 2 process).
2. Job trước chưa xong khi tới lịch kế → skip + cảnh báo (không chồng).
3. run-now độc lập lịch định kỳ (không reset next-run).
4. Mỗi run ghi cost tổng (sum llm_usage theo correlation_id).
5. Cron nhập sai → 400 kèm ví dụ đúng; preview "07:00 mỗi ngày" trước khi lưu.
6. **(PO 2026-07-11)** cleanup job tự lưu trữ project Mode 1 đã PUBLISHED sau `AUTO_ARCHIVE_DAYS` (mặc định 30; 0 = tắt); ghi audit actor=system.

## Acceptance Criteria
1. **(happy)** Cron `0 7 * * *` enabled → đúng giờ tạo run; disable → im.
2. **(biên/BR-1)** 2 process API, 1 lịch nổ → 1 run duy nhất (test tự động).
3. **(biên/BR-2)** Job treo qua lịch kế → skip + notify; history ghi skip.
4. **(lỗi/BR-5)** Cron "99 * * * *" → 400 kèm ví dụ.
5. **(BR-4)** Run Mode 1 xong → cost hiện trong history khớp llm_usage.

## Data & API
Bảng: schedules, schedule_runs (partition). Endpoints §9. Contract change: không.

## Decisions already locked
- ⏳ Cleanup mặc định 03:00 hàng ngày, tạo sẵn khi migrate (enabled).

## Execution Steps

Work these in order. Update `state/7-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: DB schema — schedules + schedule_runs
- **Files:** `backend/alembic/versions/{rev}_schedules.py`, `backend/app/models/schedule.py`
- **Do:** create `schedules` table (id, job_type enum [mode1_pipeline, analytics_collect, publish, cleanup], cron, config JSONB, enabled, next_run_at, created_by) and `schedule_runs` table partitioned by month (id, schedule_id FK, started_at, finished_at, status [running/success/failed/skipped], cost_total, correlation_id, skip_reason) per `rules/performance.md` (high-volume tables partitioned from first migration) and `docs/specs/database-schema.md` §2.7 naming.
- **Verify:** `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head` → clean up/down, no errors.
- **On failure:** transient (DB not up) → retry 3× with backoff; migration/logic error → `systematic-debugging` skill; still failing → mark step+task `blocked`.
- **Commit:** `git add backend/alembic backend/app/models/schedule.py && git commit -m "feat(scheduler): 7-1 add schedules and schedule_runs tables"` → `git push`

### Step 2: Advisory lock + APScheduler wiring
- **Files:** `backend/app/services/scheduler.py`, `backend/app/core/advisory_lock.py`
- **Do:** implement `pg_try_advisory_lock(job_id_hash)` wrapper used before executing any due job; wire APScheduler (`AsyncIOScheduler` + `SQLAlchemyJobStore` or custom store reading `schedules` table) so a job firing on 2 API instances at once results in exactly one execution (BR-1). Job trigger checks previous `schedule_runs` row for that schedule still `running` → mark this fire `skipped` + emit warning event, do not queue (BR-2).
- **Verify:** `cd backend && pytest backend/tests/integration/test_scheduler_lock.py -k two_process` → spawn 2 worker processes against same schedule, exactly 1 `schedule_runs` row with status `success`, one skip logged if applicable. Covers AC2, AC3.
- **On failure:** transient (port/DB) → retry 3×; race-condition logic bug → `systematic-debugging` skill (do not just add sleeps); still failing after 3 → `blocked`.
- **Commit:** `git commit -m "feat(scheduler): 7-1 advisory lock + APScheduler double-run guard"` → `git push`

### Step 3: 4 job type handlers + cost aggregation
- **Files:** `backend/app/services/jobs/mode1_pipeline_job.py`, `analytics_collect_job.py`, `publish_job.py`, `cleanup_job.py`
- **Do:** each handler is a thin dispatcher (business logic lives in the pipeline/service it calls — no logic in the scheduler layer itself, per `rules/code-style.md`). `cleanup_job.py` implements BR-6: archive Mode 1 `PUBLISHED` projects older than `AUTO_ARCHIVE_DAYS` (env, default 30; `0` = disabled) with `actor=system` audit row, plus render-cache TTL sweep, new month partition creation, backup trigger — per "Decisions already locked" (default schedule 03:00 daily, enabled at migration time). Every run writes `cost_total = sum(llm_usage.cost) WHERE correlation_id = run.correlation_id` on completion (BR-4).
- **Verify:** `cd backend && pytest backend/tests/unit/services/jobs/ -v` → all 4 handlers have a unit test (mocked dependencies); cleanup respects `AUTO_ARCHIVE_DAYS=0` disabling itself.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(scheduler): 7-1 job handlers incl. cleanup auto-archive"` → `git push`

### Step 4: API — CRUD, enable/disable, run-now, history, cron validation
- **Files:** `backend/app/api/schedules.py`, `backend/app/schemas/schedule.py`
- **Do:** `POST/GET/PATCH/DELETE /schedules`, `POST /schedules/{id}/run-now` (BR-3: does not reset `next_run_at`), `GET /schedules/{id}/runs` (history, paginated). Cron string validated with a strict parser; invalid cron → `400` with a corrected example in the error body, and a human-readable preview string (e.g. "07:00 mỗi ngày") returned on valid input before save (BR-5). No business logic in the router — router calls `schedule_service` functions per `rules/code-style.md`.
- **Verify:** `cd backend && pytest backend/tests/unit/api/test_schedules.py -v` → covers valid cron accept + preview, invalid cron `"99 * * * *"` → 400 with example (AC4), run-now doesn't mutate `next_run_at` (BR-3).
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(scheduler): 7-1 schedules CRUD + run-now + history API"` → `git push`

### Step 5: Frontend — Quản trị › Lịch chạy tab
- **Files:** `frontend/src/app/admin/schedules/page.tsx`, `frontend/src/components/admin/ScheduleTable.tsx`
- **Do:** table of schedules with enable/disable toggle (labeled per a11y note), run-now button, history drawer with cost + status; states default/loading/empty (suggest creating Mode 1 schedule)/error banner/disabled (cleanup job can't be deleted, only toggled). API types generated via `make gen-api-client` — no hand-written duplicate interfaces.
- **Verify:** exercise in a real running browser (per `rules/testing.md` UI requirement) — start dev server, navigate to `/admin/schedules`, confirm toggle + run-now + history render against the API from Step 4.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(scheduler): 7-1 admin schedules UI"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/...`, `backend/tests/integration/...` (mirror module under test, per `rules/folder-structure.md`)
- **Do:** one test per AC above — freezegun time-travel for AC1 (cron fires at scheduled time, disabled stays silent); 2-process spawn test for AC2 (already in Step 2, referenced here); skip+notify+history test for AC3; cron 400 test for AC4 (Step 4); cost-matches-llm_usage test for AC5. Provider/HTTP calls mocked with `respx` per `rules/testing.md`.
- **Verify:** `cd backend && pytest tests/ -k "scheduler or schedule" -v` → all AC-mapped tests pass.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "test(scheduler): 7-1 AC coverage for scheduler service"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + test lock 2-process trong CI (spawn 2 worker); time-travel bằng freezegun cho lịch.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/7-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/7-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
