# Task 4-7: Điều khiển run — huỷ / chạy ngầm / resume

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-1 · **FR:** NFR-3
**State file:** [`state/4-7.json`](state/4-7.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-7-dieu-khien-run-huy-ngam-resume` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want huỷ một bước AI đang chạy hoặc để nó chạy ngầm, so that tôi không bị giam trong màn chờ khi đổi ý hoặc muốn làm việc khác.

## Why
Gap từ design-critique: RunningState có nút Huỷ nhưng không API nào đứng sau. Không có task này, cách duy nhất dừng một run sai là chờ nó chạy hết.

## Scope
**In:** `POST runs/{id}/cancel`; abort an toàn (kết thúc sau LLM call hiện tại — không giết giữa transaction 4-1 BR-3); cạnh state machine RUNNING→CANCELLED (+previous_status); resume sau cancel = run mới từ checkpoint; "chạy ngầm" = FE rời màn (SSE sẵn — không API mới).
**Out:** pause/resume giữa node (checkpoint đủ); huỷ hàng loạt.

## Business Rules
1. Cancel best-effort có xác nhận: trạng thái CANCELLED chỉ khi node dừng thật (event xác nhận); UI hiện "đang huỷ…" trong lúc chờ (tối đa ~30s = 1 LLM call).
2. Chi phí đã phát sinh vẫn ghi usage.
3. Cancel không xoá version đã tạo trước đó.
4. Cancel run đã kết thúc → 409.

## Acceptance Criteria
1. **(happy)** Cancel giữa research → "đang huỷ…" → CANCELLED ≤30s; resume → run mới tiếp từ checkpoint.
2. **(biên)** Cancel đúng lúc node vừa xong → run kết thúc bình thường tại interrupt (không race).
3. **(lỗi/BR-4)** Cancel run xong → 409.
4. **(UI)** Rời màn khi chạy → dashboard card ●%; quay lại đúng RunningState; sau cancel card hiện "Đã huỷ — chạy tiếp?".

## Data & API
Cạnh mới state machine (cập nhật ma trận 1-4 + test); endpoint mới → cập nhật api-spec §2. Event mới: `run.cancelled` → cập nhật event-catalog.

## Decisions already locked
- ⏳ Không hard-kill LLM call đang bay (chờ xong call hiện tại) — đơn giản, an toàn transaction.

## Execution Steps

Work these in order. Update `state/4-7.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: RUNNING→CANCELLED state machine edge (+previous_status)
- **Files:** `backend/app/services/state_machine.py` (extends 1-4's matrix), `backend/tests/unit/state_machine/test_transitions.py`
- **Do:** add the `RUNNING → CANCELLED` edge to the 1-4 state matrix, preserving `previous_status` the same way the existing FAILED transition does (mirrors 4-1 BR-4's pattern). Update the matrix test.
- **Verify:** unit test: RUNNING→CANCELLED transition valid, `previous_status` preserved; invalid transitions still rejected.
- **On failure:** transient → retry 3x; logic/config → `systematic-debugging` skill; still failing → block task, log in `memory/project-memory.md`.
- **Commit:** `git add backend/app/services/state_machine.py backend/tests/unit/state_machine/ && git commit -m "feat(runs): 4-7 add RUNNING->CANCELLED state machine edge" && git push`

### Step 2: POST runs/{id}/cancel — best-effort abort after current node (BR-1, BR-4)
- **Files:** `backend/app/api/routes/runs.py`, `backend/app/services/run_service.py`
- **Do:** implement cancel: mark run "cancelling" immediately, but only transition to `CANCELLED` once the currently-executing node genuinely stops (event-confirmed) — never kill mid-transaction (respects 4-1 BR-3's atomic checkpoint+step_version write; per "Decisions already locked" this waits out the current LLM call, up to ~30s). Cancel on an already-finished run → 409 (BR-4).
- **Verify:** integration test: cancel mid-node → status is "cancelling" then `CANCELLED` within ~30s bound, without interrupting the atomic write from 4-1 Step 4. Second test: cancel a finished run → 409 (AC3).
- **On failure:** same policy as Step 1.
- **Commit:** `4-7 cancel endpoint + best-effort abort-after-current-node`.

### Step 3: Cost/usage preserved, versions preserved (BR-2, BR-3)
- **Files:** `backend/app/services/run_service.py`
- **Do:** ensure cancel never rolls back already-recorded `llm_usage` rows (BR-2) or already-created step versions (BR-3) — cancel only stops forward progress, it's not a rollback.
- **Verify:** unit test: cancel after 2 nodes completed → both nodes' usage rows and versions remain queryable post-cancel.
- **On failure:** same policy as Step 1.
- **Commit:** `4-7 preserve usage + versions across cancel`.

### Step 4: run.cancelled event + event-catalog update
- **Files:** `backend/app/events/run_events.py`, `docs/specs/event-catalog.md`
- **Do:** emit a new `run.cancelled` event through the existing 1-6 event bus/SSE — this is a contract change, update `docs/specs/event-catalog.md` in the same PR per `rules/documentation.md`.
- **Verify:** integration test: cancel flow emits `run.cancelled` with `run_id`/`correlation_id`; event-catalog diff present.
- **On failure:** same policy as Step 1.
- **Commit:** `4-7 run.cancelled event + event-catalog contract update`.

### Step 5: Resume-after-cancel = new run from checkpoint
- **Files:** `backend/app/services/run_service.py`
- **Do:** starting a new run on a cancelled project resumes from the last good checkpoint (reuses 4-1's checkpoint/resume mechanics — no new resume logic, just confirm the existing `POST steps/{step}/run` path picks up from the checkpoint after a CANCELLED state).
- **Verify:** integration test: cancel run → POST new run → resumes from the last completed node's checkpoint, doesn't re-run completed nodes (AC1).
- **On failure:** same policy as Step 1.
- **Commit:** `4-7 resume-after-cancel via existing checkpoint path`.

### Step 6: Race test — cancel vs node-finish (AC2)
- **Files:** `backend/tests/integration/pipeline/test_cancel_race.py`
- **Do:** simulate cancel arriving at the exact moment a node finishes — must resolve deterministically to either a normal finish-at-interrupt or a clean CANCELLED, never a corrupted/ambiguous state. Per DoD, this test runs 20x in CI as a flaky-hunter.
- **Verify:** `pytest backend/tests/integration/pipeline/test_cancel_race.py --count=20` (or project's repeat-test mechanism) → all 20 runs pass deterministically.
- **On failure:** any flake here is non-transient by nature (race condition) → `systematic-debugging` skill, not blind retry.
- **Commit:** `4-7 cancel-vs-node-finish race test (20x repeat)`.

### Step 7: Dashboard/RunningState UI wiring (AC4)
- **Files:** frontend component under `src/app/projects/[id]/...` (RunningState from 5-8, dashboard card)
- **Do:** wire the Cancel button (already present per the design-critique gap this task closes) to the new endpoint; leaving the screen while running shows a live-% dashboard card; returning lands back on RunningState; post-cancel the card reads "Đã huỷ — chạy tiếp?".
- **Verify:** exercise in a real running browser per `rules/testing.md` UI rule.
- **On failure:** same policy as Step 1.
- **Commit:** `4-7 wire cancel button + dashboard running-state card`.

### Step 8: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/services/test_run_service.py`, `backend/tests/integration/pipeline/test_run_cancel.py`
- **Do:** one test per Acceptance Criterion not already covered by Steps 2/6.
- **Verify:** `pytest backend/tests/unit/services/test_run_service.py backend/tests/integration/pipeline/test_run_cancel.py backend/tests/integration/pipeline/test_cancel_race.py` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** `4-7 complete AC test coverage`.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + race test (cancel vs node-finish) chạy lặp 20 lần trong CI (flaky-hunter).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-7.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-7.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
