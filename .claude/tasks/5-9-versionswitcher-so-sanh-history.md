# Task 5-9: VersionSwitcher + màn So sánh/History

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 1-5, 5-1 · **FR:** SRS §6
**State file:** [`state/5-9.json`](state/5-9.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-9-versionswitcher-so-sanh-history` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want xem, so sánh, khôi phục phiên bản ngay tại bước đang đứng, so that thử nghiệm nội dung thoải mái và quay lại trong 2 cú click.

## Why
Critique v1: History tách rời ngữ cảnh khiến versioning "có mà như không". Task này biến engine 1-5 thành giá trị nhìn thấy được.

## Scope
**In:** dropdown `v3 ▾` topbar (list: thời gian/tác giả/badge stale+tooltip); Xem (readonly overlay); So sánh với hiện hành (màn diff side-by-side text; scene-diff list added/removed/changed); Khôi phục (confirm hệ quả — dùng service 1-5); History tổng (route phụ bảng mọi bước).
**Out:** visual diff 2 preview (v1.1); so sánh chéo step (cấm).

## Business Rules
1. Khôi phục từ switcher = service 1-5 duy nhất (một đường).
2. Đang có thay đổi chưa autosave → chuyển version hoãn tới lưu xong (≤1.5s), không mất chữ.
3. Badge stale tooltip nêu nguồn gốc.
4. Diff hiển thị thêm/xoá bằng prefix + màu (không chỉ màu — a11y).

## Acceptance Criteria
1. **(happy)** So sánh script v1↔v2 → highlight đúng dòng; đóng quay về đúng chỗ.
2. **(biên)** Khôi phục scene_set v2 → confirm "Hoàn thiện sẽ lỗi thời" → trạm sau chuyển stale trên stepper.
3. **(biên/BR-2)** Đang gõ → chuyển version → hoãn lưu xong mới chuyển, không mất chữ.
4. **(empty)** Bước 1 version → dropdown thông báo đúng, không lỗi.
5. **(quyền)** Project RUNNING → nút khôi phục disabled + tooltip.

## Data & API
Endpoints versions/compare/restore (§3 — 1-5 đã chuẩn `staled_steps`). Contract change: không.

## Decisions already locked
- ⏳ History tổng giữ (route phụ, ít dùng) — giá trị audit; không đầu tư UI đẹp cho nó v1.

## Execution Steps

Work these in order. Update `state/5-9.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: VersionSwitcher dropdown — topbar `v3 ▾`
- **Files:** `frontend/src/components/workspace/VersionSwitcher.tsx` (extends 5-1's topbar), `frontend/tests/unit/components/VersionSwitcher.test.tsx`
- **Do:** Dropdown listing versions with timestamp, author, and a stale badge + tooltip explaining the staleness source (BR-3) when applicable. Empty-state: a step with only 1 version shows an appropriate "chỉ có 1 phiên bản" message, not an empty/broken dropdown (AC-4).
- **Verify:** `pnpm --filter frontend vitest run VersionSwitcher` → covers list-rendering, stale-badge-tooltip, single-version-empty-state cases.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/components/workspace/VersionSwitcher.tsx frontend/tests/unit/components/VersionSwitcher.test.tsx && git commit -m "feat(workspace): 5-9 VersionSwitcher dropdown" && git push`

### Step 2: Xem (readonly overlay)
- **Files:** `frontend/src/components/workspace/VersionViewOverlay.tsx`
- **Do:** Selecting "Xem" on a past version renders a readonly overlay of that version's content without leaving the current screen/route.
- **Verify:** `pnpm --filter frontend vitest run VersionViewOverlay` → overlay renders readonly, current editable state untouched underneath.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/VersionViewOverlay.tsx && git commit -m "feat(workspace): 5-9 readonly version view overlay" && git push`

### Step 3: So sánh (diff) — text side-by-side + scene-diff list (BR-4)
- **Files:** `frontend/src/components/workspace/VersionCompare.tsx`, `frontend/src/lib/diff/textDiff.ts`, `frontend/src/lib/diff/sceneDiff.ts`
- **Do:** Text-content versions diff side-by-side; `scene_set` versions render as an added/removed/changed list. Additions/removals must be marked with a **prefix (+/-) plus color**, not color alone (BR-4, a11y). Closing the compare view returns focus to exactly where the user opened it from (AC-1).
- **Verify:** `pnpm --filter frontend vitest run VersionCompare` → covers text-diff-highlight-correct-lines, scene-diff-added-removed-changed, prefix-not-color-only, close-restores-focus cases (AC-1).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/VersionCompare.tsx frontend/src/lib/diff && git commit -m "feat(workspace): 5-9 version compare, text+scene diff BR-4" && git push`

### Step 4: Khôi phục (restore) via the single 1-5 service + stale cascade (BR-1, BR-2)
- **Files:** `frontend/src/components/workspace/VersionRestoreDialog.tsx`, uses existing `frontend/src/lib/api/` restore endpoint generated client
- **Do:** Restore routes exclusively through the 1-5 versioning service (BR-1 — one path, no parallel restore logic in this component). Confirm dialog states the consequence (e.g. "Hoàn thiện sẽ lỗi thời") using the `staled_steps` field already returned by 1-5's restore response; on confirm, the affected downstream stations flip to stale on the stepper (AC-2). If there's an unsaved autosave in flight when a version switch is requested, defer the switch until the save completes (≤1.5s target) rather than discarding the edit (BR-2, AC-3).
- **Verify:** `pnpm --filter frontend vitest run VersionRestoreDialog` → covers restore-uses-1-5-response-staled_steps, in-flight-autosave-defers-switch-no-data-loss cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/VersionRestoreDialog.tsx && git commit -m "feat(workspace): 5-9 restore via 1-5 service + stale cascade BR-1/BR-2" && git push`

### Step 5: Restore disabled while project RUNNING (AC-5) + History route
- **Files:** `frontend/src/components/workspace/VersionRestoreDialog.tsx` (disabled state), `frontend/src/app/projects/[id]/history/page.tsx`
- **Do:** Restore button disabled with an explanatory tooltip when `project.status === RUNNING` (AC-5). Add the secondary History route: a plain table of every version across every step (locked decision — audit value, not a polished UI investment for v1).
- **Verify:** `pnpm --filter frontend vitest run VersionRestoreDialog -- --grep running` → RUNNING-disables-restore-with-tooltip case passes; `pnpm --filter frontend typecheck` → exit 0 for the History route.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/VersionRestoreDialog.tsx frontend/src/app/projects/[id]/history && git commit -m "feat(workspace): 5-9 restore disabled while RUNNING + History route" && git push`

### Step 6: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/...`, `tests/e2e/version-switcher.spec.ts`
- **Do:** One test per AC above with a fixture of 3 versions where one is stale. Playwright flow: compare → restore → confirm stepper shows stale. Then **exercise the feature in a real running browser (dev server)**: open the switcher, compare v1↔v2 and confirm line highlighting, close and confirm focus returns correctly, restore an older `scene_set` version and confirm the "Hoàn thiện" station flips to stale on the stepper.
- **Verify:** `pnpm --filter frontend test:e2e -- version-switcher` → all AC-mapped tests pass; manual dev-server walkthrough matches AC-1/AC-2 exactly.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-9 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture 3 version có stale; Playwright flow so sánh→khôi phục→stepper stale.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-9.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-9.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
