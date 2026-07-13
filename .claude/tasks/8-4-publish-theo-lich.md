# Task 8-4: Publish theo lịch

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-3, 7-1 · **FR:** FR-12
**State file:** [`state/8-4.json`](state/8-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/8-4-publish-theo-lich` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want hẹn giờ đăng video vào khung giờ vàng, so that video ra đúng lúc khán giả online mà tôi không phải thức canh.

## Why
FR-12 scheduler + đường auto-publish của Mode 1 (7-3) đi qua đây — một cơ chế duy nhất cho cả hẹn tay lẫn tự động.

## Scope
**In:** scheduled_at → job type publish (7-1); datetime picker timezone VN; huỷ trước giờ; trạng thái "đã lên lịch 20:00" trên card + tab; Mode 1 auto-publish dùng đường này.
**Out:** gợi ý giờ vàng bằng analytics (v1.1); đăng lặp lại.

## Business Rules
1. Giờ quá khứ → chặn nhập (client + server).
2. Huỷ chỉ khi chưa bắt đầu uploading.
3. Job đăng fail → notify + giữ record scheduled để đặt lại — không lặng lẽ bỏ.
4. Timezone hiển thị/nhập là Asia/Ho_Chi_Minh; lưu UTC.

## Acceptance Criteria
1. **(happy)** Hẹn 20:00 → đăng ±2'; trạng thái chuyển đúng chuỗi.
2. **(biên/BR-2)** Huỷ 19:59 → không đăng; huỷ lúc uploading → 409 giải thích.
3. **(biên)** 2 nền tảng 2 giờ → 2 job độc lập chạy đúng.
4. **(lỗi/BR-3)** Fail lúc chạy → notify + nút đặt lại hoạt động.
5. **(BR-4)** Nhập 20:00 VN → DB UTC đúng; hiển thị lại đúng VN.

## Data & API
publishes.scheduled_at; job scheduler 7-1. Contract change: không.

## Decisions already locked
- ⏳ Không giới hạn số lịch chờ.

## Execution Steps

Work these in order. Update `state/8-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: `publish` job type on the 7-1 scheduler
- **Files:** `backend/app/pipeline/jobs/publish_job.py`, registration in the 7-1 job scheduler
- **Do:** register a `publish` job type that reads `publishes.scheduled_at`, invokes `publish_service` (8-1) at fire time; store/interpret timestamps as UTC in the DB (BR-4), converting from Asia/Ho_Chi_Minh only at the input/display boundary.
- **Verify:** `mypy backend/app/pipeline/jobs/publish_job.py --strict` → 0 errors.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/pipeline/jobs/publish_job.py && git commit -m "feat(publish): 8-4 add publish job type on scheduler"` → `git push`

### Step 2: Client + server past-time guard (BR-1) and cancel rule (BR-2)
- **Files:** `backend/app/services/publish_schedule_service.py`, frontend datetime picker component
- **Do:** server rejects `scheduled_at` in the past (validated against server clock, not client-supplied "now"); client-side picker blocks past times too (defense in depth, server is authoritative); cancel endpoint allowed only while status is not yet `uploading` — attempting to cancel while `uploading` returns 409 with an explanation (BR-2, AC2).
- **Verify:** `pytest backend/tests/unit/services/test_publish_schedule_service.py -q -k "past_time or cancel"` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/publish_schedule_service.py src/... && git commit -m "feat(publish): 8-4 add past-time guard + cancel rule"` → `git push`

### Step 3: Failure handling (BR-3) — keep record scheduled, don't silently drop
- **Files:** `backend/app/pipeline/jobs/publish_job.py`, `backend/app/services/publish_schedule_service.py`
- **Do:** on job failure at fire time, emit a notify event and leave the `publishes` record in a state that supports re-scheduling ("đặt lại") rather than silently discarding it (BR-3) — per `rules/error-handling.md`, never swallow the exception to make the job "green".
- **Verify:** `pytest backend/tests/unit/services/test_publish_schedule_service.py -q -k "fail_notify"` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/pipeline/jobs/publish_job.py backend/app/services/publish_schedule_service.py && git commit -m "feat(publish): 8-4 add fail-notify-and-reset flow"` → `git push`

### Step 4: Mode 1 auto-publish wiring (7-3) through this same path
- **Files:** `backend/app/pipeline/nodes/mode1_publish.py` (or existing Mode 1 auto-publish integration point)
- **Do:** point Mode 1's auto-publish step at this same `publish` job/scheduler path instead of a separate mechanism — one code path for manual and automatic scheduling, per the "Why" section.
- **Verify:** `pytest backend/tests/integration/pipeline/test_mode1_autopublish.py -q` → passes (mocked pipeline run confirming the job type dispatched matches this task's).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/pipeline/nodes/mode1_publish.py && git commit -m "feat(publish): 8-4 wire Mode 1 auto-publish through scheduler"` → `git push`

### Step 5: Xuất bản schedule block UI
- **Files:** frontend under `src/app/projects/[id]/` (publish tab), matching wireframe **Xuất bản hẹn giờ**
- **Do:** states: chưa hẹn · đã hẹn (countdown + cancel button) · đang đăng (cancel disabled, BR-2) · lỗi (BR-3 + "đặt lại" button); datetime picker in Asia/Ho_Chi_Minh, submits/reads UTC via the API; card/tab shows "đã lên lịch 20:00" per the wireframe.
- **Verify:** exercise in a real running browser (per `rules/testing.md`) — screenshot each state; `npm run typecheck` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add src/app/... && git commit -m "feat(publish): 8-4 add schedule block UI"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/services/test_publish_schedule_service.py`, `backend/tests/integration/pipeline/test_publish_scheduling.py`
- **Do:** use `freezegun` for time control (per Test Notes); one test per AC (AC1 happy schedule-and-fire-within-±2min, AC2 BR-2 cancel-before-vs-during-upload, AC3 two-independent-jobs-two-platforms, AC4 BR-3 fail-then-reschedule, AC5 BR-4 VN-input-to-UTC-storage-and-back).
- **Verify:** `pytest backend/tests/unit/services/test_publish_schedule_service.py backend/tests/integration/pipeline/test_publish_scheduling.py -q` → all AC-mapped tests pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests/ && git commit -m "test(publish): 8-4 cover all acceptance criteria"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + freezegun cho giờ; test UTC conversion (DST không cần — VN không DST).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/8-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/8-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
