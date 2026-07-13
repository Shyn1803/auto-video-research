# Task 10-2: Bộ template 2-3

**Points:** 3đ · **Epic:** 10 — Release · **Depends:** 2-2 · **FR:** FR-11
**State file:** [`state/10-2.json`](state/10-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/10-2-bo-template-2-3` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

**⚠ Buffer cắt đầu tiên nếu trễ (docs/plan.md §5) — không chặn luồng nào khác nếu deprioritized.**

## User story
As a Content Creator, I want chọn giữa vài phong cách hình ảnh, so that video của kênh không bị một màu khi đăng hàng ngày.

## Why
Rủi ro "mass-produced content" bị nền tảng giảm reach (SRS §12) — đa dạng theme bổ sung cho cơ chế chống lặp layout (4-6 BR-9) đã enforce sẵn ở mọi theme.

## Scope
**In:** 2 theme mới (sáng / gradient động) cùng contract Scene JSON + `supportedSchemaRange`; mỗi theme khai đủ dial `motion_intensity`/`visual_density`/`accent_saturation_max`/`radius_scale` (**bắt buộc, không theme "mặc định ngầm"** — see [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md)); ví dụ: Sáng-tối-giản `(4,3,0.6,soft-16px)`, Gradient-động `(8,4,0.8,pill)`; theme cấp project (chọn khi tạo + đổi trong Phân cảnh có preview); render test matrix mở rộng.
**Out:** theme marketplace/tuỳ chỉnh màu per-project (v1.1); font riêng (v1.1).

## Business Rules
1. Đổi theme không đổi Scene JSON — chỉ mapping visual.
2. Đổi theme → mọi cảnh dirty; cảnh báo "8 cảnh sẽ render lại" trước khi áp.
3. Theme mới phải pass toàn bộ render test matrix (11 layout × 2 format) trước khi vào danh sách chọn.
4. **(video-taste.md §4.3)** 1 accent color/theme (saturation ≤ `accent_saturation_max`), 1 `radius_scale` — áp cho highlight_color, chart highlight point, winner badge trong toàn bộ scene của video; validator cảnh báo nếu scene tự ý set màu ngoài accent theme.

## Acceptance Criteria
1. **(happy)** 3 video cùng nội dung 3 theme khác biệt rõ (PO duyệt).
2. **(biên/BR-2)** Đổi theme → confirm → toàn bộ dirty → render lại đủ.
3. **(BR-3)** CI matrix theme mới xanh trước khi merge.

## Data & API
projects.theme (cột mới → migration); scene render props nhận theme. Contract change: **có** — cột + trường tạo project → cập nhật api-spec §2 + DB schema.

## Decisions already locked
- Theme cấp project, không per-scene (nhất quán video).

## Execution Steps

Work these in order. Update `state/10-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: `projects.theme` migration (contract change)
- **Files:** `app/db/migrations/` (new Alembic revision), `backend/app/schemas/project.py`, `docs/specs/database-schema.md`, `docs/specs/api-spec.md` §2.
- **Do:** Add `projects.theme` column (enum or FK to a themes table — follow existing pattern for similar project-level settings columns). This is a "đổi contract" change per `CLAUDE.md` §4/`rules/documentation.md` — update `docs/specs/database-schema.md` and `docs/specs/api-spec.md` §2 in this same commit, plus a **Contract changes** note in the PR description.
- **Verify:** migration applies cleanly on a fresh DB and on a DB seeded from 2-2 fixtures (`make db-migrate` or equivalent) → exit 0; `docs/` diff reviewed for accuracy.
- **On failure:** migration conflict → not transient, invoke `systematic-debugging`; still failing after 3 attempts → block, log in `memory/project-memory.md`.
- **Commit:** `git add app/db/migrations backend/app/schemas/project.py docs/specs/database-schema.md docs/specs/api-spec.md && git commit -m "feat(db): 10-2 add projects.theme column (contract change)" && git push`

### Step 2: Define theme dial contract for "Sáng-tối-giản" and "Gradient-động" (BR-4, layout-engine §8)
- **Files:** `packages/remotion-templates/src/presets/themes/sang-toi-gian.json`, `.../gradient-dong.json` (or wherever theme presets live per `rules/folder-structure.md` — presets are DATA, not TSX).
- **Do:** Each theme preset declares ALL required dials explicitly — `motion_intensity`, `visual_density`, `accent_saturation_max`, `radius_scale` — no implicit defaults, per `patterns/layout-engine-resolution.md`. Use the locked example values: Sáng-tối-giản `(motion_intensity=4, visual_density=3, accent_saturation_max=0.6, radius_scale=soft-16px)`; Gradient-động `(8, 4, 0.8, pill)`. Include `supportedSchemaRange` per theme contract requirement in Scope.
- **Verify:** JSON schema validation for theme presets passes (`make validate-theme-presets` or equivalent) → both new theme files pass with zero missing-dial warnings.
- **On failure:** a missing dial is a logic error (not transient) — fix immediately, this is exactly the "mặc định ngầm" bug the scope explicitly forbids.
- **Commit:** `git add packages/remotion-templates/src/presets/themes && git commit -m "feat(themes): 10-2 add sang-toi-gian + gradient-dong dial contracts" && git push`

### Step 3: Accent-color / radius-scale validator (BR-4)
- **Files:** `app/validators/theme_validator.py` (or scene-render-time validator per existing validator location conventions).
- **Do:** Extend/add a validator that flags any scene attempting to set `highlight_color`, chart highlight point, or winner badge color outside the active theme's single accent color (bounded by `accent_saturation_max`), and any scene setting `radius_scale` inconsistent with the theme's single value — per `video-taste.md` §4.3 as referenced in Scope.
- **Verify:** unit test — scene JSON with an out-of-accent color → validator warning raised; in-accent color → no warning.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add app/validators tests/unit && git commit -m "feat(validate): 10-2 enforce single accent color + radius_scale per theme (BR-4)" && git push`

### Step 4: Theme selection UI (create + change with dirty confirm, BR-2)
- **Files:** `src/app/projects/[id]/` create-project flow, Phân cảnh (Scenes) screen theme switcher component.
- **Do:** Theme chooser = 3 thumbnail previews rendering the same sample scene (per UI/UX note). Changing theme on an existing project triggers the BR-2 confirm dialog ("8 cảnh sẽ render lại") before marking all scenes dirty — do not silently mark dirty without the confirm step.
- **Verify:** manual/E2E — switch theme on a project with 8 scenes → confirm dialog appears with correct scene count → confirm → all 8 scenes flip to dirty status; cancel → no scenes marked dirty.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add "src/app/projects/[id]" && git commit -m "feat(ui): 10-2 theme selector with dirty-confirm on change (BR-2)" && git push`

### Step 5: BR-1 regression guard — theme change never touches Scene JSON
- **Files:** `backend/tests/unit/theme/`.
- **Do:** Add an explicit regression test asserting a theme change mutates only render/visual mapping, never the underlying Scene JSON content (component-kinds, text, data) — this is the core BR-1 guarantee and the boundary that keeps AI out of layout decisions.
- **Verify:** unit test — apply theme A then theme B to the same Scene JSON, assert `scene_json` bytes are byte-identical across both, only rendered output differs.
- **On failure:** if Scene JSON does mutate, this is a Layout Engine boundary violation — treat as blocking per `rules/architecture.md`, do not merge without fixing.
- **Commit:** `git add backend/tests/unit/theme && git commit -m "test(theme): 10-2 BR-1 regression guard — theme change never mutates Scene JSON" && git push`

### Step 6: Render test matrix (11 layout × 2 format) for both new themes (BR-3) + PR screenshots
- **Files:** `backend/tests/integration/render_matrix/`, PR description.
- **Do:** Run the full 11-layout × 2-format render matrix (from 2-2, extended) against both new themes; a theme only enters the selectable list once its matrix is green (BR-3 — CI gate, not a manual promise). Attach screenshots of 3 videos (same content, 3 themes: default + 2 new) to the PR per Test Notes/AC1.
- **Verify:** `make test-render-matrix THEME=sang-toi-gian` and `THEME=gradient-dong` → both green; PR contains 3-theme comparison screenshots.
- **On failure:** rendering defect in a specific layout → not transient, invoke `systematic-debugging`, fix the theme preset dial causing the failure; still failing after 3 attempts → block task, do not add the theme to the selectable list.
- **Commit:** `git add backend/tests/integration/render_matrix && git commit -m "test(render): 10-2 11×2 matrix green for both new themes (BR-3 gate)" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + tái dùng khung render test 2-2; screenshot 3 theme vào PR.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/10-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/10-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
