# Task 5-7: Màn "Nội dung" (Dàn ý collapse + Kịch bản)

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 4-5, 5-8 · **FR:** FR-05, FR-06
**State file:** [`state/5-7.json`](state/5-7.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-7-man-noi-dung` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want biên tập dàn ý và kịch bản với nguồn tham chiếu bên cạnh, so that sửa nội dung nhanh mà không rời ngữ cảnh fact đã kiểm chứng.

## Why
FR-05/06 phía user. Banner warning từ node (lệch số, title cắt — 4-5) phải "đập vào mắt" tại đây — chốt chặn con người cuối trước khi nội dung thành hình.

## Scope
**In:** Dàn ý 7 card section editable; Kịch bản (title/description/tags + voice_over textarea); panel phải fact PASS ghim + [source] link; "Sinh lại bằng AI" → RunningState; autosave; render `warnings[]` từ version content thành banner + "xem chỗ lệch".
**Out:** rich-text đầy đủ (plain + marker đủ v1); đếm thời lượng đọc chính xác (ước tính từ ký tự).

## Business Rules
1. Warnings hiện banner vàng đầu màn; loại `number_mismatch` có nút highlight đúng con số lệch 2 phía.
2. `[source_id]` render link → mở panel nguồn tương ứng.
3. Ước tính thời lượng đọc hiện cạnh voice_over — lệch mục tiêu ±20% → nhắc nhẹ.

## Acceptance Criteria
1. **(happy)** Sửa → version mới autosave; approve → RunningState bước kế.
2. **(biên/BR-1)** Version có number_mismatch → banner + highlight đúng số 2 phía.
3. **(BR-3)** Voice_over dài gấp rưỡi mục tiêu → nhắc thời lượng.
4. **(a11y)** Screen reader đọc banner khi vào màn.

## Data & API
Endpoints: versions PUT/GET (§3). Contract: `warnings[]` đã chuẩn ở 4-5.

## Decisions already locked
- **Gộp thành 1 trạm "Nội dung"** (PO 2026-07-11): dàn ý panel trên cùng — mở rộng khi chờ duyệt, collapse sau duyệt; kịch bản bên dưới. Backend giữ nguyên 2 step/2 version/2 gate (4-5 không đổi). Sửa dàn ý sau khi kịch bản tồn tại → kịch bản stale (cascade 1-5).

## Execution Steps

Work these in order. Update `state/5-7.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Nội dung screen shell — Dàn ý (collapsible) + Kịch bản
- **Files:** `frontend/src/app/projects/[id]/content/page.tsx`, `frontend/src/components/workspace/OutlinePanel.tsx`, `frontend/src/components/workspace/ScriptPanel.tsx`
- **Do:** Single "Nội dung" station combining both steps (locked decision, PO 2026-07-11): Dàn ý (7 editable section cards) as a top panel — expanded while awaiting approval, collapsed after approval — with Kịch bản (title/description/tags + voice_over textarea) below. Backend remains 2 separate steps/2 versions/2 gates (4-5 unchanged) — this is purely a UI merge, don't collapse the backend state machine.
- **Verify:** `pnpm --filter frontend typecheck` → exit 0.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/app/projects/[id]/content frontend/src/components/workspace/OutlinePanel.tsx frontend/src/components/workspace/ScriptPanel.tsx && git commit -m "feat(workspace): 5-7 Noi dung screen shell, outline+script merged station" && git push`

### Step 2: Source panel + [source_id] link (BR-2)
- **Files:** `frontend/src/components/workspace/PinnedSourcesPanel.tsx`
- **Do:** Right panel pinning fact-`PASS` sources for reference. Content containing `[source_id]` markers renders as a link that opens the panel scrolled to the matching source.
- **Verify:** `pnpm --filter frontend vitest run PinnedSourcesPanel` → `[source_id]` link opens correct panel entry.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/PinnedSourcesPanel.tsx && git commit -m "feat(workspace): 5-7 pinned sources panel + source_id links" && git push`

### Step 3: Warnings banner (BR-1) — number_mismatch highlight
- **Files:** `frontend/src/components/workspace/WarningsBanner.tsx`, `frontend/tests/unit/components/WarningsBanner.test.tsx`
- **Do:** Render `warnings[]` from the content version (contract already standardized in 4-5, no backend change) as a yellow banner at the top of the screen (`role="alert"` for a11y). `number_mismatch` warnings get a "xem chỗ lệch" button that highlights the mismatched number on both sides (outline vs script).
- **Verify:** `pnpm --filter frontend vitest run WarningsBanner` → number_mismatch case highlights both occurrences.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/WarningsBanner.tsx frontend/tests/unit/components/WarningsBanner.test.tsx && git commit -m "feat(workspace): 5-7 warnings banner + number_mismatch highlight" && git push`

### Step 4: Reading-time estimate (BR-3)
- **Files:** `frontend/src/lib/readingTime.ts`, `frontend/src/components/workspace/ScriptPanel.tsx`
- **Do:** Estimate reading duration from `voice_over` character count next to the textarea; nudge (non-blocking) when the estimate deviates ±20% from the target duration.
- **Verify:** `pnpm --filter frontend vitest run readingTime` → ±20% threshold triggers nudge, within-range does not.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/lib/readingTime.ts frontend/src/components/workspace/ScriptPanel.tsx && git commit -m "feat(workspace): 5-7 reading-time estimate nudge" && git push`

### Step 5: Autosave + "Sinh lại bằng AI" → RunningState + stale cascade
- **Files:** `frontend/src/components/workspace/RegenerateButton.tsx`, reuse `frontend/src/lib/hooks/useAutosave.ts` from 5-1
- **Do:** Edits autosave into a new content version. "Sinh lại bằng AI" routes through the RunningState component (5-8 — must be `done` first). Editing the outline after a script already exists must mark the script stale (cascade via the 1-5 versioning service — reuse it, don't reimplement staleness logic locally).
- **Verify:** `pnpm --filter frontend vitest run RegenerateButton` → outline-edit-after-script-exists marks script stale via the shared versioning service call.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/RegenerateButton.tsx && git commit -m "feat(workspace): 5-7 regenerate via RunningState + stale cascade" && git push`

### Step 6: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/components/...`, `tests/e2e/content-screen.spec.ts`
- **Do:** One test per AC above; fixture content version with each warning type (Test Notes); Playwright flow edit → regenerate → compare versions. Then **exercise the feature in a real running browser (dev server)**: load a fixture project at the Nội dung step, edit outline text, confirm autosave + script staleness, trigger regenerate, confirm RunningState shows and the screen returns to the editor on completion; confirm the warnings banner is announced by a screen reader on entry.
- **Verify:** `pnpm --filter frontend test:e2e -- content-screen` → all AC-mapped tests pass; manual dev-server walkthrough confirms banner `role=alert` announcement.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-7 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture version có warnings mỗi loại; Playwright flow sửa → sinh lại → so version.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-7.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-7.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
