# Task 5-1: Project workspace — topbar + stepper + khung Phân cảnh

**Points:** 5đ · **Epic:** 5 — Workspace UI · **Depends:** 2-1, 2-3, 1-5 · **FR:** FR-09
**State file:** [`state/5-1.json`](state/5-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-1-project-workspace-topbar-stepper` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want một khung làm việc nhất quán với stepper luôn cho biết tôi đang ở đâu và cần làm gì, so that không bao giờ lạc trong quy trình 5 bước.

## Why
"Pipeline là xương sống UI" — nguyên tắc #1 của `docs/design/ux-design.md`. Khung mọi story UI khác lắp vào.

## Scope
**In:** layout `/projects/{id}`: topbar (← Dự án, tên, StatusBadge, slot VersionSwitcher); PipelineStepper 5 trạm đủ trạng thái (design-system §3.2); màn Phân cảnh 3 cột (sidebar thumbnail + SceneForm schema-driven + ScenePlayer); header "Đã duyệt x/y"; ApproveBar chuẩn §3.3; autosave 1s; 422→inline theo field_path; chế độ xem-lại readonly + "Sửa lại từ đây".
**Out:** controls chi tiết (5-2); AssetPicker (5-3); scene ops (5-4); RunningState (5-8); VersionSwitcher nội dung (5-9).

## Business Rules
1. Trạm done click → readonly + nút "Sửa lại từ đây" → confirm liệt kê bước sẽ stale → mở chế độ sửa.
2. Trạm locked click → tooltip điều kiện mở.
3. Autosave lỗi mạng → badge "⚠ chưa lưu" + retry tự động + giữ nội dung local — không mất chữ đang gõ.
4. SceneForm sinh từ JSON Schema — field mới trong schema tự có control mặc định theo type.
5. Duyệt từng cảnh ghi trạng thái; header đếm x/y realtime.
6. **(PO 2026-07-11)** Stepper **5 trạm** (Nghiên cứu → Nội dung → Phân cảnh → Hoàn thiện → Xuất bản); trạm done còn cảnh báo hiển thị **✓⚠** + tooltip liệt kê.
7. Topbar có nút **▶ Xem bản mới nhất**; tên project ⓘ mở ProjectDrawer (5-10).

## Acceptance Criteria
1. **(happy)** Sửa field → Player <100ms + autosave version mới + badge đúng chu trình.
2. **(biên/BR-1)** Click trạm ✓ Kịch bản → readonly; "Sửa lại từ đây" → confirm nêu bước sẽ lỗi thời → vào sửa được.
3. **(lỗi/BR-3)** Ngắt mạng khi gõ → ⚠ chưa lưu; nối lại → tự lưu; chữ không mất (Playwright offline test).
4. **(biên/BR-4)** Thêm field optional vào schema fixture → form tự render control.
5. **(a11y)** Điều hướng stepper bằng phím đủ; NVDA đọc trạng thái trạm.
6. **(states)** Đủ 5 states có test/screenshot trong PR.

## Data & API
Endpoints: GET/PUT scenes (§6), approve scene (mới — `POST scenes/{id}/approve` → cập nhật api-spec §6); GET project tổng hợp trạng thái stepper. Contract change: **có**.

## Decisions already locked
- Duyệt theo từng cảnh (không duyệt cả bước một nút).

## Execution Steps

Work these in order. Update `state/5-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Route shell + topbar
- **Files:** `frontend/src/app/projects/[id]/layout.tsx`, `frontend/src/components/workspace/Topbar.tsx`, `frontend/src/lib/api/` (generated client, run `make gen-api-client` if project schema exists)
- **Do:** Build `/projects/{id}` layout with topbar: `← Dự án` back link, project name (click opens ⓘ ProjectDrawer per BR-7 — stub a placeholder `onOpenDrawer` prop if 5-10 isn't done yet, don't block on it), `StatusBadge`, a named slot for `VersionSwitcher` (render `null` placeholder — 5-9 fills it), and the `▶ Xem bản mới nhất` button (BR-7) that opens the latest scene_set/video preview. Follow `docs/design/wireframe.html` topbar markup as visual source of truth.
- **Verify:** `pnpm --filter frontend typecheck && pnpm --filter frontend lint` → exit 0.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/app/projects frontend/src/components/workspace/Topbar.tsx && git commit -m "feat(workspace): 5-1 topbar shell" && git push`

### Step 2: PipelineStepper (5 trạm, BR-6)
- **Files:** `frontend/src/components/workspace/PipelineStepper.tsx`, `frontend/tests/unit/components/PipelineStepper.test.tsx`
- **Do:** Implement the 5-station stepper (Nghiên cứu → Nội dung → Phân cảnh → Hoàn thiện → Xuất bản) per `docs/design/design-system.md` §3.2, covering every station state (locked/current/done/done-with-warning `✓⚠`/error). Done-with-warning stations show a tooltip listing the warnings. `<nav>` semantics + `aria-current="step"`; arrow-key + Enter navigation (BR-2 tooltip on locked-station click: "Hoàn thành Kịch bản trước" pattern).
- **Verify:** `pnpm --filter frontend vitest run PipelineStepper` → all cases pass (locked/current/done/done-with-warning/keyboard nav).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/PipelineStepper.tsx frontend/tests/unit/components/PipelineStepper.test.tsx && git commit -m "feat(workspace): 5-1 PipelineStepper 5 stations" && git push`

### Step 3: Scenes screen — 3-column frame
- **Files:** `frontend/src/app/projects/[id]/scenes/page.tsx`, `frontend/src/components/workspace/SceneSidebar.tsx`, `frontend/src/components/workspace/SceneFormPanel.tsx` (placeholder, controls come in 5-2), `frontend/src/components/workspace/ScenePlayerPanel.tsx` (wraps the Remotion `<Player>` from `packages/remotion-templates`, per `patterns/scene-video-composition-split.md`)
- **Do:** Build the 3-column Phân cảnh screen: sidebar of scene thumbnails, middle SceneForm panel (schema-driven, wired in Step 4), right ScenePlayer. Header shows "Đã duyệt x/y" computed from scene `approved` counts (BR-5, realtime).
- **Verify:** `pnpm --filter frontend typecheck` → exit 0; manual render in dev server shows 3 columns with fixture scene_set.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/app/projects/[id]/scenes frontend/src/components/workspace/Scene*.tsx && git commit -m "feat(workspace): 5-1 3-column Phan canh frame" && git push`

### Step 4: Schema-driven SceneForm generator (BR-4)
- **Files:** `frontend/src/lib/schema-form/generate.ts`, `frontend/src/lib/schema-form/*.test.ts`
- **Do:** Generator that reads the Scene JSON Schema (exported from `backend/app/schemas/scene.py`, consumed via the generated Zod schema in `packages/remotion-templates/src/schema.ts` — never hand-write a duplicate type per `rules/code-style.md`) and renders a default control per field `type` (string→text, enum→select, number→numeric input, etc.). A new optional field added to the schema fixture must get a control with zero FE code changes (AC-4).
- **Verify:** `pnpm --filter frontend vitest run schema-form` → includes a test that adds a field to the fixture schema and asserts a control renders.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/lib/schema-form && git commit -m "feat(workspace): 5-1 schema-driven SceneForm generator" && git push`

### Step 5: Autosave (BR-3) + 422 inline errors
- **Files:** `frontend/src/lib/hooks/useAutosave.ts`, `frontend/src/lib/hooks/useAutosave.test.ts`
- **Do:** 1s debounce autosave on SceneForm edits, PUT via generated API client. On network failure: badge "⚠ chưa lưu" + automatic retry with backoff, local content preserved (never clobber unsaved keystrokes). On `422`, map `field_path` from the error response to the matching form field's inline error.
- **Verify:** `pnpm --filter frontend vitest run useAutosave` → covers success/422/offline-retry cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/lib/hooks/useAutosave.* && git commit -m "feat(workspace): 5-1 autosave + 422 inline errors" && git push`

### Step 6: Scene approve + ApproveBar (contract change)
- **Files:** `frontend/src/components/workspace/ApproveBar.tsx`, `backend/app/api/` scenes router, `docs/specs/api-spec.md` §6 (đổi contract — update in same PR per `rules/documentation.md`)
- **Do:** Add `POST scenes/{id}/approve` backend endpoint + `approved` field on scene response (this is a "đổi contract" change — update `docs/specs/api-spec.md` §6 and note it in the PR description's **Contract changes** section per `rules/pull-requests.md`). Wire ApproveBar (design-system §3.3) to call it per-scene (not per-step — decision already locked).
- **Verify:** `pnpm --filter backend pytest backend/tests/unit/api/test_scenes_approve.py -q` and `pnpm --filter frontend vitest run ApproveBar` → pass.
- **On failure:** same policy as Step 1; a schema/contract change without the doc update is a review-reject per `rules/code-review.md` — don't skip the doc.
- **Commit:** `git add frontend/src/components/workspace/ApproveBar.tsx backend/app/api docs/specs/api-spec.md && git commit -m "feat(scene): 5-1 scene approve endpoint + ApproveBar" && git push`

### Step 7: Readonly / "Sửa lại từ đây" flow (BR-1, BR-2)
- **Files:** `frontend/src/components/workspace/StaleConfirmDialog.tsx`, station click handlers in `PipelineStepper.tsx`/scenes page
- **Do:** Clicking a done station opens it readonly with a "Sửa lại từ đây" button; clicking it opens a confirm dialog listing which later steps will become stale, then unlocks edit mode. Clicking a locked station shows the BR-2 tooltip instead of navigating.
- **Verify:** `pnpm --filter frontend vitest run StaleConfirmDialog` → pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/StaleConfirmDialog.tsx && git commit -m "feat(workspace): 5-1 readonly + sua lai tu day flow" && git push`

### Step 8: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/components/...`, `tests/e2e/scenes-workspace.spec.ts` (Playwright, mirrors module under test per `rules/folder-structure.md`)
- **Do:** One test per AC above (happy/biên/lỗi/a11y/states) — Playwright is primary per Test Notes (frame + offline + keyboard), vitest for the form generator. Cover all 5 UI states (default/loading skeleton/empty/error/disabled) with screenshots in the PR per `docs/design/design-system.md` §3. Then **exercise the feature in a real running browser (dev server)**, not just type-check/unit test — start the frontend dev server, navigate to `/projects/{id}/scenes` with a fixture project, and manually confirm: field edit reflects in Player <100ms, autosave badge cycle, offline→reconnect keeps text, stepper keyboard nav, done-station readonly→edit flow.
- **Verify:** `pnpm --filter frontend test:e2e -- scenes-workspace` → all AC-mapped tests pass; manual dev-server walkthrough confirms no console errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-1 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + Playwright chính (khung + offline + keyboard); vitest cho form generator.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
