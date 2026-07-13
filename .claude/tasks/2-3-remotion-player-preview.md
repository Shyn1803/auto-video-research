# Task 2-3: Remotion Player preview trong Next.js

**Points:** 3đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-2 · **FR:** FR-09, AR-4
**State file:** [`state/2-3.json`](state/2-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/2-3-remotion-player-preview` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want xem phân cảnh ngay trong trình duyệt khi chỉnh sửa, so that vòng lặp chỉnh–xem tính bằng giây thay vì chờ render.

## Why
"Preview tức thì" là NFR-1 và lý do chọn kiến trúc Remotion Player ([decisions/0006-remotion-player-shared-template.md](../decisions/0006-remotion-player-shared-template.md): Player và worker cùng template → preview = render, không lệch pixel). **Invoke `/remotion-interactivity` before writing** (dev-guide.md §2.1).

## Scope
**In:** `ScenePlayer` wrap `<Player>` thật của `@remotion/player` (props: `component`, `inputProps`=scene JSON, `durationInFrames`, `fps`, `compositionWidth/Height` theo format, `controls`, `ref` — `docs/specs/remotion-integration.md` §2.4); import cùng package composition với worker; scrub dùng `playerRef.current.seekTo(frame)`, progress dùng `addEventListener('frameupdate', ...)`; **2 composition riêng trong `Root.tsx`** ([patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)): `Scene` (1 cảnh — dùng ở Phân cảnh 5-1 + render-worker) và `Video` (nối toàn bộ cảnh qua `<Sequence>` + `<Audio>` BGM — chỉ dùng ở Player Hoàn thiện 5-5, KHÔNG bao giờ render thật); lazy-load + skeleton; chế độ frame tĩnh (thumbnail cho 5-1, dùng `seekTo` + capture).
**Out:** editor form (5-1); audio waveform (không cần v1).

## Business Rules
1. Props đổi → re-render ngay (key theo content hash), không giữ state cũ.
2. Chưa có audio produce → phát hình không tiếng + hint; có audio → phát đồng bộ.
3. Bundle Remotion lazy — route không cần preview không tải chunk này.

## Acceptance Criteria
1. **(happy)** Sửa scene JSON state → player cập nhật <100ms không network call.
2. **(biên/BR-2)** Cảnh chưa produce → im lặng + hint; sau produce → có tiếng đúng timing.
3. **(nhất quán)** 1 frame giữa: player vs render CLI cùng scene giống nhau (kiểm tay, ghi vào PR).
4. **(perf/BR-3)** Trang Dashboard không tải remotion chunk (kiểm network).
5. **(lỗi)** Composition throw → error state có mã, app không crash (error boundary).

## Decisions already locked
- Preview "cả video" ở màn Hoàn thiện dùng Player nối cảnh — chấp nhận transition xấp xỉ (transition thật chỉ trong render thật); UI ghi rõ "bản xem thử".

## Execution Steps

Work these in order. Update `state/2-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit. **Invoke `/remotion-interactivity` before writing any Player-driving code** (dev-guide.md §2.1) — this is a DoD requirement (PR must state the skill was invoked).

### Step 1: Two compositions in `Root.tsx` — `Scene` and `Video`
- **Files:** `packages/remotion-templates/src/Root.tsx`
- **Do:** Add `Scene` (single scene — used by the Phân cảnh editor screen 5-1 and the render-worker, this is the composition actually rendered per [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)) and `Video` (all scenes concatenated via `<Sequence>` + `<Audio>` for BGM — used ONLY by the Player on the Hoàn thiện screen 5-5, NEVER rendered for real, per [decisions/0009-scene-video-two-compositions.md](../decisions/0009-scene-video-two-compositions.md)) as two separate registered compositions, both importing the same `SceneRenderer` from 2-2 — no forked template code.
- **Verify:** `npx tsc --noEmit` exits 0; `npx remotion compositions` (or equivalent Studio listing) shows both `Scene` and `Video` registered.
- **On failure:** transient → retry same step up to 3×, log attempt in state file; logic/config error → stop retrying, invoke `systematic-debugging` skill; still failing after 3 → mark step + task `blocked`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add packages/remotion-templates/src/Root.tsx && git commit -m "feat(remotion): 2-3 add Scene and Video compositions (render-worker uses Scene only)"` → `git push`

### Step 2: `ScenePlayer` component wrapping `@remotion/player`
- **Files:** `frontend/src/components/scene-player/ScenePlayer.tsx` (per `context/folder-structure.md` domain-component placement)
- **Do:** Wrap the real `<Player>` from `@remotion/player` per `docs/specs/remotion-integration.md` §2.4: props `component` (the `Scene` composition from Step 1), `inputProps` (scene JSON), `durationInFrames`, `fps`, `compositionWidth`/`compositionHeight` (per `format`), `controls`, and a forwarded `ref`. Import the same package composition used by the render-worker (2-2) — this is what makes preview == render (ADR-6). Key the `<Player>` on a content hash of props so a props change forces a fresh mount instead of stale internal state (BR-1).
- **Verify:** `npx tsc --noEmit` exits 0; component test mounts `ScenePlayer` with a 2-1 fixture and asserts the underlying `<Player>` receives the correct `compositionWidth/Height` for both 9:16 and 16:9 fixtures.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/scene-player/ScenePlayer.tsx && git commit -m "feat(player): 2-3 add ScenePlayer wrapping @remotion/player (BR-1 content-hash key)"` → `git push`

### Step 3: Scrub + progress via `seekTo`/`frameupdate` (no custom tracking)
- **Files:** `frontend/src/components/scene-player/ScenePlayer.tsx`, `frontend/src/components/scene-player/useScenePlayerProgress.ts`
- **Do:** Implement scrubbing via `playerRef.current.seekTo(frame)` and progress tracking via `playerRef.current.addEventListener('frameupdate', ...)` — use Remotion's own mechanisms, don't hand-roll a separate frame-tracking loop (per Scope note in `docs/backlog/epic-02-scene-remotion.md`).
- **Verify:** component test simulates a `seekTo` call and asserts the player's current frame updates; a `frameupdate` event handler test confirms progress state updates without a network call (covers AC-1's "<100ms không network call" — assert via mocked fetch/XHR spy showing zero calls).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/scene-player && git commit -m "feat(player): 2-3 add scrub (seekTo) + progress (frameupdate) tracking"` → `git push`

### Step 4: Audio hint state — no-audio vs produced audio (BR-2)
- **Files:** `frontend/src/components/scene-player/ScenePlayer.tsx`
- **Do:** When a scene has no produced audio yet, play video muted with a visible hint ("chưa tạo giọng đọc"); once audio is produced, play in sync per timestamps. Drive this off the scene JSON's audio metadata field (populated by 2-4's worker), not a separate flag invented here.
- **Verify:** component test with a scene fixture lacking audio metadata → hint element renders, player muted; same fixture with audio metadata populated → hint absent, `<Audio>`/audio track present (covers AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/scene-player/ScenePlayer.tsx && git commit -m "feat(player): 2-3 add no-audio hint state (BR-2)"` → `git push`

