# Task 10-1: Multi-format render production

**Points:** 3đ · **Epic:** 10 — Release · **Depends:** 6-2, 2-2 · **FR:** FR-11
**State file:** [`state/10-1.json`](state/10-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/10-1-multi-format-render-production` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want một dự án xuất được cả bản dọc lẫn ngang, so that cùng một nội dung phủ TikTok/Shorts lẫn YouTube dài mà không làm lại.

## Why
FR-11 multi-format — nhân đôi giá trị mỗi video sản xuất. Template responsive đã dựng từ 2-2; task này đưa nó thành luồng sản phẩm hoàn chỉnh.

## Scope
**In:** nghiệm thu production template 16:9; projects.formats nhiều giá trị; render batch per-format (cache riêng — 6-2 engine sẵn); UI: chọn format khi tạo (1-3 có sẵn) + "＋ Tạo bản 16:9" tại tab Xuất bản; publish tự chọn format hợp nền tảng (8-1 BR-3).
**Out:** format vuông 1:1 (v1.1 nếu cần); layout khác nhau per-format (template responsive đủ).

## Business Rules
1. Thêm format sau không đụng cache format cũ.
2. Mỗi format trạng thái render/download độc lập trên UI.
3. Asset orientation: format ngang ưu tiên ảnh ngang — produce re-resolve asset thiếu orientation (cờ cảnh báo nếu phải dùng ảnh dọc crop).

## Acceptance Criteria
1. **(happy)** Cùng scene_set 2 format → PO duyệt chất lượng cả hai.
2. **(biên/BR-1)** Thêm 16:9 vào project 9:16 done → chỉ render 16:9; cache 9:16 nguyên.
3. **(BR-3)** Cảnh có ảnh dọc sang 16:9 → cờ cảnh báo crop; picker gợi ý tìm ảnh ngang.
4. **(publish)** YouTube chọn 16:9; platform dọc chọn 9:16 tự động.

## Data & API
projects.formats[] (schema sẵn); render §7 nhận formats. Contract change: không.

## Decisions already locked
- 2 format v1 (dọc + ngang) — vuông khi có nhu cầu thật.

## Execution Steps

Work these in order. Update `state/10-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Confirm 16:9 production template + cache_key format isolation (BR-1)
- **Files:** `packages/remotion-templates/` (16:9 composition path), `backend/app/pipeline/render/cache.py` (or wherever `cache_key` is computed per `rules/performance.md`).
- **Do:** Verify the 16:9 template that came out of 2-2 is production-grade (not a dev spike) across all 11 layout classes. Confirm `cache_key = sha256(canonical_scene_json + template_version + format)` already includes `format` (per `rules/performance.md`) — this is what makes BR-1 ("adding a format later doesn't touch the old format's cache") true by construction. If `format` is missing from the cache key, that's a blocking bug in 6-2's engine, not something to patch here — flag it and fix the cache-key computation as step 1a before continuing.
- **Verify:** existing 2-2 render test matrix run for 16:9 across all layout classes passes; a manual diff shows the 9:16 cache entries are untouched after a 16:9-only render.
- **On failure:** transient (render worker flake) → retry 3× short backoff; cache-key bug → not transient, invoke `systematic-debugging`, this is high-risk per `rules/performance.md` ("changes to cache-key logic as high-risk") — fix + add a regression test before proceeding.
- **Commit:** `git add packages/remotion-templates backend/app/pipeline/render && git commit -m "feat(render): 10-1 verify 16:9 template + cache_key format isolation"` → `git push`

### Step 2: `projects.formats[]` multi-value support in project service
- **Files:** `backend/app/schemas/project.py`, `backend/app/services/project_service.py` (or equivalent per `rules/folder-structure.md`).
- **Do:** Confirm `projects.formats[]` (schema already exists per Data & API note — no contract change) accepts multiple format entries and that adding a format to an existing project only enqueues render jobs for the *new* format, never re-triggering the existing one. No DB migration needed since the field already exists.
- **Verify:** unit test — create project with `formats=["9:16"]`, add `"16:9"` after status=done, assert only one new render job is enqueued (for 16:9) and existing 9:16 scene cache entries are unchanged.
- **On failure:** same retry/debugging policy as Step 1.
- **Commit:** `git add backend/app/schemas/project.py backend/app/services/project_service.py tests/unit && git commit -m "feat(project): 10-1 support adding formats post-hoc without touching existing cache" && git push`

### Step 3: Per-format render batch + independent UI status (BR-2)
- **Files:** `backend/app/pipeline/nodes/produce.py` (or the render orchestration node), frontend `src/app/projects/[id]/` publish tab component.
- **Do:** Render batch dispatches one job group per format (reuses 6-2 orchestrator, per-format cache already established in Step 1). Publish tab UI tracks and displays state independently per format: ○ chưa tạo · ● đang · ✓ · ✗ retry (per wireframe in Data & API section).
- **Verify:** manual/E2E — start a 16:9 render on a project whose 9:16 is already ✓; UI shows 9:16 staying ✓ while 16:9 cycles ○→●→✓ independently.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add backend/app/pipeline/nodes/produce.py "src/app/projects/[id]" && git commit -m "feat(publish-ui): 10-1 per-format independent render status" && git push`

### Step 4: Asset orientation re-resolve + crop warning flag (BR-3)
- **Files:** `backend/app/services/asset_service.py` (asset resolution logic), `backend/app/schemas/scene.py` only if a new non-breaking warning field is needed on the render result (not Scene JSON itself — this is a render-time flag, not an AI-authored field, so it does not violate the Layout Engine boundary).
- **Do:** When rendering a horizontal (16:9) format, if a scene's resolved asset is vertical-orientation, attempt re-resolution against the asset library for a horizontal alternative first; only if none exists, fall back to a center-crop and set a `crop_warning: true` flag surfaced to the AssetPicker UI ("gợi ý tìm ảnh ngang").
- **Verify:** unit test — scene with only a vertical asset, render for 16:9 → asset re-resolution attempted, `crop_warning=true` returned when no horizontal alternative exists; a second test confirms no warning when a horizontal alternative is found.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add backend/app/services/asset_service.py tests/unit && git commit -m "feat(assets): 10-1 orientation-aware re-resolve + crop warning for horizontal format" && git push`

### Step 5: Publish auto-selects format per platform (AC4, consumes 8-1 BR-3)
- **Files:** `backend/app/adapters/publish/` (platform capability config consumed here, not redefined), publish trigger service.
- **Do:** When a project has multiple formats rendered, the publish flow auto-selects the format matching the target platform's orientation requirement (YouTube → 16:9, vertical-native platforms → 9:16) using the capability table already established by 8-1 BR-3 — this task only wires the *selection*, it does not redefine platform capabilities.
- **Verify:** unit test — project with both formats ready, publish to YouTube selects the 16:9 render; publish to a vertical platform selects 9:16.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add backend/app/adapters/publish tests/unit && git commit -m "feat(publish): 10-1 auto-select render format by platform orientation" && git push`

### Step 6: Render test matrix acceptance + manual review of 2 videos (DoD)
- **Files:** `backend/tests/integration/render_matrix/` (per `rules/folder-structure.md`), PR description.
- **Do:** Run the full 2-2 layout×format render test matrix promoted to acceptance status for 16:9. Manually review 2 full videos (one per format, same `scene_set`) for visual quality; attach review notes/screenshots to the PR per AC1 ("PO duyệt chất lượng cả hai").
- **Verify:** `make test-render-matrix` (or equivalent per `context/build-process.md`) → all layout×format combinations green; PO sign-off recorded in PR.
- **On failure:** logic/rendering defect → not transient, invoke `systematic-debugging`; still failing after 3 attempts → block task, log in `memory/project-memory.md` Open Questions.
- **Commit:** `git add backend/tests/integration/render_matrix && git commit -m "test(render): 10-1 promote layout×format matrix to acceptance, manual 2-video review" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + render test matrix layout×format từ 2-2 nâng thành nghiệm thu; kiểm tay 2 video.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/10-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/10-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
