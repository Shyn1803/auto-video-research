# Task 2-5: Subtitle từ timestamps + burn vào video

**Points:** 3đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-2, 2-4 · **FR:** FR-19
**State file:** [`state/2-5.json`](state/2-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/2-5-subtitle-tu-timestamps` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a viewer, I want phụ đề khớp chính xác lời đọc, so that xem không bật tiếng (đa số trên mobile) vẫn hiểu trọn nội dung.

## Why
70-80% video mạng xã hội được xem không tiếng — subtitle sync là điều kiện sống của định dạng, không phải tính năng phụ.

## Scope
**In:** **kiểm tra `@remotion/captions` trước** (Remotion Agent Skill `/remotion-captions` — dev-guide.md §2.1) — nếu khớp constraint §3.6 scene-json-schema thì dùng package chính chủ; nếu không khớp (ví dụ "không tách cụm số+đơn vị" tiếng Việt), giữ thuật toán tự viết: nhóm timestamps → segments (≤42 ký tự/dòng, cắt ranh giới từ, ưu tiên dấu câu); component subtitle style `line`; sinh segments lúc chuẩn bị props (không lưu trong Scene JSON — spec §3.4); unit test thuật toán.
**Out:** karaoke style (schema v2); vị trí/size subtitle tuỳ chỉnh (v1.1); file .srt xuất riêng (v1.1).

## Business Rules
1. Không tách cụm số+đơn vị ("92,5 phần trăm" nguyên vẹn 1 segment).
2. Segment hiển thị tối thiểu 700ms — ngắn hơn gộp với segment kế.
3. `subtitle.enabled=false` → không render, không chừa khoảng trống.
4. Segment vượt 42 ký tự do 1 từ quá dài → cho phép tràn mềm (không cắt giữa từ).

## Acceptance Criteria
1. **(happy)** Cảnh 6s → phụ đề đúng thời điểm (lệch ≤200ms), 1 dòng, không tràn safe-area.
2. **(biên/BR-1)** "92,5 phần trăm" nguyên cụm 1 segment.
3. **(biên/BR-2)** Từ đơn 300ms → gộp, không nháy.
4. **(BR-3)** Tắt subtitle → khung hình dùng trọn không gian.
5. **(unit)** Bộ test câu dài/số/từ ghép/dấu câu pass.

## Decisions already locked
- Subtitle bật mặc định mọi cảnh có voice (mobile-first).

## Execution Steps

Work these in order. Update `state/2-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Evaluate `@remotion/captions` against scene-json-schema §3.6 constraints
- **Files:** none (research/decision step — record outcome in `state/2-5.json` `decisions[]` and this file's Decisions section if it changes the plan)
- **Do:** Invoke the `/remotion-captions` Agent Skill first (dev-guide.md §2.1 — mandatory before writing subtitle code, and this task's Scope explicitly requires checking the package before hand-rolling anything). Compare `@remotion/captions`'s grouping behavior against `docs/specs/scene-json-schema.md` §3.6 constraints, in particular BR-1 (never split a number+unit cluster like "92,5 phần trăm"). If `@remotion/captions` satisfies all constraints, use it directly and skip Step 2's custom algorithm (adjust downstream steps accordingly, note the decision). If it doesn't (the Vietnamese number+unit rule is the likely gap called out in the Scope), proceed with the custom algorithm in Step 2.
- **Verify:** a short spike script/test exercising `@remotion/captions` against a "92,5 phần trăm" fixture — passes (package usable) or fails (custom algorithm needed) with a clear recorded reason either way.
- **On failure:** transient (package install) → retry same step up to 3×, log attempt in state file; a genuine incompatibility is not a "failure" — it's an expected decision outcome, record it and move to Step 2.
- **Commit:** `git add packages/remotion-templates/spike-captions-eval.md` (or wherever the spike note lives) `&& git commit -m "docs(subtitle): 2-5 evaluate @remotion/captions vs BR-1 (decision recorded)"` → `git push`

### Step 2: Custom segmentation algorithm (only if Step 1 concluded `@remotion/captions` doesn't fit)
- **Files:** `packages/remotion-templates/src/subtitle/segmentTimestamps.ts` (or `backend/app/services/subtitle_segmentation.py` if segmentation happens backend-side per the actual props-preparation location — check `docs/specs/scene-json-schema.md` §3.4 for where segments are generated)
- **Do:** Implement a pure function grouping word timestamps into segments: ≤42 characters/line, cut only at word boundaries, prefer punctuation boundaries, never split a number+unit cluster (BR-1), minimum 700ms display per segment — merge a too-short segment with the next (BR-2), allow soft overflow past 42 chars only when caused by a single long word, never cut mid-word (BR-4). Segments are generated at props-preparation time, not stored in Scene JSON (per Scope note, spec §3.4).
- **Verify:** unit test feeding a timestamp array through the function and asserting segment boundaries respect all four rules on a handful of representative inputs.
- **On failure:** same policy as Step 1 (transient/logic split), invoking `systematic-debugging` for logic errors.
- **Commit:** `git add packages/remotion-templates/src/subtitle/segmentTimestamps.ts && git commit -m "feat(subtitle): 2-5 add custom timestamp segmentation algorithm (BR-1,2,4)"` → `git push`

### Step 3: `Subtitle` `line` style component + enabled/disabled (BR-3)
- **Files:** `packages/remotion-templates/src/primitives/Subtitle.tsx` (extends the primitive scaffolded in 2-2)
- **Do:** Invoke `/remotion-markup` before touching this component (composition/primitive change, dev-guide.md §2.1). Implement the `line` subtitle style: dark translucent background, white text, positioned inside the safe area avoiding TikTok/YouTube UI chrome, per the UI/UX note. When `subtitle.enabled=false`, render nothing and reserve no layout space (BR-3) — this must not leave an empty gap in the flex slot.
- **Verify:** snapshot test with `subtitle.enabled=false` confirms no DOM node/space reserved (covers AC-4); snapshot with `enabled=true` shows the line positioned within the safe area.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/primitives/Subtitle.tsx && git commit -m "feat(subtitle): 2-5 add line-style subtitle component (BR-3 enabled/disabled)"` → `git push`

### Step 4: Wire segments into `SceneRenderer` props preparation
- **Files:** wherever scene props are assembled before being passed to `SceneRenderer` (per 2-2/2-3's actual location, likely `backend/app/services/scene_props.py` or a frontend equivalent)
- **Do:** Call the segmentation function (Step 1's `@remotion/captions` path or Step 2's custom function) when assembling render/preview props from a scene's audio timestamps (from 2-4), producing the `Subtitle` component's input. Confirm subtitle is on by default for any scene with voice (per Decisions already locked).
- **Verify:** integration test: a scene fixture with 2-4-shaped word timestamps → props preparation yields subtitle segments matching the chosen algorithm's output.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/scene_props.py packages/remotion-templates/src/SceneRenderer.tsx && git commit -m "feat(subtitle): 2-5 wire segmentation into scene props preparation"` → `git push`

### Step 5: Wire up tests + property test + verify all Acceptance Criteria
- **Files:** `packages/remotion-templates/src/subtitle/__tests__/segmentTimestamps.test.ts`, `packages/remotion-templates/src/primitives/__tests__/Subtitle.test.tsx`
- **Do:** One test per Acceptance Criterion: AC-1 (a 6s scene fixture → subtitle timing within ≤200ms of expected, single line, no safe-area overflow — verify the ≤200ms tolerance and layout bounds programmatically where possible, note the "kiểm tay 3 mẫu" manual portion in the PR), AC-2 (covered by Step 2/BR-1 test), AC-3 (a 300ms single-word segment merges with the next, no flicker — assert merged duration ≥700ms), AC-4 (covered by Step 3), AC-5 (a test suite covering long sentences, numbers, compound words, punctuation per Test Notes). Add the mandatory property test: for every input, the concatenation of all segment texts equals the original text (no characters lost) — per Test Notes and the DoD line below.
- **Verify:** `npx vitest run segmentTimestamps.test.ts Subtitle.test.tsx` → all AC-mapped tests + the property test pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/src/subtitle/__tests__ packages/remotion-templates/src/primitives/__tests__ && git commit -m "test(subtitle): 2-5 cover all acceptance criteria (AC-1..AC-5) + no-text-lost property test"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + property test: mọi input, tổng text segments == text gốc (không mất chữ). PR states which Remotion Skill was invoked / why not used.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/2-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/2-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
