# Task 5-5: Màn Hoàn thiện — timeline + BGM + render trigger

**Points:** 5đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1, 2-4, 6-2 (tiến độ thật) · **FR:** FR-10, FR-11
**State file:** [`state/5-5.json`](state/5-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-5-man-hoan-thien` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want tinh chỉnh nhịp, chuyển cảnh, nhạc nền rồi bấm tạo video trên một màn, so that bước cuối gọn trong một chỗ và chỉ render phần thay đổi.

## Why
FR-10 + cửa vào FR-11. Gộp Timeline+Render thành trạm "Hoàn thiện" là quyết định IA từ critique (stepper 5 trạm khớp state machine).

## Scope
**In:** TimelineBar (resize chặn dưới audio+300ms + tooltip; transition tại khớp nối); BGM picker (nguồn 6-5) + volume/fade; tổng thời lượng realtime; nghe thử giọng/cảnh; Play toàn bộ (Player nối cảnh — "bản xem thử", see [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)); khối Tạo video per-format + tiến độ inline (consume 6-2 — mock trước khi 6-2 xong).
**Out:** render logic (6-2); download/publish (6-3); BGM ingest (6-5).

## Business Rules
1. Vào màn chỉ khi mọi cảnh approve (trạm lock + guard API).
2. Resize hiện tooltip lý do chặn dưới ("giọng đọc 5.2s + đệm").
3. Mọi thay đổi ở màn này → cảnh liên quan dirty → nút "Tạo video" đổi nhãn "Tạo lại (2 cảnh thay đổi)".
4. Render đang chạy → điều khiển timeline disabled + giải thích (khớp 6-2 BR-4).

## Acceptance Criteria
1. **(happy)** Kéo 6s→5.5s (audio 5.2) OK; 4s → chặn 5.5 + tooltip; transition đổi nghe/nhìn được khi Play.
2. **(biên/BR-3)** Đổi transition cảnh 3 → chỉ cảnh 3 dirty; nhãn nút "Tạo lại (1 cảnh)".
3. **(lỗi/BR-4)** Đang render → timeline khoá + giải thích; xong → mở lại.
4. **(a11y)** Resize bằng phím hoạt động.
5. **(BGM)** Chọn track + volume → Play nghe được; render có nhạc đúng mức.

## Data & API
Endpoints: GET/PATCH timeline (§6), POST render (§7). Contract change: không.

## Decisions already locked
- "Bản xem thử" Player nối cảnh chấp nhận transition xấp xỉ. Nhãn UI ghi rõ.

## Execution Steps

Work these in order. Update `state/5-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit. **Note:** this task depends on `6-2` for real render progress — if `6-2` isn't `done` yet in `sprint-status.yaml` when you reach Step 5/6, use the mocked SSE fixture (interface already locked via the event catalog) rather than blocking the whole task; record that decision in the state file's `decisions[]`.

### Step 1: Route guard (BR-1) — Hoàn thiện station lock
- **Files:** `frontend/src/app/projects/[id]/finishing/page.tsx`, station-lock check reusing `PipelineStepper` from 5-1
- **Do:** The Hoàn thiện screen is reachable only once every scene is approved (trạm lock in stepper + a server-side guard on the timeline GET endpoint — don't rely on client-side gating alone).
- **Verify:** `pnpm --filter frontend vitest run finishing-guard` → unapproved-scenes case blocks entry with the correct tooltip/redirect.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/app/projects/[id]/finishing && git commit -m "feat(workspace): 5-5 finishing screen route guard BR-1" && git push`

### Step 2: TimelineBar — resize with audio-length floor (BR-2)
- **Files:** `frontend/src/components/workspace/TimelineBar.tsx`, `frontend/src/components/workspace/TimelineBlock.tsx`, `frontend/tests/unit/components/TimelineBar.test.tsx`
- **Do:** Each scene block resizable down to `audio_duration + 300ms`, not below; resize attempts below that floor snap back and show a tooltip stating the reason (e.g. "giọng đọc 5.2s + đệm"). Transition picker lives at each block junction (standard menu, not custom widget — a11y). Resize also operable via keyboard: select block → ±100ms via ←/→ (AC-4).
- **Verify:** `pnpm --filter frontend vitest run TimelineBar` → covers floor-enforced-with-tooltip and keyboard-resize cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/TimelineBar.tsx frontend/src/components/workspace/TimelineBlock.tsx frontend/tests/unit/components/TimelineBar.test.tsx && git commit -m "feat(workspace): 5-5 TimelineBar resize floor + keyboard" && git push`

### Step 3: BGM picker + volume/fade
- **Files:** `frontend/src/components/workspace/BgmPicker.tsx`
- **Do:** BGM source list (consumes the library from 6-5 — if not yet `done`, use its already-agreed API shape against a fixture, note the dependency status in state `decisions[]`), volume slider, fade in/out controls. Selecting a track + adjusting volume must be audible via the Play-all preview (Step 4).
- **Verify:** `pnpm --filter frontend vitest run BgmPicker` → volume/fade state persists to timeline PATCH payload correctly.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/BgmPicker.tsx && git commit -m "feat(workspace): 5-5 BGM picker volume+fade" && git push`

### Step 4: Total duration (realtime) + Play-all preview
- **Files:** `frontend/src/components/workspace/TotalDurationBadge.tsx`, `frontend/src/components/workspace/PlayAllPreview.tsx` (Player concatenation, per `patterns/scene-video-composition-split.md` — "bản xem thử" with approximate transitions, per the locked decision)
- **Do:** Realtime total-duration readout as timeline changes; a Play-all control that concatenates the Remotion `<Player>` across scenes for a preview (explicitly labeled in the UI as an approximate preview — transitions may not be frame-exact, per the locked decision). Also wire "nghe thử giọng/cảnh" (per-scene audio preview).
- **Verify:** `pnpm --filter frontend typecheck` → exit 0; manual dev-server check that duration updates live while resizing.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/TotalDurationBadge.tsx frontend/src/components/workspace/PlayAllPreview.tsx && git commit -m "feat(workspace): 5-5 realtime duration + play-all preview" && git push`

### Step 5: Dirty tracking (BR-3) — "Tạo lại (N cảnh thay đổi)"
- **Files:** `frontend/src/lib/state/finishingDirtyTracker.ts`, `frontend/tests/unit/state/finishingDirtyTracker.test.ts`
- **Do:** Any timeline/BGM/transition change marks the affected scene(s) dirty; the "Tạo video" button label reflects the dirty count ("Tạo lại (N cảnh thay đổi)") vs. the first-render label.
- **Verify:** `pnpm --filter frontend vitest run finishingDirtyTracker` → changing one transition marks exactly that scene dirty, label updates to "(1 cảnh)".
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/lib/state/finishingDirtyTracker.ts frontend/tests/unit/state/finishingDirtyTracker.test.ts && git commit -m "feat(workspace): 5-5 dirty tracking + Tao video label" && git push`

### Step 6: Render trigger block + inline progress (BR-4, consumes 6-2)
- **Files:** `frontend/src/components/workspace/RenderTriggerBlock.tsx`, `frontend/src/lib/sse.ts` (existing SSE client from 1-6), mock SSE fixture under `tests/fixtures/render-progress-sse.ts` if `6-2` isn't done yet
- **Do:** "Tạo video" per output format, inline progress consuming SSE events (real if `6-2` is done; mocked fixture otherwise per the locked event-catalog interface). While a render is running, disable timeline controls and show why (BR-4, matches 6-2 BR-4).
- **Verify:** `pnpm --filter frontend vitest run RenderTriggerBlock` → covers in-progress-disables-timeline and completion-reenables cases against the SSE fixture.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/RenderTriggerBlock.tsx frontend/src/lib/sse.ts tests/fixtures/render-progress-sse.ts && git commit -m "feat(workspace): 5-5 render trigger + inline progress" && git push`

### Step 7: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/...`, `tests/e2e/finishing.spec.ts`
- **Do:** One test per AC above. Then **exercise the feature in a real running browser (dev server)**: resize a block down to the audio floor and confirm the tooltip and snap-back; change a transition and confirm only that scene shows dirty; pick a BGM track, adjust volume, and confirm it's audible on Play-all; trigger a render (against mock or real 6-2) and confirm timeline controls lock during the run.
- **Verify:** `pnpm --filter frontend test:e2e -- finishing` → all AC-mapped tests pass; manual dev-server walkthrough confirms no console errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-5 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock render progress qua SSE fixture khi 6-2 chưa xong (interface đã chốt event-catalog).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
