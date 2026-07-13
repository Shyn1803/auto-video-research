# Task 3-5: Cost tracking + daily cap + màn Providers

**Points:** 2đ · **Epic:** 3 — Provider framework · **Depends:** 3-3, 3-4 · **FR:** FR-18, FR-21
**State file:** [`state/3-5.json`](state/3-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/3-5-cost-tracking-daily-cap-man-providers` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As an Admin, I want một màn nhìn thấy hệ thống đang chạy bằng provider nào và tốn bao nhiêu, so that tôi kiểm soát chi phí bằng số liệu thay vì phỏng đoán.

## Why
Màn "niềm tin" của FR-21 — startup validation hiện hình. Daily cap là hàng rào cuối chống hoá đơn bất ngờ.

## Scope
**In:** llm_usage partition tháng; check cap trước call; vượt → pause pipeline + event `cost.cap_reached` + notify; tab Quản trị › Providers (ma trận StatusBadge + lý do inactive 3 loại, nút health-check, cost hôm nay/cap); API `/admin/costs?group_by=`.
**Out:** Grafana chart sâu (9-5); thống kê gate Mode 1 (7-3 — cùng màn, khối riêng).

## Business Rules
1. cap=0 nghĩa "chỉ free" (tương đương ALLOW_PAID=false runtime).
2. Chạm cap giữa run → dừng ở ranh giới node kế (không giết giữa node); status FAILED(reason=cost_cap); resume thủ công sau xử lý.
3. Ma trận phân biệt 3 lý do inactive: "thiếu key" / "kiểm tra thất bại" / "bị chặn trả phí".
4. Cost hiển thị = ước tính từ bảng giá — ghi rõ "ước tính" trên UI.

## Acceptance Criteria
1. **(happy)** 3 kịch bản env (0 key / free keys / full) → ma trận đúng từng nhãn.
2. **(biên/BR-2)** Cap chạm giữa run → dừng sau node hiện tại; resume sau reset chạy tiếp.
3. **(lỗi/BR-3)** Provider health fail → nhãn "kiểm tra thất bại"; service sống lại + bấm kiểm tra → ✓ ngay.
4. **(số liệu)** `group_by=task` khớp tổng llm_usage seed.

## Data & API
Bảng: llm_usage (partition). Endpoints: `/admin/providers`, `/admin/providers/{n}/health-check`, `/admin/costs`. Contract change: không.

## Decisions already locked
- `DAILY_COST_CAP` mặc định 0 (chỉ free) — an toàn nhất cho giai đoạn test.

## Execution Steps

Work these in order. Update `state/3-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: `llm_usage` table partitioned by month
- **Files:** `backend/app/models/llm_usage.py`, `backend/alembic/versions/{ts}_add_llm_usage_partitioned.py`
- **Do:** Create `llm_usage` matching `docs/specs/database-schema.md` §2.7, partitioned by month from the first migration (per [rules/performance.md](../rules/performance.md) — "high-volume tables partitioned by month from the first migration, not retrofitted later"). Columns snake_case, matches schema exactly.
- **Verify:** `alembic upgrade head` against test DB → partitioned table exists; insert rows spanning 2 months → each lands in the correct partition.
- **On failure:** transient (DB) → retry 3×; logic error → `systematic-debugging` skill; still failing → mark step/task `blocked`, log in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/models/llm_usage.py backend/alembic/ && git commit -m "feat(costs): 3-5 llm_usage table partitioned by month" && git push`

### Step 2: Daily cap check before each call + `cost.cap_reached` event (BR-1, BR-2)
- **Files:** `backend/app/core/router.py`, `backend/app/events/cost.py`
- **Do:** Before each provider call, the router (3-2) checks today's accumulated cost against `DAILY_COST_CAP` (default 0 = "chỉ free", BR-1). On breach mid-run: do not kill the in-flight node — stop at the next node boundary (BR-2), set pipeline status `FAILED(reason=cost_cap)`, emit `cost.cap_reached` event + trigger notify. Resume is manual after the cap issue is addressed (BR-2 — no auto-resume).
- **Verify:** unit test: cap set low, calls accumulate past it mid-run → current node completes, next node does not start, status becomes `FAILED(reason=cost_cap)`, event fired once (AC2).
- **On failure:** same policy.
- **Commit:** `git add backend/app/core/router.py backend/app/events/cost.py && git commit -m "feat(costs): 3-5 daily cap check + node-boundary stop + cost.cap_reached event" && git push`

### Step 3: `/admin/providers` endpoint — 3-reason inactive matrix (BR-3)
- **Files:** `backend/app/api/admin/providers.py`, `backend/app/services/provider_status_service.py`
- **Do:** Endpoint returns, per capability × provider, a `StatusBadge`-ready state distinguishing exactly 3 inactive reasons — "thiếu key" / "kiểm tra thất bại" / "bị chặn trả phí" (BR-3) — plus active state. Reuses router availability logic from 3-2 rather than re-deriving it.
- **Verify:** unit test with 3 env scenarios (0 key / free keys only / full keys+paid) → matrix labels match exactly (AC1).
- **On failure:** same policy.
- **Commit:** `git add backend/app/api/admin/providers.py backend/app/services/provider_status_service.py && git commit -m "feat(costs): 3-5 /admin/providers endpoint with 3-reason inactive matrix" && git push`

### Step 4: `/admin/providers/{n}/health-check` endpoint
- **Files:** `backend/app/api/admin/providers.py`
- **Do:** On-demand health-check endpoint delegating to 3-2's on-demand health-check function; on failure shows "kiểm tra thất bại" (BR-3); once the service recovers, a fresh check call must reflect ✓ immediately (AC3), no stale caching bypass for manual checks.
- **Verify:** integration test: mock provider failing → health-check shows failed label; mock recovers → manual health-check call flips to ✓ immediately.
- **On failure:** same policy.
- **Commit:** `git add backend/app/api/admin/providers.py && git commit -m "feat(costs): 3-5 on-demand health-check endpoint" && git push`

### Step 5: `/admin/costs?group_by=` endpoint
- **Files:** `backend/app/api/admin/costs.py`, `backend/app/services/cost_service.py`
- **Do:** Query `llm_usage` grouped by the requested dimension (`task`, `provider`, etc.), returning cost labeled as an estimate (BR-4 — "cost hiển thị = ước tính từ bảng giá, ghi rõ 'ước tính' trên UI" is a backend+frontend contract: backend marks the value as an estimate in the response).
- **Verify:** unit test seeding `llm_usage` (3 days × 3 providers × 3 tasks per Test Notes) → `group_by=task` totals match the seeded sums exactly (AC4).
- **On failure:** same policy.
- **Commit:** `git add backend/app/api/admin/costs.py backend/app/services/cost_service.py && git commit -m "feat(costs): 3-5 /admin/costs endpoint with group_by" && git push`

### Step 6: Admin › Providers tab UI
- **Files:** `frontend/src/app/admin/providers/page.tsx`, `frontend/src/components/admin/ProvidersMatrix.tsx`
- **Do:** Implement per wireframe **Quản trị › Providers**: default matrix (StatusBadge + 3 inactive reasons + health-check button + cost today/cap), loading, error (health-check API fails → keep old data + "chưa cập nhật" label, per Scope UI/UX). A11y: badge shows text, not color-only (design-system §2.1, per Scope note). "Ước tính" label visible on cost figures (BR-4).
- **Verify:** exercise in a real running browser per [rules/testing.md](../rules/testing.md) — confirm matrix renders all 3 env scenarios and the error state.
- **On failure:** same policy.
- **Commit:** `git add frontend/src/app/admin/providers/ frontend/src/components/admin/ProvidersMatrix.tsx && git commit -m "feat(costs): 3-5 Admin Providers tab UI" && git push`

### Step 7: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/services/test_cost_service.py`, `backend/tests/integration/test_admin_costs_api.py`
- **Do:** Seed `llm_usage` 3 days × 3 providers × 3 tasks (per Test Notes/DoD) for the group_by comparison test; one test per remaining AC (1, 2, 3).
- **Verify:** `pytest backend/tests/unit/services/test_cost_service.py backend/tests/integration/test_admin_costs_api.py -v` → all AC-mapped tests pass, seeded totals match `group_by=task` output exactly.
- **On failure:** same policy as above.
- **Commit:** `git add backend/tests/unit/services/test_cost_service.py backend/tests/integration/test_admin_costs_api.py && git commit -m "test(costs): 3-5 full AC coverage + seeded usage comparison test" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + seed llm_usage 3 ngày × 3 provider × 3 task cho test costs. Note: cap drill là mục Release Checklist (10-5), task này chỉ cần test tự động.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/3-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/3-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
