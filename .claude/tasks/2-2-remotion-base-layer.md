# Task 2-2: Remotion base layer — SceneRenderer + primitives + 5 preset cơ bản + theme

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-1 · **FR:** FR-08, FR-11
**State file:** [`state/2-2.json`](state/2-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/2-2-remotion-base-layer` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a viewer, I want video có bố cục đẹp nhất quán trên cả khung dọc lẫn ngang, so that nội dung trông chuyên nghiệp trên mọi nền tảng.

## Why
Tầng hiện thực Remotion của Layout Engine — [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md): **không có composition cứng per-layout**, chỉ 1 `SceneRenderer` đọc preset (data). **Invoke Remotion Agent Skill `/remotion-markup` before writing** (dev-guide.md §2.1).

## Scope
**In:** `SceneRenderer` = `<Composition>` thật của Remotion với `schema` (Zod, 2-1) + `calculateMetadata` resolve width/height/durationInFrames động (`docs/specs/remotion-integration.md` §2.1); mỗi track MotionPlan render bằng `<Sequence from={ms→frames} durationInFrames layout="none">` (bắt buộc `layout="none"` — mặc định Sequence bọc AbsoluteFill phá preset flex); primitives cơ bản `Heading/Body/Media(kenburns)/Subtitle/Watermark` (`**bold**` → highlight); `motion/Animated` wrapper dùng `interpolate()`/`spring()` thật + bảng preset khởi điểm; `ThemeProvider` + theme mặc định; **5 preset json** Hero/TextFocus/MediaFull/MediaText/Comparison (mỗi preset × 2 format); `supportedSchemaRange`; render CLI; render test class×format + golden-frame.
**Out:** primitives dữ liệu + 6 preset + motion đặc thù (2-6); theme 2-3 (10-2); transition ngoài enum v1; watermark/intro-outro tuỳ chỉnh (v1.1).

## Business Rules
1. Template không fetch mạng — mọi media là đường dẫn cục bộ trong props (see [anti-patterns/render-worker-external-fetch.md](../anti-patterns/render-worker-external-fetch.md)).
2. Text tràn → auto-shrink tới 60% cỡ gốc rồi ellipsis — không bao giờ vỡ khung.
3. Scene ngoài schema range → throw mã `SCHEMA_RANGE`, không render-sai-lặng-lẽ.
4. Font nhúng trong package (Inter + font Việt fallback) — render không phụ thuộc font hệ thống.
5. Mỗi layout = constraint preset flexbox dạng data (slots/gap/padding), không toạ độ tuyệt đối; thêm class mới = thêm preset json — SceneRenderer không đổi.
6. Primitive không biết layout — chỉ render nội dung + motion trong slot; mọi animation qua `Animated` wrapper.
7. Ease mặc định `cubic-bezier(0.16,1,0.3,1)`; duration entrance 450–600ms (dial 4-7 mặc định); theme khai `motion_intensity`/`visual_density` — `Animated` đọc dial để scale duration.

## Acceptance Criteria
1. **(happy)** Fixture mỗi layout render 2 format: đúng resolution, duration ±100ms; PO duyệt visual (10 ảnh trong PR).
2. **(biên/BR-2)** Heading 200 ký tự → shrink+ellipsis không tràn (snapshot test).
3. **(biên)** Cùng scene 9:16 vs 16:9 → bố cục responsive đúng thiết kế từng layout.
4. **(lỗi/BR-3)** Scene 2.0.0 vào template ^1.0 → lỗi SCHEMA_RANGE.
5. **(BR-4)** Render trong container sạch không font hệ thống → chữ Việt đúng (có dấu).

## Decisions already locked
- ⏳ Đếm số cho `stat` chỉ khi content là số thuần — text lẫn số thì hiện tĩnh.

## Execution Steps

Work these in order. Update `state/2-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit. **Before any step that writes Remotion composition/primitive/preset code, invoke the `/remotion-markup` Agent Skill first** per `docs/dev-guide.md` §2.1 — this is a Definition-of-Done requirement (PR must state the skill was invoked), not optional.

### Step 1: Scaffold `packages/remotion-templates` package + Root.tsx stub
- **Files:** `packages/remotion-templates/package.json`, `packages/remotion-templates/src/Root.tsx`, `packages/remotion-templates/tsconfig.json`
- **Do:** Invoke `/remotion-create` (first-time package/composition scaffold, per dev-guide.md §2.1 skill table) to scaffold the package skeleton per `context/folder-structure.md` layout (`src/SceneRenderer.tsx`, `src/primitives/`, `src/motion/`, `src/theme/`, `src/presets/layouts/`, `src/schema.ts`). Do not fork a second template implementation — this package is shared between the Player (2-3) and render-worker.
- **Verify:** `cd packages/remotion-templates && npm install && npx tsc --noEmit` → exits 0.
- **On failure:** transient (npm registry) → retry same step up to 3×, log attempt in state file; logic/config error → stop retrying, invoke `systematic-debugging` skill; still failing after 3 → mark step + task `blocked`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add packages/remotion-templates/package.json packages/remotion-templates/tsconfig.json packages/remotion-templates/src/Root.tsx && git commit -m "feat(remotion): 2-2 scaffold remotion-templates package (via /remotion-create)"` → `git push`

### Step 2: `SceneRenderer` composition + `calculateMetadata`
- **Files:** `packages/remotion-templates/src/SceneRenderer.tsx`
- **Do:** Invoke `/remotion-markup` first. Implement `SceneRenderer` as the real Remotion `<Composition>` — `schema` prop is the Zod schema generated in 2-1 (`packages/remotion-templates/src/schema.ts`, never hand-edited per `rules/type-safety.md`), `calculateMetadata` resolves `width`/`height`/`durationInFrames` dynamically from `format`/`duration_ms` per `docs/specs/remotion-integration.md` §2.1 — do not hand-roll this resolution logic outside Remotion's own mechanism. There is exactly one composition per scene (`SceneRenderer`) — never one composition per layout class, per `rules/folder-structure.md`.
- **Verify:** `npx tsc --noEmit` in the package → exits 0; a minimal Remotion Studio smoke load (`npx remotion studio` briefly, or a headless metadata resolution unit test) confirms `calculateMetadata` returns correct dims for a 9:16 fixture and a 16:9 fixture.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/SceneRenderer.tsx && git commit -m "feat(remotion): 2-2 add SceneRenderer composition with calculateMetadata"` → `git push`

### Step 3: MotionPlan track rendering via `<Sequence layout="none">`
- **Files:** `packages/remotion-templates/src/SceneRenderer.tsx`, `packages/remotion-templates/src/motion/Animated.tsx`
- **Do:** Render each MotionPlan track as `<Sequence from={msToFrames(...)} durationInFrames={...} layout="none">` — `layout="none"` is mandatory (default `Sequence` wraps content in an `AbsoluteFill` that overlaps and breaks the flex preset, per BR — see [rules/code-review.md](../rules/code-review.md) which explicitly flags this as a reject-on-sight review item, not a nitpick). Implement `motion/Animated` wrapper using Remotion's real `interpolate()`/`spring()` (`docs/specs/remotion-integration.md` §2.3) plus a starting preset table; ease default `cubic-bezier(0.16,1,0.3,1)`, entrance duration 450–600ms scaled by the theme's `motion_intensity`/`visual_density` dial (BR-7) — never hardcode one duration value.
- **Verify:** unit test rendering a 2-track scene fixture, asserting each `<Sequence>` receives `layout="none"` and frame offsets match `ms → frames` conversion at the fixture's fps.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/SceneRenderer.tsx packages/remotion-templates/src/motion/Animated.tsx && git commit -m "feat(remotion): 2-2 add MotionPlan track rendering (layout=none, Animated wrapper, BR-7 dial)"` → `git push`

### Step 4: Primitives — Heading/Body/Media(kenburns)/Subtitle/Watermark
- **Files:** `packages/remotion-templates/src/primitives/Heading.tsx`, `Body.tsx`, `Media.tsx`, `Subtitle.tsx`, `Watermark.tsx`
- **Do:** One component per component-kind, per `rules/folder-structure.md` ("never create a composition per layout class — one component per component-kind"). Primitives are layout-blind: they render content + motion in the slot they're given and never author their own `spring()`/`interpolate()` calls — all animation flows through the `Animated` wrapper from Step 3 (BR-6). `Body`/`Heading` parse `**bold**` markdown into a highlight span. `Media` implements Ken Burns pan/zoom. Text overflow: auto-shrink to 60% of original size, then ellipsis — never overflow the frame (BR-2).
- **Verify:** `npx tsc --noEmit` exits 0; snapshot test rendering `Heading` with a 200-character string confirms shrink+ellipsis and no overflow (covers AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/primitives && git commit -m "feat(remotion): 2-2 add base primitives (Heading/Body/Media/Subtitle/Watermark, BR-2 auto-shrink)"` → `git push`

### Step 5: ThemeProvider + default theme (fonts embedded, BR-4)
- **Files:** `packages/remotion-templates/src/theme/ThemeProvider.tsx`, `packages/remotion-templates/src/theme/themes/default.json`, `packages/remotion-templates/assets/fonts/`
- **Do:** Implement `ThemeProvider` reading design tokens (per `docs/backlog/epic-02-scene-remotion.md` "UI/UX" — theme video ăn theo tokens §2 design-system) and declaring `motion_intensity`/`visual_density` dials consumed by `Animated` (Step 3). Embed Inter + a Vietnamese-diacritics-safe fallback font inside the package (not relying on system fonts) per BR-4 — render must not depend on host fonts.
- **Verify:** render a fixture scene with Vietnamese diacritics (e.g. "Xin chào các bạn") in a clean container without system fonts installed (Docker or equivalent per `context/build-process.md` once available) → diacritics render correctly (covers AC-5).
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/theme packages/remotion-templates/assets/fonts && git commit -m "feat(remotion): 2-2 add ThemeProvider + embedded fonts (BR-4)"` → `git push`

### Step 6: 5 constraint presets (Hero/TextFocus/MediaFull/MediaText/Comparison) × 2 formats
- **Files:** `packages/remotion-templates/src/presets/layouts/hero.9x16.json`, `hero.16x9.json`, `text-focus.9x16.json`, `text-focus.16x9.json`, `media-full.*.json`, `media-text.*.json`, `comparison.*.json`
- **Do:** Invoke `/remotion-markup` if not already active for this session. Each preset is DATA (flexbox slots/gap/padding + responsive rules per `docs/specs/layout-engine.md` §6–7), never a TSX component (per `rules/folder-structure.md`: "Layout constraint presets are DATA, not code"). Adding a class means adding a preset JSON — `SceneRenderer` itself never changes (BR-5).
- **Verify:** `SceneRenderer` loads each preset by layout-class name without a code change; a schema-level test confirms all 10 files (5 classes × 2 formats) parse and satisfy the preset JSON shape.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/presets/layouts && git commit -m "feat(remotion): 2-2 add 5 base layout presets x 2 formats (BR-5)"` → `git push`

### Step 7: `supportedSchemaRange` + SCHEMA_RANGE guard (BR-3) + render CLI
- **Files:** `packages/remotion-templates/package.json` (or a dedicated `src/schemaRange.ts`), `packages/remotion-templates/src/SceneRenderer.tsx`, `render-worker/` CLI entry (per `context/folder-structure.md`)
- **Do:** Declare `supportedSchemaRange` (semver range, e.g. `^1.0.0`) and have `SceneRenderer`/the render CLI throw a `SCHEMA_RANGE` error code when a scene's `schema_version` falls outside it — never silently render a mismatched scene (BR-3). Implement/confirm the render CLI entry point used for local render smoke tests.
- **Verify:** feed a scene fixture with `schema_version: "2.0.0"` against `supportedSchemaRange: "^1.0.0"` → CLI/renderer throws with error code `SCHEMA_RANGE` (covers AC-4); feed a valid `1.0.0` fixture → renders successfully.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates render-worker && git commit -m "feat(remotion): 2-2 add supportedSchemaRange guard (BR-3) + render CLI"` → `git push`

### Step 8: Wire up render tests (class×format matrix) + golden-frame + all Acceptance Criteria
- **Files:** `packages/remotion-templates/src/__tests__/render.test.ts`, `packages/remotion-templates/src/__tests__/__golden__/`
- **Do:** One test per Acceptance Criterion: AC-1 (each of the 5 layouts × 2 formats renders at correct resolution, duration ±100ms of the fixture's `duration_ms` — golden-frame comparison for the fast CI path: 1 layout × 1 format per PR per Test Notes, full 10-combination matrix nightly), AC-2 (covered by Step 4's shrink/ellipsis snapshot), AC-3 (9:16 vs 16:9 responsive layout differs per preset design), AC-4 (covered by Step 7), AC-5 (covered by Step 5). Capture baseline screenshots for visual regression (10 images, one per class×format) and attach to the PR per the "UI/UX" note in `docs/backlog/epic-02-scene-remotion.md` (PO visual approval).
- **Verify:** `npx vitest run render.test.ts` → all AC-mapped tests pass; render CLI smoke run produces MP4/frame output for at least 1 class×format combination without error.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/__tests__ && git commit -m "test(remotion): 2-2 cover all acceptance criteria (AC-1..AC-5) + golden-frame baseline"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + render test CI 1 layout×1 format/PR (nhanh), đủ 10 tổ hợp nightly; baseline screenshot cho visual regression. PR states which Remotion Skill was invoked.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/2-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/2-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
