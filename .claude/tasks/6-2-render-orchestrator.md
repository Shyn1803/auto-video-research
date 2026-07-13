# Task 6-2: Render orchestrator + worker in-process + cache + merge

**Points:** 5đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 6-1, 2-2 · **FR:** FR-11
**State file:** [`state/6-2.json`](state/6-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/6-2-render-orchestrator` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want tạo video nhanh nhờ chỉ render phần thay đổi, so that vòng sửa–xem cuối cùng tính bằng chục giây thay vì render lại cả video.

## Why
Hiện thực lời hứa trung tâm của SRS ("scene là đơn vị cache/render độc lập"). **Invoke `/remotion-saas` + `/remotion-render` before writing** (dev-guide.md §2.1). Read [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md) first — render-worker only ever calls `renderMedia()` on the `Scene` composition, never `Video`.

## Scope
**In:** cache_key/cảnh (hash 2-1 + template_version + format); queue in-process (interface NATS-like); song song `RENDER_CONCURRENCY`; worker theo pipeline chính thức Remotion `bundle() → selectComposition() → renderMedia()` (`docs/specs/remotion-integration.md` §2.5) → MinIO; bảng renders + SSE render.progress; merge ffmpeg (concat + BGM volume/fade + CRF); retry từng job; per-format batch.
**Out:** worker container (9-2); multi-format UI (10-1 — engine sẵn); GPU encode (v1.1 nếu benchmark cần).

## Business Rules
1. Job idempotent theo cache_key — trùng → phát hiện qua renders/MinIO, bỏ qua.
2. Job fail không huỷ batch; batch kết thúc khi mọi job xong; trạng thái tổng trung thực ("7/8 + 1 lỗi").
3. Merge chỉ khi 100% cảnh done. **Merge is ffmpeg's job — never a second `renderMedia()` call on a whole-video composition** (see [rules/performance.md](../rules/performance.md)).
4. Sửa cảnh khi đang render → batch hiện tại chạy nốt; cảnh sửa dirty cho batch sau.
5. Output theo layout storage cố định (ARCHITECTURE §6); cache TTL dọn bởi cleanup job.
6. `bundle()` **1 lần lúc khởi động**, cache `serveUrl` in-memory, tái dùng cho mọi job sau đó — không bundle lại mỗi render (see [rules/performance.md](../rules/performance.md), [postmortems/](../postmortems/) bundle-caching gap).

## Acceptance Criteria
1. **(happy)** 8 cảnh 3 dirty → 3 render + 5 cache_hit; MP4 đúng thứ tự, audio sync, BGM fade.
2. **(biên/BR-4)** Sửa cảnh giữa batch → batch xong bình thường; nút "Tạo lại (1 cảnh)" hiện.
3. **(lỗi/BR-2)** 1 cảnh fail → batch kết thúc "7/8 + 1 lỗi"; retry cảnh đó → merge chạy.
4. **(biên/BR-1)** Kill worker giữa job → retry không double-render.
5. **(SSE)** Progress từng cảnh + tổng % đúng.

## Data & API
Bảng: renders. Endpoints §7. Events: render.progress. Contract change: không.

## Decisions already locked
- ⏳ CRF 20, preset medium khởi điểm — tune sau benchmark 6-4.

## Execution Steps

Work these in order. Update `state/6-2.json` after **every** step. **Before Step 1**, invoke `/remotion-saas` and `/remotion-render` per `docs/dev-guide.md` §2.1 and read [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md) — this task is the highest cache-correctness risk in the epic (see [rules/performance.md](../rules/performance.md)).

**Placement judgment call (record in `state/6-2.json` `decisions[]`):** `folder-structure.md` defines `render-worker/` as the eventual Node.js/Remotion-CLI/NATS-consumer directory, extracted as its own container in 9-2. For this task (in-process, no container yet), orchestration/queue/cache-key/DB logic lives in `backend/app/services/render_orchestrator.py` (Python), and the actual Remotion `bundle()/selectComposition()/renderMedia()` calls live in `render-worker/src/` (Node.js), invoked in-process (long-lived child process, not per-job spawn) from the backend — this keeps the Node.js Remotion surface identical to what 9-2 later containerizes, so extraction stays non-breaking per `rules/architecture.md` ("tách theo đo đạc, không tách trước"). This is a reversible/locally-scoped call, not a new decision needing PO sign-off.

### Step 1: Scaffold orchestrator + cache_key
- **Files:** `backend/app/services/render_orchestrator.py`, `backend/app/services/cache_key.py`, `render-worker/src/bundleCache.ts`, `render-worker/src/worker.ts`
- **Do:** implement `compute_cache_key(canonical_scene_json, template_version, format) -> str` = `sha256(...)` per [rules/performance.md](../rules/performance.md) — treat this function as high-risk, a bug here silently defeats the entire cache. Reuse the canonical scene JSON hashing already established in 2-1. Scaffold `render-worker/src/worker.ts` module skeleton (no logic yet).
- **Verify:** `cd backend && python -c "from app.services.cache_key import compute_cache_key"` → exit 0; `cd render-worker && npm run typecheck` → exit 0.
- **On failure:** transient → retry 3×; logic/config → `systematic-debugging` skill; still failing → mark `blocked`, note in `memory/project-memory.md` Open Questions, work a different unblocked task.
- **Commit:** `git add backend/app/services/render_orchestrator.py backend/app/services/cache_key.py render-worker/src/bundleCache.ts render-worker/src/worker.ts && git commit -m "feat(render): 6-2 scaffold orchestrator + cache_key" && git push`

### Step 2: `bundle()` once at startup, cache `serveUrl` (BR-6)
- **Files:** `render-worker/src/bundleCache.ts`, `render-worker/src/worker.ts`
- **Do:** implement a module-level singleton `bundleOnce()` called exactly once when the worker process starts; cache the resulting `serveUrl` in memory; every render job reuses the cached value — **never call `bundle()` inside the per-job render function** (this is the exact gap called out in `docs/specs/remotion-integration.md` §2.5 and [rules/performance.md](../rules/performance.md); don't reintroduce it).
- **Verify:** `cd render-worker && npm test -- bundleCache.test.ts` → a counter wrapper around `bundle()` asserts it is called exactly 1 time across N simulated jobs.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(render): 6-2 bundle() once at startup, cache serveUrl (BR-6)"`

### Step 3: In-process queue, NATS-like interface, bounded concurrency
- **Files:** `backend/app/services/render_orchestrator.py`
- **Do:** implement an in-process async queue whose interface shape mirrors a future NATS consumer (`subscribe`/`ack`/`nack`-equivalent methods) so 9-2's extraction is a deployment change, not an interface rewrite (per `rules/architecture.md`); bound parallelism via `RENDER_CONCURRENCY` (config through the typed settings object, never read directly from env in the queue).
- **Verify:** `cd backend && pytest backend/tests/unit/services/test_render_orchestrator.py::test_concurrency_bound -v` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(render): 6-2 in-process queue with NATS-like interface"`

### Step 4: cache_key idempotency — skip on cache hit (BR-1)
- **Files:** `backend/app/services/render_orchestrator.py`, `backend/app/models/renders.py` (per `docs/specs/database-schema.md` §2.5 `renders` table)
- **Do:** before enqueuing a scene render job, compute `cache_key` and check the `renders` table / MinIO for an existing artifact; skip the job on a hit. Only cache-miss scenes reach the render-worker.
- **Verify:** `pytest backend/tests/unit/services/test_render_orchestrator.py::test_cache_hit_skips_render -v` (8 scenes, 3 dirty → exactly 3 real `renderMedia()` calls via a counter wrapper, 5 cache hits) → passes (AC-1, AC-4).
- **On failure:** treat any mismatch here as non-transient (cache correctness bug) — invoke `systematic-debugging` immediately, don't blind-retry.
- **Commit:** `git commit -m "feat(render): 6-2 cache_key idempotency, skip on hit (BR-1)"`

### Step 5: Job-level fail isolation + honest batch status (BR-2)
- **Files:** `backend/app/services/render_orchestrator.py`, SSE `render.progress` event emission (reuse 1-6 event bus)
- **Do:** one job failing must never cancel the batch; the batch is "done" only once every job reaches a terminal state (done or failed); expose a truthful aggregate status string (e.g. "7/8 + 1 lỗi"); emit `render.progress` per scene plus an aggregate percentage.
- **Verify:** `pytest backend/tests/unit/services/test_render_orchestrator.py::test_job_failure_does_not_cancel_batch backend/tests/unit/services/test_render_orchestrator.py::test_sse_progress_events -v` → both pass (AC-3, AC-5).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(render): 6-2 job fail isolation + honest batch status (BR-2)"`

### Step 6: Retry per job, no double-render on worker kill (BR-1 continued)
- **Files:** `backend/app/services/render_orchestrator.py`, `render-worker/src/worker.ts`
- **Do:** per-job retry on failure; a job already marked in-progress/done for a given `cache_key` must not be re-rendered by a retry after a simulated worker kill mid-job (use a status column / row lock, not a re-check-and-hope race).
- **Verify:** `pytest backend/tests/unit/services/test_render_orchestrator.py::test_kill_worker_mid_job_no_double_render -v` (counter wrapper asserts render count unchanged after retry) → passes (AC-4).
- **On failure:** non-transient by nature (race condition) — invoke `systematic-debugging` skill on first failure, don't blind-retry.
- **Commit:** `git commit -m "feat(render): 6-2 job retry without double-render on kill"`

### Step 7: ffmpeg merge — concat + BGM + CRF (BR-3, BR-5)
- **Files:** `backend/app/services/video_merge.py`
- **Do:** merge triggers only when 100% of scene jobs reached a terminal state (BR-3). ffmpeg concat demuxer in scene order + BGM mix (volume/fade, track from 6-5) + `-crf 20 -preset medium` (Decisions already locked, ⏳ tuned after 6-4 benchmark) → output to the fixed storage layout per ARCHITECTURE.md §6. **This step is ffmpeg only — never a second `renderMedia()` call on a whole-video `Video` composition** (see [rules/performance.md](../rules/performance.md), [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)).
- **Verify:** `pytest backend/tests/unit/services/test_video_merge.py::test_merge_only_at_100_percent -v` → passes; manual audio-sync check on 3 sample videos (start/middle/end), per the epic's Test Notes checklist.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(render): 6-2 ffmpeg merge concat+BGM+CRF (BR-3/BR-5)"`

### Step 8: Dirty-scene-during-batch handling (BR-4)
- **Files:** `backend/app/services/render_orchestrator.py`, `backend/app/api/renders.py` (endpoints per `docs/specs/api-spec.md` §7)
- **Do:** editing a scene while its batch is in flight lets the current batch finish untouched using the scene JSON version it started with; the edited scene is flagged dirty only for the next batch (ties into 5-5 BR-4's UI lock).
- **Verify:** `pytest backend/tests/unit/services/test_render_orchestrator.py::test_edit_during_batch_deferred_to_next_batch -v` → passes (AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(render): 6-2 defer mid-batch edits to next batch (BR-4)"`

### Step 9: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/services/test_render_orchestrator.py`, `backend/tests/integration/services/test_render_orchestrator_integration.py`, `render-worker/src/*.test.ts`
- **Do:** one test per Acceptance Criterion (1–5); mock HTTP with `respx` for backend adapters per [rules/testing.md](../rules/testing.md); note in the PR description exactly which Remotion Agent Skills were invoked and for what part (dev-guide.md §2.1 Definition of Done, [rules/pull-requests.md](../rules/pull-requests.md)).
- **Verify:** `cd backend && pytest backend/tests/unit/services/test_render_orchestrator.py backend/tests/integration/services/test_render_orchestrator_integration.py -v` → all pass; `cd render-worker && npm test` → all pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "test(render): 6-2 full AC coverage for render orchestrator"`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + đo "số lần render thực" bằng counter wrapper quanh CLI call; audio sync kiểm tay checklist (đầu/giữa/cuối). PR states which Remotion Skill was invoked.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/6-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/6-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
