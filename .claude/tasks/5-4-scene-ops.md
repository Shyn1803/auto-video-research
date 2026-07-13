# Task 5-4: Scene ops — thêm/xoá/nhân bản/sắp xếp

**Points:** 2đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1 · **FR:** FR-09
**State file:** [`state/5-4.json`](state/5-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-4-scene-ops` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want thêm, xoá, nhân bản, kéo-thả sắp xếp phân cảnh, so that cấu trúc video theo đúng nhịp tôi muốn.

## Why
FR-09 danh sách thao tác cảnh. Điểm kỹ thuật then chốt: scene_id bất biến (see [patterns/scene-versioning.md](../patterns/scene-versioning.md)) — mọi op chỉ đổi scene_number.

## Scope
**In:** kéo-thả (dnd-kit) + nút ↑↓; thêm cảnh (chọn layout, chèn sau cảnh hiện tại); xoá (confirm); nhân bản; mọi op tạo scene_set version.
**Out:** copy cảnh giữa project (v1.1); bulk ops.

## Business Rules
1. Reorder đổi scene_number giữ scene_id (cache/diff sống nhờ điều này).
2. Xoá confirm nêu ảnh hưởng ("video ngắn đi 6s").
3. Mọi op = version mới (undo = restore 5-9).
4. Nhân bản = scene_id **mới**, nội dung copy (cache key tự khác).

## Acceptance Criteria
1. **(happy)** Kéo #4 → vị trí 2: số cập nhật, id giữ (verify qua API), version mới.
2. **(biên)** Xoá cảnh đang mở → focus cảnh kế; xoá hết → empty state.
3. **(biên/BR-4)** Nhân bản → id mới; sửa bản sao không ảnh hưởng gốc; cache key khác.
4. **(a11y)** Toàn bộ ops làm được không chuột.

## Data & API
Reorder endpoint (§6 sẵn); thêm/xoá/duplicate (§6 sẵn). Contract change: không.

## Decisions already locked
- Không undo-stack riêng trong editor — version là undo.

## Execution Steps

Work these in order. Update `state/5-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Scene ops reducer (reorder/add/delete/duplicate)
- **Files:** `frontend/src/lib/state/sceneOpsReducer.ts`, `frontend/tests/unit/state/sceneOpsReducer.test.ts`
- **Do:** Pure reducer for the 4 ops. Reorder must only mutate `scene_number`, never `scene_id` (BR-1 — this is what keeps cache/diff correct, see `patterns/scene-versioning.md`); duplicate must mint a **new** `scene_id` with copied content (BR-4, so cache key differs). Every op produces a new scene_set version (BR-3 — no separate undo stack, version is undo per the locked decision).
- **Verify:** `pnpm --filter frontend vitest run sceneOpsReducer` → covers reorder-preserves-id, duplicate-new-id, delete cases.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/lib/state/sceneOpsReducer.ts frontend/tests/unit/state/sceneOpsReducer.test.ts && git commit -m "feat(workspace): 5-4 scene ops reducer" && git push`

### Step 2: Drag-and-drop reorder + ↑↓ buttons
- **Files:** `frontend/src/components/workspace/SceneSidebar.tsx` (extends 5-1's sidebar), uses `dnd-kit`
- **Do:** Wire `dnd-kit` drag-and-drop on the scene thumbnail sidebar, plus ↑↓ buttons as a fully keyboard-equivalent alternative (a11y AC-4 — every op must be doable without a mouse). Both paths call the reducer from Step 1 and PATCH the reorder endpoint (already exists per Data & API — no backend change needed).
- **Verify:** `pnpm --filter frontend typecheck` → exit 0; manual dev-server drag test confirms order updates.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/SceneSidebar.tsx && git commit -m "feat(workspace): 5-4 drag-drop reorder + keyboard up-down" && git push`

### Step 3: Add scene (layout picker, insert-after)
- **Files:** `frontend/src/components/workspace/AddSceneButton.tsx`, `frontend/src/components/workspace/LayoutPickerMenu.tsx`
- **Do:** "+" control that opens a layout-class picker (PascalCase canonical names only, per `rules/naming.md`) and inserts the new scene immediately after the currently open one.
- **Verify:** `pnpm --filter frontend vitest run AddSceneButton` → new scene inserted at correct position with chosen layout.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/AddSceneButton.tsx frontend/src/components/workspace/LayoutPickerMenu.tsx && git commit -m "feat(workspace): 5-4 add scene with layout picker" && git push`

### Step 4: Delete (confirm + impact) and duplicate
- **Files:** `frontend/src/components/workspace/DeleteSceneDialog.tsx`, `frontend/src/components/workspace/DuplicateSceneButton.tsx`
- **Do:** Delete confirm dialog states the impact (e.g. "video ngắn đi 6s", BR-2), and focus-trap defaults to the safe (cancel) button. On confirm, deleting the currently-open scene moves focus/selection to the next scene; deleting the last scene shows the empty state (CTA: add scene / re-run storyboard). Duplicate creates a copy with a new `scene_id` (Step 1 reducer) and confirms editing the copy never touches the original.
- **Verify:** `pnpm --filter frontend vitest run DeleteSceneDialog DuplicateSceneButton` → covers delete-open-scene-focus-next, delete-all-empty-state, duplicate-independent-edit.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/DeleteSceneDialog.tsx frontend/src/components/workspace/DuplicateSceneButton.tsx && git commit -m "feat(workspace): 5-4 delete confirm + duplicate" && git push`

### Step 5: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/state/sceneOpsReducer.test.ts`, `tests/e2e/scene-ops.spec.ts`
- **Do:** One test per AC above; Playwright for drag-and-drop + full keyboard-only path (Test Notes). Then **exercise the feature in a real running browser (dev server)**: drag scene #4 to position 2 and confirm via the API response that `scene_id` is preserved and only `scene_number` changed; delete the open scene and confirm focus moves; duplicate and edit the copy, confirming the original is untouched.
- **Verify:** `pnpm --filter frontend test:e2e -- scene-ops` → all AC-mapped tests pass; manual dev-server walkthrough confirms scene_id stability via API inspection.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-4 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + vitest reducer ops; Playwright kéo-thả + keyboard path.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
