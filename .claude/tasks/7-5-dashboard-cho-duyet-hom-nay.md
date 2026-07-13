# Task 7-5: Dashboard "Chờ duyệt hôm nay" + duyệt nhanh

**Points:** 3đ · **Epic:** 7 — Automation · **Depends:** 7-2, 8-3, 6-3 · **FR:** Mode 1, FR-01
**State file:** [`state/7-5.json`](state/7-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/7-5-dashboard-cho-duyet-hom-nay` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.
>
> **Frontend/UI task — real-browser rule applies** (`rules/testing.md`): type-checks and unit tests are necessary but not sufficient here; the mobile viewport AC (AC3) must be exercised in an actual running browser (Playwright), not just asserted via component snapshot.
>
> **Gate note:** "Duyệt & đăng" is a real publish trigger, not a UI convenience — it must go through the same `MODE1_AUTOPUBLISH`/verdict enforcement as any other publish path (BR-1: only shown when `PASS` + platform active), so this task never becomes a second, looser path around the 7-3 gate.

## User story
As a PO, I want hàng đợi video chờ duyệt ngay đầu dashboard với nút duyệt-và-đăng 1 click, so that 2 phút mỗi sáng — kể cả từ điện thoại — xử lý xong tin hàng ngày.

## Why
Gap từ wireframe v2. Màn ROI cao nhất của Mode 1: toàn bộ giá trị "tự động 95%" quy về 1 cú click cuối cùng của con người. Yêu cầu mobile là ngoại lệ cố ý của chiến lược desktop-first.

## Scope
**In:** khối queue card (READY mode daily_news + mọi NEED_REVIEW): xem video inline (modal player), "✓ Duyệt & đăng" (READY+PASS+platform active → publish theo config), "Mở duyệt" (deep-link đúng tab); sort cũ nhất trước; badge đếm trên sidebar; **responsive <1024px cho riêng màn này**.
**Out:** duyệt hàng loạt; push notification (7-4 lo).

## Business Rules
1. "Duyệt & đăng" chỉ hiện khi PASS + platform active; ngược lại chỉ "Mở duyệt".
2. Duyệt nhanh ghi audit như duyệt thường (actor, thời điểm) + tính vào thống kê 7-3.
3. Queue rỗng → khối ẩn hẳn (không chiếm chỗ).
4. Card hiện verdict + tiêu đề + thời lượng + thumbnail — đủ ra quyết định không cần mở.

## Acceptance Criteria
1. **(happy)** Sáng 2 video → khối 2 card đủ thông tin BR-4; "Duyệt & đăng" → publish chạy → card biến mất + toast.
2. **(biên/BR-1)** Video WARN → chỉ "Mở duyệt"; deep-link tới claim đang chờ.
3. **(mobile)** 390px: xem video + duyệt được (Playwright viewport); từ link Telegram (7-4) → màn này mở đúng.
4. **(quyền)** Creator thấy queue project mình; admin thấy tất.
5. **(BR-2)** Duyệt nhanh → audit + accuracy_event ghi đúng.

## Data & API
Endpoint: `GET /projects/review-queue` (mới — tổng hợp 2 nguồn + verdict + next_action) → cập nhật api-spec §2; publish dùng §8. Contract change: **có**.

## Decisions already locked
- ⏳ Duyệt nhanh không cho sửa metadata (muốn sửa → "Mở duyệt").

## Execution Steps

Work these in order. Update `state/7-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: `GET /projects/review-queue` endpoint (contract change)
- **Files:** `backend/app/api/projects.py` (extend), `backend/app/schemas/project.py`, `docs/specs/api-spec.md` §2 (update in same PR)
- **Do:** aggregate READY-mode-`daily_news` projects + all `NEED_REVIEW` projects into one queue response, each item carrying verdict, title, duration, thumbnail (enough for BR-4's "decide without opening"), and `next_action` (publish-eligible vs open-only per BR-1), sorted oldest-first. No business logic in the router — service function does the aggregation (`rules/code-style.md`). Update `docs/specs/api-spec.md` §2 and note the change in the PR's **Contract changes** section.
- **Verify:** `cd backend && pytest backend/tests/unit/api/test_review_queue.py -v` → fixture with PASS/WARN/FAILED projects returns correctly shaped, correctly sorted queue; permission-scoped (creator sees own projects, admin sees all — AC "quyền"). 
- **On failure:** transient → retry 3×; scope/permission logic bug → `systematic-debugging` skill; still failing → `blocked`.
- **Commit:** `git add backend/app/api/projects.py backend/app/schemas/project.py docs/specs/api-spec.md && git commit -m "feat(dashboard): 7-5 review-queue endpoint (contract change)"` → `git push`

### Step 2: Queue card component + empty/loading/error states
- **Files:** `frontend/src/components/dashboard/ReviewQueueBlock.tsx`, `frontend/src/components/dashboard/ReviewQueueCard.tsx`
- **Do:** card shows verdict + title + duration + thumbnail (BR-4); modal inline video player; block renders default/loading-skeleton/empty(hidden entirely per BR-3)/error-banner states; API types generated via `make gen-api-client`, no hand-written duplicate types.
- **Verify:** exercise in a real running browser — dev server, dashboard route, confirm all 4 states render against fixture data from Step 1.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(dashboard): 7-5 review queue card block + states"` → `git push`

### Step 3: "Duyệt & đăng" action wired to gate-enforced publish
- **Files:** `frontend/src/components/dashboard/ReviewQueueCard.tsx` (extend), backend reuses the Step 4 publish path from 7-3 (no new publish logic here)
- **Do:** button shown only when `PASS` + platform active (BR-1); on click, calls the existing publish endpoint (§8, gate-enforced by 7-3 — this task does not add a second publish trigger); on success, card disappears from queue + toast shown; audit + `accuracy_events` write happens server-side identically to a normal approval (BR-2, reuse 7-3's accuracy-tracking hook, don't duplicate it here). "Mở duyệt" always available as a deep-link to the full review tab (for WARN or anyone wanting to edit metadata — quick-approve intentionally does not allow metadata edits per "Decisions already locked").
- **Verify:** `cd backend && pytest backend/tests/integration/test_review_queue_publish.py -v` → PASS+active → publish succeeds, audit + accuracy_event rows written (AC5); WARN → only "Mở duyệt" shown, no publish button (AC2).
- **On failure:** if this step is tempted to add a shortcut that bypasses 7-3's gate check, stop — that's the non-negotiable-gate violation flagged in the header note; escalate instead of implementing a bypass.
- **Commit:** `git commit -m "feat(dashboard): 7-5 quick-approve action via gate-enforced publish"` → `git push`

### Step 4: Sidebar badge count
- **Files:** `frontend/src/components/layout/Sidebar.tsx` (extend)
- **Do:** badge showing queue count, sourced from the Step 1 endpoint (or a lightweight count variant if full payload is too heavy for a sidebar poll — reasonable, locally-scoped judgment call per `rules/autonomy-policy.md`, record the choice in `state/7-5.json` `decisions[]`).
- **Verify:** exercise in a real running browser — badge count matches queue length, updates after a quick-approve removes a card.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(dashboard): 7-5 sidebar review-queue badge"` → `git push`

### Step 5: Mobile responsive (<1024px) for this screen only
- **Files:** `frontend/src/components/dashboard/ReviewQueueBlock.tsx`, `ReviewQueueCard.tsx` (styling pass)
- **Do:** per Scope, responsiveness is scoped to this screen only (an intentional exception to desktop-first strategy — don't generalize it to other dashboard blocks). Touch targets ≥44px, player modal full-width on mobile, verified down to 390px.
- **Verify:** Playwright mobile viewport test (390px) — this is a hard AC per Test Notes, not optional: view video + approve action both usable at 390px.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(dashboard): 7-5 mobile responsive review queue (<1024px)"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `frontend/tests/e2e/review-queue.spec.ts` (Playwright), `backend/tests/unit/...`, `backend/tests/integration/...`
- **Do:** one test per AC — happy path 2-card queue + approve-and-publish (AC1), WARN deep-link (AC2), 390px mobile Playwright incl. simulated Telegram-link entry point (AC3, cross-reference 7-4's deep-link shape), permission scoping (AC4, from Step 1), quick-approve audit/accuracy_event (AC5, from Step 3). Fixture queue with 3 states (PASS/WARN/FAILED) per Test Notes.
- **Verify:** `cd frontend && npx playwright test review-queue` and `cd backend && pytest tests/ -k review_queue -v` → all AC-mapped tests pass.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "test(dashboard): 7-5 full AC coverage incl. Playwright mobile"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + Playwright mobile viewport là AC cứng; fixture queue 3 trạng thái (PASS/WARN/FAILED).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/7-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/7-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
