# Task 1-4: State machine + status_history

**Points:** 5đ · **Epic:** 1 — Nền tảng · **Depends:** 1-3 · **FR:** FR-17
**State file:** [`state/1-4.json`](state/1-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/1-4-state-machine` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a system, I want mọi chuyển trạng thái project đi qua một cổng duy nhất có kiểm tra và audit, so that pipeline resume chính xác sau lỗi và mọi thay đổi truy vết được.

## Why
FR-17 là xương sống độ tin cậy: LangGraph resume (4-1), hàng đợi duyệt (7-5), gate Mode 1 (7-3) đều đọc status. Một chỗ ghi status "chui" là một bug resume tương lai.

## Scope
**In:** ma trận cạnh FR-17 dạng data (một nguồn cho code+test+docs); service `ProjectStateMachine.transition()` (validate cạnh, ghi history actor/reason, phát event `project.status`); `previous_status` cho FAILED/CANCELLED; API `GET status-history`.
**Out:** UI timeline lịch sử (5-9); cạnh CANCELLED chi tiết (4-7 bổ sung, dùng cùng service).

## Business Rules
1. Mọi write `projects.status` ngoài service bị cấm — enforced bằng CI grep + code review.
2. Actor bắt buộc: user uuid | `system` | tên node; reason bắt buộc với cạnh bất thường (→FAILED, override).
3. FAILED/CANCELLED giữ `previous_status`; resume chỉ về đúng trạng thái đó.
4. ARCHIVED đến từ trạng thái kết thúc (PUBLISHED/FAILED/DRAFT/READY); không từ trạng thái đang chạy.
5. Transition idempotent-safe: chuyển tới trạng thái hiện tại → no-op trả 200 (chống double-click), trừ cạnh có side-effect.

## Acceptance Criteria
1. **(happy)** APPROVED→PRODUCING: status đổi + history đủ actor/reason + event phát.
2. **(biên/BR-3)** FAILED từ RENDERING → resume → RENDERING, không về DRAFT.
3. **(lỗi)** PUBLISHED→RESEARCHING → 409 STATE_CONFLICT body chuẩn.
4. **(biên/BR-5)** Gọi 2 lần cùng transition → lần 2 no-op 200, history 1 dòng.
5. **(test)** Parametrize 100% cạnh hợp lệ + đại diện cạnh cấm; CI grep pass.

## Data & API
Bảng: cột `status` + `status_history`. Event: `project.status`. Contract change: không.

## Decisions already locked
- PUBLISHING tách khỏi READY (giữ nguyên FR-17 v3 SRS).

## Execution Steps

Work these in order. Update `state/1-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: FR-17 transition matrix as data
- **Files:** `backend/app/services/state_machine_edges.py`
- **Do:** encode the FR-17 allowed-transition matrix from `docs/SRS.md` FR-17 as a single data structure (e.g. `EDGES: dict[Status, set[Status]]`) that both code and tests import — "một nguồn cho code + test + docs" per Scope. Do not invent an edge not stated in FR-17.
- **Verify:** `cd backend && uv run python -c "from app.services.state_machine_edges import EDGES; assert EDGES"` → exit 0.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/services/state_machine_edges.py && git commit -m "feat(state-machine): 1-4 FR-17 transition matrix as data"` → `git push`

### Step 2: status_history table + ProjectStateMachine.transition()
- **Files:** `backend/app/models/status_history.py`, `backend/alembic/versions/xxxx_status_history.py`, `backend/app/services/state_machine.py`
- **Do:** implement `status_history` per `docs/specs/database-schema.md` §2.2; implement `ProjectStateMachine.transition(project, to_status, actor, reason=None)` as the **only** function allowed to write `projects.status` (BR-1): validates the edge against `EDGES`, requires `actor` (user uuid | `"system"` | node name, BR-2), requires `reason` for abnormal edges (→FAILED, override), preserves `previous_status` for FAILED/CANCELLED (BR-3), and is idempotent-safe — a same-status call is a no-op 200 with no new history row unless the edge has a side effect (BR-5).
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_state_machine.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/models backend/alembic backend/app/services/state_machine.py && git commit -m "feat(state-machine): 1-4 ProjectStateMachine.transition() service"` → `git push`

### Step 3: Event emission stub + CI grep guard (BR-1)
- **Files:** `backend/app/events/project_status.py`, `scripts/check_no_direct_status_write.py`, `.github/workflows/ci.yml`
- **Do:** emit a `project.status` event on every transition (shape per event-catalog envelope) — 1-6 owns the real bus and will swap this stub's transport without changing the call site, per AR-5; add a CI step that greps the codebase for any `.status =` write on the `Project` model outside `backend/app/services/state_machine.py` and fails the build if found (BR-1).
- **Verify:** `python scripts/check_no_direct_status_write.py` → exit 0 on the current tree; introduce a deliberate violation locally, confirm non-zero exit with a clear message naming the offending file, then revert the deliberate violation.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/events scripts .github && git commit -m "chore(ci): 1-4 CI grep guard against direct status writes + project.status event stub"` → `git push`

### Step 4: GET status-history API endpoint
- **Files:** `backend/app/api/projects.py`
- **Do:** implement `GET /projects/{id}/status-history` returning ordered history rows (`actor`, `reason`, `from_status`, `to_status`, `created_at`).
- **Verify:** `curl localhost:8000/projects/{id}/status-history` → 200 with an array.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/projects.py && git commit -m "feat(state-machine): 1-4 GET status-history endpoint"` → `git push`

### Step 5: Wire up tests — parametrized edges + property test + all Acceptance Criteria
- **Files:** `backend/tests/unit/test_state_machine.py`, `backend/tests/property/test_state_machine_random_walk.py`
- **Do:** parametrize 100% of valid edges from `EDGES` plus representative forbidden edges (AC-5); property test doing a random walk that only takes valid edges and never raises (per Test Notes); explicit tests for AC-1 (APPROVED→PRODUCING happy path with history+event), AC-2 (FAILED-from-RENDERING resumes to RENDERING, BR-3), AC-3 (PUBLISHED→RESEARCHING → 409 STATE_CONFLICT body), AC-4 (calling the same transition twice → 2nd call no-op 200, 1 history row); export the edge matrix to a table (markdown/CSV) in the PR per Test Notes so PO/BA can review it once.
- **Verify:** `cd backend && uv run pytest tests/ -v` → all pass, including the property test.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests && git commit -m "test(state-machine): 1-4 tests covering AC 1-5 + edge matrix export"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + ma trận cạnh export ra bảng trong PR; property test (random walk chỉ đi cạnh hợp lệ không bao giờ raise).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/1-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/1-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
