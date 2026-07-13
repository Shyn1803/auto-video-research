# Task 5-2: Edit controls — text/màu/animation/layout/giọng

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1 · **FR:** FR-09
**State file:** [`state/5-2.json`](state/5-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-2-edit-controls` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want chỉnh chữ, màu, hiệu ứng, bố cục và lời đọc bằng control trực quan, so that tuỳ biến cảnh mà không hiểu gì về JSON.

## Why
FR-09 phần "sửa mọi thứ". Dry-run đổi layout (BR-1) chuyển lỗi validate từ "bực mình sau khi lưu" thành "quyết định có thông tin trước khi đổi".

## Scope
**In:** controls text (content marker bold, role, position, màu + highlight picker), animation (type + delay slider); đổi layout với dry-run cảnh báo phần tử bị cắt; voice panel (textarea, giọng nam/nữ, tốc độ).
**Out:** đổi ảnh (5-3); font tuỳ chỉnh (v1.1).

## Business Rules
1. Đổi layout vi phạm ràng buộc → dialog liệt kê đích danh phần tử bị bỏ; huỷ = nguyên trạng.
2. Color picker preset theo theme + custom hex có cảnh báo contrast (không chặn).
3. Sửa voice text sau produce → audio cũ đánh dấu stale + badge "giọng đọc sẽ tạo lại".
4. Bold marker nhập bằng nút **B** trên selection (user không cần gõ `**`).

## Acceptance Criteria
1. **(happy)** Mỗi control đổi → Player phản ánh ngay; lưu đúng schema.
2. **(biên/BR-1)** Ghi đè MediaText (3 text) → MediaFull (max 2): dialog nêu "chữ 't3' sẽ bị bỏ"; huỷ giữ nguyên.
3. **(biên/BR-3)** Sửa lời đọc cảnh đã produce → badge cảnh báo hiện; produce lại chỉ cảnh này (nối 6-1 BR-4).
4. **(BR-4)** Bôi đen chữ bấm B → content có marker + Player highlight.
5. **(a11y)** Slider delay điều khiển bằng ←/→.

## Data & API
PUT scene (sẵn). Contract change: không.

## Decisions already locked
- Không WYSIWYG kéo vị trí tự do — position ngữ nghĩa (top/center/bottom) đúng spec schema v1 (chống scope creep).

## Execution Steps

Work these in order. Update `state/5-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Text controls (content marker bold, role, position, màu)
- **Files:** `frontend/src/components/workspace/controls/TextControl.tsx`, `frontend/src/components/workspace/controls/BoldButton.tsx` (BR-4), `frontend/tests/unit/components/controls/TextControl.test.tsx`
- **Do:** Add controls into the SceneForm (from 5-1) for `content` (with bold marker), `role`, semantic `position` (top/center/bottom — no free WYSIWYG drag, per the locked decision), and color + highlight picker. BR-4: a **B** button on text selection inserts the bold marker syntax (no manual `**` typing); wire `Ctrl+B` shortcut too.
- **Verify:** `pnpm --filter frontend vitest run TextControl` → covers marker insertion via button and shortcut.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/components/workspace/controls/TextControl.tsx frontend/src/components/workspace/controls/BoldButton.tsx frontend/tests/unit/components/controls/TextControl.test.tsx && git commit -m "feat(workspace): 5-2 text controls + bold marker button" && git push`

### Step 2: Color picker with contrast warning (BR-2)
- **Files:** `frontend/src/components/workspace/controls/ColorPicker.tsx`
- **Do:** Theme presets + custom hex input. Custom hex triggers a non-blocking contrast warning using an existing contrast-check library (do not hand-roll WCAG contrast math — Test Notes explicitly says "dùng lib sẵn").
- **Verify:** `pnpm --filter frontend vitest run ColorPicker` → contrast warning fires below threshold, does not block save.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/controls/ColorPicker.tsx && git commit -m "feat(workspace): 5-2 color picker + contrast warning" && git push`

### Step 3: Animation controls (type + delay slider)
- **Files:** `frontend/src/components/workspace/controls/AnimationControl.tsx`
- **Do:** Animation `type` select + `delay` slider bound to the Motion Planner's allowed preset values (read from `packages/remotion-templates/src/motion/presets.ts` — never invent a new animation value client-side, that would be an AI/UI-chooses-layout violation per `anti-patterns/ai-chooses-layout.md` if it leaked into stored content; this control only picks among Layout-Engine-approved presets). Slider operable via ←/→ (a11y AC-5).
- **Verify:** `pnpm --filter frontend vitest run AnimationControl` → keyboard-operable slider test passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/controls/AnimationControl.tsx && git commit -m "feat(workspace): 5-2 animation type + delay slider" && git push`

### Step 4: Layout change with dry-run (BR-1)
- **Files:** `frontend/src/components/workspace/controls/LayoutDryRunDialog.tsx`, `frontend/src/lib/api/` (dry-run endpoint call if backend exposes one, else client-side constraint check reusing the Layout Engine's constraint resolver contract)
- **Do:** Changing layout class validates against the target layout's constraints (e.g. MediaText 3-text → MediaFull max-2) **before** committing; on violation, show a dialog naming the exact elements that would be dropped (e.g. "chữ 't3' sẽ bị bỏ"). Cancel restores the prior selection exactly.
- **Verify:** `pnpm --filter frontend vitest run LayoutDryRunDialog` → violation case names the dropped element; cancel path leaves state unchanged.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/controls/LayoutDryRunDialog.tsx && git commit -m "feat(workspace): 5-2 layout change dry-run dialog" && git push`

### Step 5: Voice panel + stale-audio badge (BR-3)
- **Files:** `frontend/src/components/workspace/controls/VoicePanel.tsx`
- **Do:** Textarea for voice text, giọng nam/nữ select, tốc độ control. If the scene was already produced (has audio) and voice text changes, mark old audio stale and show badge "giọng đọc sẽ tạo lại" (cross-references 6-1 BR-4 — re-produce only this scene, don't implement the re-produce trigger itself here, only the badge/flag).
- **Verify:** `pnpm --filter frontend vitest run VoicePanel` → stale badge appears after edit on a produced scene.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/controls/VoicePanel.tsx && git commit -m "feat(workspace): 5-2 voice panel + stale-audio badge" && git push`

### Step 6: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/components/controls/...`, `tests/e2e/edit-controls.spec.ts`
- **Do:** One test per AC above; Playwright for the dry-run dialog flow (Test Notes). Then **exercise the feature in a real running browser (dev server)**: open a fixture scene, run each control (text/color/animation/layout dry-run/voice) and confirm the Player reflects changes immediately and saved content matches schema.
- **Verify:** `pnpm --filter frontend test:e2e -- edit-controls` → all AC-mapped tests pass; manual dev-server walkthrough shows no console errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-2 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + vitest control-level; Playwright cho dialog dry-run; contrast check dùng lib sẵn (không tự viết).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
