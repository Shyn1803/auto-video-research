# Task 6-3: Màn Xuất bản — video + download + metadata

**Points:** 3đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 6-2 · **FR:** FR-12
**State file:** [`state/6-3.json`](state/6-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/6-3-man-xuat-ban-video-download` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want xem video cuối, tải về và copy sẵn tiêu đề/mô tả/tags, so that đăng tay lên bất kỳ nền tảng nào trong 1 phút.

## Why
Đường publish "luôn hoạt động" (FR-12 tầng download) — giá trị dùng được ngay từ M4 khi chưa có nền tảng nào duyệt API.

## Scope
**In:** player video final theo format; Download presigned (per-format); metadata copy (từng cái + tất cả); publish record `download` → PUBLISHED; bảng nền tảng đúng trạng thái provider (✓/⚠ chờ duyệt/○ chưa key — hàng khác của 8-1/10-3 hiện đúng nhãn từ giờ).
**Out:** đăng tự động (8.x); hẹn giờ (8-4).

## Business Rules
1. Presigned URL 24h; hết → nút "Tạo link mới".
2. Lần tải đầu (format bất kỳ) → PUBLISHED (1 lần chuyển); tải tiếp không đổi trạng thái.
3. Màn truy cập được từ READY trở đi (kể cả PUBLISHED — xem lại/tải lại).
4. Metadata copy gồm cả attribution BGM nếu track yêu cầu (6-5 BR-2).

## Acceptance Criteria
1. **(happy)** Tải 9:16 → file đúng; PUBLISHED; quay lại tải 16:9 vẫn được, trạng thái không đổi.
2. **(biên/BR-1)** URL 24h+ → "Tạo link mới" hoạt động.
3. **(copy/BR-4)** "Copy tất cả" đủ 3 phần + attribution khi có.
4. **(states)** Chưa READY → trạm lock đúng; render lỗi → error state đúng.

## Data & API
Bảng: publishes. Endpoints: §7 video + §8 publish-preview/publish(download). Contract change: không.

## Decisions already locked
- ⏳ PUBLISHED khi tải (không cần xác nhận "đã đăng thật").

## Execution Steps

Work these in order. Update `state/6-3.json` after **every** step. This is a UI task — the real-browser exercise rule applies (`rules/testing.md`): type-checks and unit tests are necessary but not sufficient for "done."

### Step 1: Scaffold the route + wireframe skeleton
- **Files:** `frontend/src/app/projects/[id]/xuat-ban/page.tsx` (route naming per [rules/folder-structure.md](../rules/folder-structure.md) `src/app/projects/[id]/`)
- **Do:** build the "Xuất bản" screen skeleton matching `docs/design/wireframe.html` and all 5 UI states (default/loading/empty/error/disabled) per `docs/design/design-system.md` §3; guard the route so it's a locked stepper state (BR-3) until project status is READY or later.
- **Verify:** `cd frontend && npm run typecheck && npm run build` → exit 0.
- **On failure:** transient → retry 3×; logic/config → `systematic-debugging` skill; still failing → mark `blocked`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add frontend/src/app/projects/[id]/xuat-ban && git commit -m "feat(publish): 6-3 scaffold Xuất bản route + states" && git push`

### Step 2: Final video player
- **Files:** `frontend/src/components/publish/VideoPlayer.tsx`
- **Do:** fetch the presigned download URL for the selected format via the OpenAPI-generated client (never hand-write a duplicate type, per [rules/type-safety.md](../rules/type-safety.md)); render a native `<video>` element (this plays the real merged MP4 file, not a Remotion `<Player>` — the Remotion runtime touchpoints end at render, per [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)); format switcher tab per available format.
- **Verify:** exercise in a real running browser per `rules/testing.md` — load the screen against a READY fixture project, confirm playback starts.
- **Commit:** `git commit -m "feat(publish): 6-3 final video player"`

### Step 3: Download presigned + regenerate on expiry (BR-1)
- **Files:** `frontend/src/components/publish/DownloadButton.tsx`, backend endpoints already spec'd in `docs/specs/api-spec.md` §8 publish-preview/publish(download) — reused, no contract change
- **Do:** Download button fetches a presigned URL (24h TTL); on an expired/failed URL (403/410 from storage) show "Tạo link mới" which re-requests a fresh presigned URL.
- **Verify:** Playwright test simulating an expired-URL response → "Tạo link mới" regenerates and download succeeds → AC-2.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(publish): 6-3 presigned download + regenerate on expiry (BR-1)"`

### Step 4: First-download triggers PUBLISHED, idempotent (BR-2, BR-3)
- **Files:** backend `backend/app/api/publish.py`, backend `backend/app/services/state_machine.py` (reuse the state machine from 1-4)
- **Do:** the first download call of any format transitions the project to PUBLISHED exactly once; subsequent downloads (same or different format) never re-transition; the screen stays reachable from READY through PUBLISHED for replay/redownload (BR-3).
- **Verify:** `cd backend && pytest backend/tests/integration/api/test_publish.py::test_first_download_triggers_published backend/tests/integration/api/test_publish.py::test_repeat_download_no_retransition -v` → both pass; Playwright: download 9:16 → PUBLISHED; go back, download 16:9 → still PUBLISHED (AC-1).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(publish): 6-3 first-download PUBLISHED transition (BR-2/BR-3)"`

### Step 5: Metadata copy incl. BGM attribution (BR-4)
- **Files:** `frontend/src/components/publish/MetadataCopyPanel.tsx`
- **Do:** per-field copy buttons (title/description/tags) + "Copy tất cả"; description auto-appends the BGM attribution line when the selected 6-5 track requires it (6-5 BR-2); copy buttons give an accessible "đã copy" confirmation readable by assistive tech (a11y requirement in the epic's UI/UX section).
- **Verify:** Playwright: select an attribution-requiring BGM track, click "Copy tất cả" → clipboard contains all 3 metadata parts + attribution line → AC-3.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(publish): 6-3 metadata copy panel with BGM attribution (BR-4)"`

### Step 6: Platform status table + lock/error states
- **Files:** `frontend/src/components/publish/PlatformStatusTable.tsx`
- **Do:** render ✓/⚠ chờ duyệt/○ chưa key badges from real per-platform provider availability (feeds 8-1/10-3 later, don't hardcode); locked stepper state when not yet READY; error state with retry when the upstream render job failed.
- **Verify:** Playwright covering all 5 UI states (default/loading/empty/error/disabled) per `docs/design/design-system.md` §3 → AC-4.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(publish): 6-3 platform status table + lock/error states"`

### Step 7: E2E Playwright — canonical M4 flow
- **Files:** `frontend/tests/e2e/m4-topic-to-download.spec.ts`
- **Do:** per this task's own DoD, this is the canonical M4 end-to-end test (topic → render → download) that the test plan references going forward; drive it through a real browser per `rules/testing.md`, ending at the Xuất bản screen's download action.
- **Verify:** `npx playwright test m4-topic-to-download.spec.ts` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "test(publish): 6-3 canonical M4 end-to-end Playwright flow"`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + Playwright flow M4 end-to-end kết thúc tại đây — trở thành E2E chuẩn của test-plan.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/6-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/6-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
