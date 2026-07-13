# Task 5-8: RunningState component + tích hợp mọi bước

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 1-6, 4-1, 4-7 · **FR:** NFR-1
**State file:** [`state/5-8.json`](state/5-8.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-8-runningstate-component` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

> **Note:** this component is a dependency for 5-6 and 5-7's own Execution Steps (both wire "RunningState integration" as one of their steps) — build it as a genuinely reusable component (`RunningState.tsx` taking a `stepKind`/message-stream prop), not something tailored to one screen, or those tasks will need rework.

## User story
As a Content Creator, I want màn "đang chạy" nhất quán cho mọi bước AI với thông điệp thật và nút huỷ/chạy ngầm, so that tôi luôn biết hệ thống đang làm gì và không bao giờ nhìn spinner câm.

## Why
Phát hiện lớn nhất của design-critique: trạng thái chạy là 50% trải nghiệm nhưng v1 không thiết kế. Component này là "gương mặt" của pipeline.

## Scope
**In:** component theo design-system §3.4: message SSE mới nhất + elapsed + progress (indeterminate khi không % thật) + Chạy ngầm + Huỷ (gọi 4-7); error state phân loại (hết-chain: render danh sách provider+lý do từ AllProvidersFailed; khác: message dịch nghĩa) + Thử lại + chi tiết collapse; tích hợp: mọi Duyệt→bước AI đi qua nó; stepper ●% khi ngầm.
**Out:** API cancel (4-7); notification (7-4).

## Business Rules
1. Chỉ hiện message SSE thật — không bịa %; không % → indeterminate.
2. Error hết-chain: admin thấy link Quản trị › Providers; creator thấy "báo quản trị viên" (đúng vai).
3. Huỷ confirm khi run >30s ("giữ kết quả các bước đã xong").
4. Sub-state "đang huỷ…" cho tới event xác nhận (4-7 BR-1).

## Acceptance Criteria
1. **(happy)** Duyệt Kịch bản → RunningState "Đang tạo phân cảnh…" message thật → tự chuyển editor khi xong.
2. **(biên)** Chạy ngầm → dashboard card ●% → click quay lại đúng màn đúng tiến độ.
3. **(lỗi/BR-2)** AllProvidersFailed → danh sách provider+lý do; đúng nội dung theo vai admin/creator.
4. **(BR-4)** Huỷ → "đang huỷ…" → về trạng thái đã huỷ kèm "chạy tiếp?".
5. **(a11y)** NVDA đọc message cập nhật; reduced-motion không animation pulse.

## Data & API
Consume SSE (1-6) + cancel (4-7). Contract change: không.

## Decisions already locked
- ⏳ Không ước lượng "còn X phút" v1 — chỉ elapsed + message.

## Execution Steps

Work these in order. Update `state/5-8.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: RunningState core component — real SSE message + elapsed + indeterminate progress (BR-1)
- **Files:** `frontend/src/components/workspace/RunningState.tsx`, `frontend/src/lib/sse.ts` (existing SSE client from 1-6), `frontend/tests/unit/components/RunningState.test.tsx`
- **Do:** Component takes an SSE stream + `stepKind` and renders the latest real message verbatim plus elapsed time; **never invent a percentage** — indeterminate spinner/progress bar when no real `%` is present in the event payload (BR-1, this is the core anti-pattern the design-critique flagged — a fabricated % is a defect, not a nice-to-have). `prefers-reduced-motion` disables the pulse animation (AC-5).
- **Verify:** `pnpm --filter frontend vitest run RunningState` → covers real-message-display, no-percent-shows-indeterminate, reduced-motion-disables-pulse cases.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/components/workspace/RunningState.tsx frontend/src/lib/sse.ts frontend/tests/unit/components/RunningState.test.tsx && git commit -m "feat(workspace): 5-8 RunningState core, real SSE message + indeterminate" && git push`

### Step 2: Chạy ngầm (background) + dashboard progress card
- **Files:** `frontend/src/components/workspace/RunningState.tsx` (background toggle), `frontend/src/components/dashboard/ProjectProgressCard.tsx`
- **Do:** "Chạy ngầm" backgrounds the run; the project dashboard shows a live `●%`/indeterminate card that, when clicked, returns the user to the exact screen and progress state (AC-2).
- **Verify:** `pnpm --filter frontend vitest run ProjectProgressCard` → click-through returns to correct screen with live state.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/RunningState.tsx frontend/src/components/dashboard/ProjectProgressCard.tsx && git commit -m "feat(workspace): 5-8 background run + dashboard progress card" && git push`

### Step 3: Error state — chain-exhausted vs generic (BR-2)
- **Files:** `frontend/src/components/workspace/RunningStateError.tsx`, `frontend/tests/unit/components/RunningStateError.test.tsx`
- **Do:** Classify errors: `AllProvidersFailed` renders the list of providers tried + failure reason per provider (role-aware — admin sees a "Quản trị › Providers" link, creator sees "báo quản trị viên", per BR-2); any other error shows a translated/human message with a collapsible technical-detail section. Both offer "Thử lại".
- **Verify:** `pnpm --filter frontend vitest run RunningStateError` → covers AllProvidersFailed-admin-view, AllProvidersFailed-creator-view, generic-error-with-collapse cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/RunningStateError.tsx frontend/tests/unit/components/RunningStateError.test.tsx && git commit -m "feat(workspace): 5-8 error state, chain-exhausted BR-2 role-aware" && git push`

### Step 4: Cancel flow — confirm >30s + "đang huỷ…" sub-state (BR-3, BR-4, consumes 4-7)
- **Files:** `frontend/src/components/workspace/RunningStateCancel.tsx`
- **Do:** Cancel button calls the 4-7 cancel API. If the run has been active >30s, show a confirm dialog warning that already-completed sub-steps' results are kept (BR-3). After confirming, show an "đang huỷ…" sub-state until the 4-7 cancellation-confirmed SSE event arrives (BR-4, matches 4-7 BR-1) — don't optimistically flip to cancelled before the event.
- **Verify:** `pnpm --filter frontend vitest run RunningStateCancel` → covers under-30s-no-confirm, over-30s-confirm-required, cancelling-substate-until-event cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/RunningStateCancel.tsx && git commit -m "feat(workspace): 5-8 cancel flow BR-3/BR-4" && git push`

### Step 5: Integrate into every Duyệt→AI-step transition + stepper background indicator
- **Files:** `frontend/src/components/workspace/PipelineStepper.tsx` (extend from 5-1), integration points across `frontend/src/app/projects/[id]/*/page.tsx`
- **Do:** Wire RunningState as the universal transition UI for every "Duyệt" action that triggers an AI step (research, script, storyboard, etc. per 4-1); when backgrounded, the stepper shows a live `●%`/indeterminate indicator on the running station (AC-2's stepper half).
- **Verify:** `pnpm --filter frontend typecheck` → exit 0; manual dev-server check that approving any step shows RunningState and the stepper reflects background runs.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/PipelineStepper.tsx frontend/src/app/projects && git commit -m "feat(workspace): 5-8 wire RunningState into every approve transition" && git push`

### Step 6: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/components/RunningState*.test.tsx`, `tests/e2e/running-state.spec.ts`, Storybook fixtures for the 4 states (default/loading/error/cancelling) if Storybook is present, else fixture-driven component tests covering the same 4 states
- **Do:** One test per AC-1..AC-5; fixture-driven coverage for the 4 core states (Test Notes requirement). Then **exercise the feature in a real running browser (dev server)**: approve a step, confirm the real SSE message renders and updates, background it, click through from the dashboard card, then trigger a fixture chain-exhaustion error and confirm the role-aware message + retry.
- **Verify:** `pnpm --filter frontend test:e2e -- running-state` → AC-mapped tests pass, includes approve→running→auto-transition flow (AC-1).
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-8 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + Storybook/fixture cho 4 trạng thái component; Playwright flow duyệt→running→auto-chuyển.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-8.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-8.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
