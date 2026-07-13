# Task 8-6: Analytics dashboard

**Points:** 2đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-5 · **FR:** FR-13
**State file:** [`state/8-6.json`](state/8-6.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/8-6-analytics-dashboard` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want dashboard tổng quan hiệu quả video theo thời gian và nền tảng, so that quyết định chủ đề tiếp theo dựa trên con số.

## Why
FR-13 phần hiển thị — vòng lặp học của cả sản phẩm.

## Scope
**In:** màn Analytics: 4 số tổng, chart theo ngày, bảng video (sort CTR/completion/views), filter platform + khoảng ngày; empty state; nút ✎ nhập tay per-row.
**Out:** so sánh A/B chủ đề (v1.1); export CSV (v1.1); per-video detail page.

## Business Rules
1. Metric nền tảng không cung cấp → "—" + tooltip lý do (không hiện 0 gây hiểu sai).
2. Số dashboard khớp DB tuyệt đối (test so khớp seed).
3. Nguồn số liệu (tự động/nhập tay) hiển thị per-row.

## Acceptance Criteria
1. **(happy)** Khớp wireframe; filter platform/ngày đúng; sort bảng đúng.
2. **(biên/BR-1)** TikTok completion → "—" + tooltip "nền tảng không cung cấp qua API".
3. **(BR-2)** Seed biết trước → 4 số tổng khớp query tay.
4. **(empty)** 0 video đăng → empty state + CTA.

## Data & API
Endpoints §8 dashboard/videos. Contract change: không.

## Decisions already locked
- 4 số tổng: Video/Views/Giờ xem/Xem hết + delta so kỳ trước.

## Execution Steps

Work these in order. Update `state/8-6.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit. This task is frontend-heavy — its UI half must be exercised in a real running browser before being marked complete (`rules/testing.md`: "UI/frontend stories require exercising the feature in a real running browser... type-checks and unit tests are necessary, not sufficient").

### Step 1: Dashboard aggregate + video-list API endpoints
- **Files:** `backend/app/api/routes/analytics_dashboard.py` (per §8 api-spec)
- **Do:** implement the dashboard/videos endpoints per `docs/specs/api-spec.md` §8: 4 summary numbers (Video/Views/Giờ xem/Xem hết + delta vs. prior period, per locked decision), platform + date-range filters, video-list sortable by CTR/completion/views; router calls a service function, no aggregation logic in the route (`rules/code-style.md`).
- **Verify:** `pytest backend/tests/integration/api/test_analytics_dashboard.py -q -k "aggregate"` → passes.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/api/routes/analytics_dashboard.py && git commit -m "feat(analytics): 8-6 add dashboard aggregate + video-list endpoints"` → `git push`

### Step 2: Missing-metric handling (BR-1) + source display (BR-3)
- **Files:** `backend/app/services/analytics_dashboard_service.py`
- **Do:** when a platform doesn't provide a given metric via API, return an explicit "not available" marker (never a bare `0`, per BR-1 — a real `0` and "not measured" must never be visually or semantically identical); every row carries its data source (`api`/`manual`) for BR-3 display.
- **Verify:** `pytest backend/tests/unit/services/test_analytics_dashboard_service.py -q -k "missing_metric or source"` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/analytics_dashboard_service.py && git commit -m "feat(analytics): 8-6 add missing-metric marker + source field"` → `git push`

### Step 3: Analytics screen UI — 4 tổng số, chart, table, filters, empty state
- **Files:** frontend under `src/app/analytics/` (or per `rules/folder-structure.md` routing), matching wireframe **Analytics**
- **Do:** 4 summary tiles with delta, daily chart, sortable video table, platform + date-range filters, manual-entry ✎ button per row (opens the 8-5 manual-entry form), states (default/loading skeleton/empty with CTA/error banner/disabled N/A); "—" cells carry an `aria-label` explaining why (A11y, BR-1); chart has a hidden equivalent data table for screen readers.
- **Verify:** exercise in a real running browser (per `rules/testing.md`) — screenshot default, empty, and error states; `npm run typecheck` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add src/app/analytics/... && git commit -m "feat(analytics): 8-6 add Analytics dashboard screen UI"` → `git push`

### Step 4: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/integration/api/test_analytics_dashboard.py`, frontend `vitest` specs under the dashboard component directory, `tests/fixtures/analytics/seed_14x30x2.py`
- **Do:** seed fixture generator for 14 videos × 30 days × 2 platforms (per Test Notes); one test per AC (AC1 happy filter/sort matches wireframe, AC2 BR-1 "—" + tooltip for TikTok completion, AC3 BR-2 seed-known-numbers match a hand-computed query exactly, AC4 empty-state + CTA); vitest for the aggregate display logic.
- **Verify:** `pytest backend/tests/integration/api/test_analytics_dashboard.py -q && npx vitest run src/app/analytics` → all AC-mapped tests pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests/ src/app/analytics/... && git commit -m "test(analytics): 8-6 cover all acceptance criteria"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + seed metrics 14 video × 30 ngày × 2 nền tảng; vitest cho aggregate hiển thị.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/8-6.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/8-6.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
