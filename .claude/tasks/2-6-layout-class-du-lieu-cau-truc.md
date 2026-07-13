# Task 2-6: 6 layout class dữ liệu & cấu trúc — constraint preset + motion preset

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-1, 2-2, 2-4 (timestamps) · **FR:** FR-08, FR-11
**State file:** [`state/2-6.json`](state/2-6.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/2-6-layout-class-du-lieu-cau-truc` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want các bố cục chuyên cho số liệu, so sánh, danh sách, trích dẫn và code — với hiệu ứng chuyển động phù hợp từng loại nội dung, so that video tin công nghệ đa dạng và truyền tải đúng bản chất thông tin.

## Why
Feedback PO 2026-07-11 + [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md): mỗi layout class = constraint preset (flexbox) + motion preset theo loại component. Dựng 6 class nhóm Dữ liệu + Cấu trúc (`BigNumber`, `Chart`, `VersusTable`, `List`, `Quote`, `Code`) + bảng motion preset dùng chung cho cả 5 class cơ bản của 2-2.

## Scope
**In:** 6 composition = constraint preset flex (slots, gap, padding) + responsive rules 2 format; motion preset table + renderer cho MotionPlan: mỗi track = `<Sequence from>` + Animated, sync_points = interpolate mốc tuyệt đối — countUp kết thúc theo `end_by_ms`, list stagger theo `enter_at_ms` từng item; áp cả cho 5 class 2-2; Pydantic + Zod 6 element types (mở rộng 2-1); SceneForm control tương ứng; gallery override trong editor; render test matrix 11 class × 2 format.
**Out:** chart line/pie, Timeline/Gallery class, lower_third (v1.1); solver tổng quát (v1.1); classifier (4-6).

## Business Rules
1. Dữ liệu chart/table/number là inline trong Scene JSON, không fetch ngoài; constraints theo spec §3.6 (points 2-6, rows 2-4, items 3-5…).
2. `quote_block` bắt buộc `source_id` truy được fact-check; không nguồn → validator chặn (strict) / engine hạ class về TextFocus (auto_fix + warning).
3. List stagger khớp voice: item i xuất hiện khi từ đầu tiên của ý i được đọc; không có timestamps → fallback 90ms/item (dial 4-7) hoặc 60ms/item (dial 8-10) — `docs/specs/video-taste.md` §3.
4. Số trong number/chart/table phải khớp fact đã kiểm chứng — mapper 4-6 chỉ điền từ claims/key_facts, kèm `[source_id]`.
5. Mỗi class mới pass đủ render test 2 format + auto-shrink trước khi được bật trong rule table của Layout Classifier (4-6) — AI không biết đến danh sách layout.

## Acceptance Criteria
1. **(happy)** Fixture 6 layout render 2 format đúng spec; PO duyệt visual (12 ảnh); count-up/bar-grow/stagger đúng nhịp.
2. **(biên/BR-3)** List 4 items voice 8s → xuất hiện đúng lúc từng ý được đọc.
3. **(biên/BR-2)** quote không source_id: strict → 422; auto_fix → hạ TextFocus + warning.
4. **(lỗi)** chart 7 points → validator chặn đúng field_path; table label 25 ký tự → 422.
5. **(pipeline)** Bật 6 class trong rule table classifier → storyboard 3 topic thật (Ollama) chọn ≥3 class mới hợp lý.
6. **(editor)** Ghi đè sang Chart trong gallery → form đổi sang bảng nhập points; Player cập nhật ngay.

## Decisions already locked
- 6 layout thuộc v1 (PO 2026-07-11). Lịch: tuần 4-6, sau M1, không chặn critical path.
- ⏳ Màu chart: 1 màu primary + highlight — không palette nhiều màu.

## Execution Steps

Work these in order. Update `state/2-6.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit. **Invoke `/remotion-markup` before writing any composition/primitive/preset code** (dev-guide.md §2.1) — DoD requires the PR state which skill was invoked.

### Step 1: Pydantic + Zod — 6 new element types (extends 2-1's schema)
- **Files:** `backend/app/schemas/scene.py`
- **Do:** Add the 6 new element types backing `BigNumber`, `Chart`, `VersusTable`, `List`, `Quote`, `Code` per `docs/specs/scene-json-schema.md` §3.6 constraints (points 2–6, rows 2–4, items 3–5, etc. — read the exact bounds from the spec, don't invent numbers). This extends the discriminated union added in 2-1; the 11-class enum name set was already fixed there per `rules/naming.md`, so this step only adds the data shapes, not new class names. `quote_block` requires `source_id` (BR-2). Chart/table/number data is inline in Scene JSON, never fetched externally (BR-1). Still schema `1.0.0` — not released yet, no migration needed per Data & API note.
- **Verify:** `make gen-scene-schema` → regenerates `schema-1.0.0.json` + `schema.ts` cleanly, exits 0; a smoke import test confirms all 6 new types are constructible.
- **On failure:** transient → retry same step up to 3×, log attempt in state file; logic/type error → stop retrying, invoke `systematic-debugging` skill; still failing after 3 → mark step + task `blocked`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/schemas/scene.py packages/remotion-templates/schema/scene-1.0.0.json packages/remotion-templates/src/schema.ts && git commit -m "feat(scene): 2-6 add 6 data/structure element types (BigNumber/Chart/VersusTable/List/Quote/Code)"` → `git push`

### Step 2: Validator rules — data bounds (BR-1) and quote source_id gate (BR-2)
- **Files:** `backend/app/services/scene_validator.py`
- **Do:** Add strict-mode 422 rejection with correct `field_path` for out-of-bounds data (chart >6 points, table rows outside 2–4, list items outside 3–5, table label >25 chars — confirm exact bounds against spec §3.6). Add the `quote_block` gate: missing `source_id` → strict mode rejects (422), `auto_fix` mode downgrades the scene to `TextFocus` + logs a warning (BR-2) — this downgrade path only exists in `auto_fix`, matching 2-1's auto_fix/strict split.
- **Verify:** unit tests: a 7-point chart in strict mode → 422 with correct `field_path` (covers AC-4); a `quote_block` with no `source_id` in strict → 422; same input in `auto_fix` → scene downgraded to `TextFocus` with warning logged (covers AC-3).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/scene_validator.py && git commit -m "feat(scene): 2-6 add data-bounds + quote source_id validator rules (BR-1, BR-2)"` → `git push`

### Step 3: Motion preset table (§9.1) + MotionPlan renderer (§9.3)
- **Files:** `packages/remotion-templates/src/motion/presets.ts`, `packages/remotion-templates/src/motion/Animated.tsx` (extends 2-2's wrapper)
- **Do:** Implement the shared motion preset table per `docs/specs/layout-engine.md` §9.1, applying to both the 6 new classes here and the 5 base classes from 2-2 (this table is shared, not per-class duplicated code). Implement the MotionPlan renderer per §9.3: each track is `<Sequence from>` + `Animated`; `sync_points` interpolate to absolute time marks — count-up animations finish exactly `end_by_ms`, list items stagger per-item `enter_at_ms`, highlights trigger at their `sync_point`. Reuse the `<Sequence layout="none">` convention fixed in 2-2 — don't reintroduce the default-Sequence-wraps-AbsoluteFill bug flagged in `rules/code-review.md`.
- **Verify:** unit test feeding a MotionPlan with `sync_points` asserts each animated element reaches its target state (opacity/position/count value) at the frame corresponding to its `end_by_ms`/`enter_at_ms`, not before or after.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/motion && git commit -m "feat(remotion): 2-6 add shared motion preset table + MotionPlan sync_points renderer (layout-engine §9)"` → `git push`

### Step 4: List stagger mapped to voice timestamps (BR-3)
- **Files:** `packages/remotion-templates/src/motion/listStagger.ts`
- **Do:** Implement the pure function mapping list item `i` to its `enter_at_ms` from the first word's timestamp of that item's corresponding idea (per BR-3), using the word timestamps produced by 2-4. When timestamps are unavailable, fall back to a fixed per-item stagger: 90ms/item for `motion_intensity` dial 4–7, 60ms/item for dial 8–10, per `docs/specs/video-taste.md` §3.
- **Verify:** unit test (pure function, per Test Notes) with a 4-item list + a mock 8s voice timestamp array → each item's `enter_at_ms` matches the timestamp of its idea's first word; a second test with no timestamps confirms the dial-based fallback (90ms vs 60ms) applies correctly (covers AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/motion/listStagger.ts && git commit -m "feat(remotion): 2-6 add list-stagger-to-voice-timestamp mapping (BR-3, pure function)"` → `git push`

### Step 5: 6 constraint presets (BigNumber/Chart/VersusTable/List/Quote/Code) × 2 formats
- **Files:** `packages/remotion-templates/src/presets/layouts/big-number.*.json`, `chart.*.json`, `versus-table.*.json`, `list.*.json`, `quote.*.json`, `code.*.json`; corresponding primitives if a new component-kind is introduced (`packages/remotion-templates/src/primitives/*.tsx`)
- **Do:** Each of the 6 classes is a constraint preset (flexbox slots/gap/padding, layout-engine §6) with responsive rules for both formats (§7) — data, not code, same convention as 2-2's 5 presets (`rules/folder-structure.md`). Add any new primitive needed per new component-kind (e.g. a `Code` primitive with JetBrains Mono per the UI/UX note, a `BigNumber` primitive with count-up wired through the `Animated` wrapper — text-and-number-mixed content displays statically, not counted, per the locked ⏳ decision). Chart uses a single primary color + highlight only — no multi-color palette (locked decision).
- **Verify:** all 12 preset JSON files (6 classes × 2 formats) parse against the preset schema; `SceneRenderer` renders each without a code change to `SceneRenderer.tsx` itself (BR-5's "adding a class = adding a preset json" holds).
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/presets/layouts packages/remotion-templates/src/primitives && git commit -m "feat(remotion): 2-6 add 6 data/structure layout presets x 2 formats + new primitives"` → `git push`

### Step 6: SceneForm controls + gallery override in editor
- **Files:** `frontend/src/components/scene-form/` (per `context/folder-structure.md`), editor gallery component
- **Do:** Add a `SceneForm` control per new element type (editable table for chart points/table rows/list items, per the UI/UX note), and wire the layout gallery's optgroup select so overriding a scene's layout class to e.g. `Chart` swaps the form to the matching bảng-nhập-points control and updates the `ScenePlayer` (2-3) immediately.
- **Verify:** component test: selecting `Chart` in the gallery override control renders the chart-points table form and re-mounts `ScenePlayer` with updated props (covers AC-6).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/scene-form && git commit -m "feat(editor): 2-6 add SceneForm controls + gallery override for 6 new classes"` → `git push`

### Step 7: Fixtures (share pool with 2-1) + render test matrix (11 class × 2 format)
- **Files:** `packages/remotion-templates/schema/fixtures/*.json` (added to 2-1's shared pool), `packages/remotion-templates/src/__tests__/render-matrix.test.ts`
- **Do:** Add one valid fixture per new class plus invalid fixtures for each new validator rule (chart 7-points, table label 25 chars, quote without source_id) into the same shared fixture pool used by 2-1's pytest+vitest tests (per Test Notes: "Fixtures 6 layout vào bộ share (2.1)"). Extend the render test matrix to the full 11 classes × 2 formats = 22 combinations, run nightly (fast CI path stays 1 combination per PR, consistent with 2-2's convention).
- **Verify:** `npx vitest run render-matrix.test.ts` (nightly config) → 22/22 combinations render at correct resolution with count-up/bar-grow/stagger animations completing at their `end_by_ms`/`enter_at_ms` marks (covers AC-1).
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/schema/fixtures packages/remotion-templates/src/__tests__/render-matrix.test.ts && git commit -m "test(remotion): 2-6 add 6-class fixtures + 22-combination nightly render matrix"` → `git push`

### Step 8: Pipeline sanity check — enable 6 classes in Classifier rule table (manual/semi-automated, AC-5)
- **Files:** `backend/app/pipeline/nodes/layout_classifier.py` (per `context/folder-structure.md` node placement — this task only flips the rule-table config per BR-5, it does not build the classifier itself, which is task 4-6)
- **Do:** Per BR-5, a new class only becomes selectable by the Layout Classifier once it has passed the full render-test-and-auto-shrink bar — after Step 7 passes, enable the 6 new classes in the classifier's rule table config (the classifier itself, owned by 4-6, must already exist as a dependency; if 4-6 isn't done yet, this step is blocked — check `sprint-status.yaml` and mark blocked rather than building the classifier here). Run the pipeline against 3 real topics via local Ollama and confirm the classifier selects ≥3 of the new classes appropriately based on content semantics (AC-5) — this is a manual/semi-automated acceptance step, not a unit test; record the run's output scene JSONs and confirm each passes strict validation.
- **Verify:** 3 pipeline runs against real topics → resulting `scene_set` is strict-valid for each, and across the 3 runs at least 3 distinct new classes were chosen by the classifier (not hardcoded — AI never sees the layout list, per the note in AC-5).
- **On failure:** if blocked on the 4-6 dependency not being done yet, mark this step `blocked` in the state file with that reason, leave Steps 1–7 as `done`, and move to a different unblocked task — don't build the classifier inline to unblock this step (scope creep beyond this task's boundary).
- **Commit:** `git add backend/app/pipeline/nodes/layout_classifier.py && git commit -m "feat(pipeline): 2-6 enable 6 new classes in Layout Classifier rule table (BR-5)"` → `git push`

### Step 9: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/schemas/test_scene_v2_elements.py`, `backend/tests/unit/motion/test_list_stagger.py` (mirrors module under test per `rules/folder-structure.md`)
- **Do:** Confirm each Acceptance Criterion has an explicit test: AC-1 (Step 7), AC-2 (Step 4), AC-3 (Step 2), AC-4 (Step 2), AC-5 (Step 8, documented as a manual/semi-automated acceptance run since it depends on a live Ollama pipeline), AC-6 (Step 6). Fill any gap found during this review.
- **Verify:** full test suite for this task's touched paths (`pytest backend/tests/unit/schemas backend/tests/unit/motion -v && npx vitest run` in `packages/remotion-templates`) → all pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests/unit/schemas backend/tests/unit/motion && git commit -m "test(scene): 2-6 close remaining acceptance-criteria test gaps"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixtures vào bộ share (2-1); render test matrix nightly 22 tổ hợp; unit stagger-mapping là pure function.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/2-6.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/2-6.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