### Step 5: Lazy-load + skeleton + error boundary (BR-3, AC-5)
- **Files:** `frontend/src/components/scene-player/ScenePlayer.tsx`, `frontend/src/components/scene-player/ScenePlayerSkeleton.tsx`, `frontend/src/components/scene-player/ScenePlayerErrorBoundary.tsx`
- **Do:** Lazy-load the Remotion Player bundle (`next/dynamic` or equivalent) so routes that don't render `ScenePlayer` (e.g. Dashboard) don't pull in the chunk (BR-3). Add a skeleton sized to the target aspect ratio for the loading state, and a React error boundary around the composition that renders an error state with a code instead of crashing the whole app when the composition throws (AC-5). Per the wireframe states in the backlog doc: default (player) / loading (skeleton at correct format ratio) / empty (no scene selected → guidance) / error (crash → message + code).
- **Verify:** component test forces the lazy import to reject → skeleton then error boundary state render, no unhandled exception propagates past the boundary; `next build` (once app scaffolded) + bundle analyzer confirms the Dashboard route's bundle excludes the Remotion Player chunk (covers AC-4).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/scene-player && git commit -m "feat(player): 2-3 add lazy-load, skeleton, empty/error states (BR-3, AC-4, AC-5)"` → `git push`

### Step 6: Static frame / thumbnail mode
- **Files:** `frontend/src/components/scene-player/useScenePlayerThumbnail.ts`
- **Do:** Implement a static-frame mode for thumbnails (used by the Phân cảnh screen 5-1 scene list): `seekTo` a target frame, then capture it — reuse the same `ScenePlayer`/`Player` instance rather than mounting a second renderer.
- **Verify:** component test calls the thumbnail hook with a target frame and asserts a captured frame/data URL is returned without mounting a second `<Player>` instance.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/scene-player/useScenePlayerThumbnail.ts && git commit -m "feat(player): 2-3 add static frame thumbnail mode"` → `git push`

### Step 7: Wire up tests + verify all Acceptance Criteria + manual player-vs-render-CLI check
- **Files:** `frontend/src/components/scene-player/__tests__/*.test.tsx`
- **Do:** One test per Acceptance Criterion: AC-1 (covered by Step 3), AC-2 (covered by Step 4), AC-3 is a manual, one-time consistency check — render one frame via the 2-2 render CLI and one frame via `ScenePlayer.seekTo` on the same scene fixture, compare visually, and record the result in the PR description (per Test Notes: "kiểm tay, ghi vào PR" — this cannot be fully automated, do it once and document it), AC-4 (covered by Step 5), AC-5 (covered by Step 5).
- **Verify:** `npx vitest run` in `frontend/` for the scene-player test suite → all AC-mapped automated tests pass; PR description includes the AC-3 manual comparison note.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/scene-player/__tests__ && git commit -m "test(player): 2-3 cover all acceptance criteria (AC-1..AC-5)"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + vitest component với fixture 2-1; kiểm bundle bằng next build analyze trong PR đầu. PR states which Remotion Skill was invoked.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/2-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/2-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
