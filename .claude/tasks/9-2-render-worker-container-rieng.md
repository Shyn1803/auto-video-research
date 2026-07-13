# Task 9-2: Render Worker container riêng

**Points:** 5đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-1 · **FR:** NFR-2
**State file:** [`state/9-2.json`](state/9-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/9-2-render-worker-container-rieng` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

> **Sequencing note:** this task, like the rest of Epic 9, starts only after Epic 6 (M4) is `done` (contract stability before extraction — ADR-0001, see `tasks/README.md`). It also directly depends on `9-1` for the event bus — do not claim before `9-1` is `done`.

## User story
As an operator, I want render chạy ở worker riêng scale được bằng replicas, so that render nặng không nghẽn API và tăng máy là tăng throughput.

## Why
NFR-2 scale ngang. Đặt sau M4: tách khi logic đã đúng in-process — di chuyển code ổn định, không debug 2 thứ cùng lúc.

## Scope
**In:** `render-worker/` Node.js: consumer render.scene/video.request → `bundle()` **1 lần khi container khởi động** (cache serveUrl in-memory — mỗi replica bundle độc lập, không share qua network) → `selectComposition()`/`renderMedia()` mỗi job → MinIO → done event; orchestrator publish qua NATS khi bật; compose replicas; graceful shutdown (ack in-flight xong mới thoát); version handshake supportedSchemaRange → từ chối vào DLQ.
**Out:** autoscale theo queue depth (10-5 đánh giá); GPU render (không cần — Remotion CPU).

## Business Rules
1. Idempotent theo cache_key — check renders/MinIO trước render (kể cả redeliver).
2. `ack_wait` = thời gian render tối đa dự kiến × 1.5 (từ benchmark 6-4) — crash → redeliver worker khác không chờ quá lâu.
3. Worker version cũ gặp scene mới → DLQ + alert — không render sai lặng lẽ (nối 2-2 BR-3).
4. SIGTERM → dừng nhận job mới, hoàn thành job hiện tại, ack, thoát (deploy không mất job).

## Acceptance Criteria
1. **(happy)** 2 replicas, batch 8 cảnh → phân phối đều; throughput ≈2× benchmark 1 worker.
2. **(biên/BR-1)** Kill -9 worker giữa job → redeliver worker kia hoàn thành; tổng số lần render thực = số cảnh.
3. **(lỗi/BR-3)** Scene 1.1.0 vào worker ^1.0 → DLQ SCHEMA_RANGE + alert.
4. **(BR-4)** `docker compose restart render-worker` giữa batch → batch hoàn thành đủ, không job mất.
5. **(vận hành)** `--scale render-worker=4` chạy không cấu hình thêm.

## Data & API
Container mới + compose; payload theo event-catalog (đã spec). Contract change: không.

## Decisions already locked
- Worker image riêng (node + chromium Remotion cần) — không nhét vào image backend.

## Execution Steps

Work these in order. Update `state/9-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Scaffold `render-worker/` container
- **Files:** `render-worker/package.json`, `render-worker/Dockerfile`, `render-worker/src/index.ts`
- **Do:** New Node.js service per `context/folder-structure.md` (`render-worker/` at repo root, Node.js + Remotion CLI + NATS consumer). Dockerfile is a dedicated image (node + chromium for Remotion) — per "Decisions already locked", never add this to the backend image.
- **Verify:** `docker build -f render-worker/Dockerfile .` → exits 0.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add render-worker/ && git commit -m "feat(render-worker): 9-2 scaffold dedicated Node+chromium container"` → `git push`

### Step 2: Bundle-once-at-startup + consumer wiring
- **Files:** `render-worker/src/bundle.ts`, `render-worker/src/consumer.ts`
- **Do:** `bundle()` called exactly once per container start, `serveUrl` cached in-memory for the process lifetime (per `rules/performance.md`: "never re-bundle per job" — this was a caught design gap, don't reintroduce it). Consumer subscribes to `render.scene`/`video.request` subjects via the `9-1` event lib (`app/events` NATS bus, imported as a shared package or vendored client per event-catalog envelope).
- **Verify:** start container, publish 3 test jobs → logs show exactly 1 `bundle()` call and 3 `renderMedia()` calls.
- **On failure:** same policy as Step 1.
- **Commit:** `git add render-worker/src/ && git commit -m "feat(render-worker): 9-2 bundle once at startup, per-job renderMedia"` → `git push`

### Step 3: Idempotent render + cache_key check (BR-1)
- **Files:** `render-worker/src/renderJob.ts`
- **Do:** Before calling `renderMedia()`, check MinIO/render record for existing output at `cache_key` (per `rules/performance.md` cache-key convention: `sha256(canonical_scene_json + template_version + format)`). If present, skip render and emit the done event directly — this is what makes a NATS redelivery of the same job safe (ties directly to `rules/error-handling.md`: "a redelivered NATS message must not double-render or double-charge").
- **Verify:** publish the same job twice (simulating redelivery) → `renderMedia()` invoked exactly once, done event emitted twice with identical output reference.
- **On failure:** same policy as Step 1.
- **Commit:** `git add render-worker/src/renderJob.ts && git commit -m "feat(render-worker): 9-2 idempotent render via cache_key check (BR-1)"` → `git push`

### Step 4: Version handshake + graceful shutdown
- **Files:** `render-worker/src/consumer.ts`, `render-worker/src/shutdown.ts`
- **Do:** On job receipt, check scene `schema_version` against this worker's `supportedSchemaRange`; out-of-range → publish to DLQ with reason `SCHEMA_RANGE` + alert event, do not attempt render (BR-3, AC-3). Handle `SIGTERM`: stop accepting new jobs, finish in-flight job, ack, exit (BR-4). Set `ack_wait` = benchmark-derived max render time × 1.5 (BR-2, pull the benchmark number from `docs/backlog/epic-06-*.md`/6-4 results — if not yet recorded, use a documented placeholder and flag it in `memory/project-memory.md` Open Questions per `rules/autonomy-policy.md`, don't block on it).
- **Verify:** unit test SIGTERM handler completes in-flight job before exit; unit test schema out-of-range → DLQ with `SCHEMA_RANGE` reason.
- **On failure:** same policy as Step 1.
- **Commit:** `git add render-worker/src/ && git commit -m "feat(render-worker): 9-2 schema version handshake + graceful SIGTERM shutdown"` → `git push`

### Step 5: Compose replicas + orchestrator NATS publish
- **Files:** `docker/docker-compose.prod.yml` (or per `context/folder-structure.md`), `backend/app/pipeline/` (orchestrator publish call site)
- **Do:** Add `render-worker` service to compose supporting `--scale render-worker=N` with no extra config (AC-5). Ensure the render orchestrator (6-2) publishes via NATS through the `EventBus` interface from `9-1` when `NATS_URL` is set — no behavior change to the in-process path.
- **Verify:** `docker compose --scale render-worker=4 up` (or documented equivalent) → 4 containers healthy, no manual per-replica config needed.
- **On failure:** same policy as Step 1.
- **Commit:** `git add docker/ backend/app/pipeline/ && git commit -m "feat(render-worker): 9-2 compose replicas + orchestrator NATS publish"` → `git push`

### Step 6: Chaos test (kill -9) + throughput benchmark + full AC coverage
- **Files:** `render-worker/tests/`, `.github/workflows/*.yml` (nightly job)
- **Do:** One test per AC: 2-replica batch-of-8 distributes evenly with ≈2× single-worker throughput (AC-1, record the number in `docs/ARCHITECTURE.md` per the story's own note "số ghi vào ARCHITECTURE" — flag for docs update if that file isn't touched here); `kill -9` mid-job → redelivery completes on the other replica, total actual renders == scene count, never double (AC-2, ties to BR-1); schema mismatch → DLQ (AC-3, covered in Step 4 but assert end-to-end here too); `docker compose restart render-worker` mid-batch completes the whole batch (AC-4). Wire the kill -9 chaos test into CI nightly per Definition of Done.
- **Verify:** `pytest render-worker/tests/ -v` (or `npm test` per the worker's own test runner) + nightly CI chaos job green.
- **On failure:** same policy as Step 1.
- **Commit:** `git add render-worker/tests/ .github/ && git commit -m "test(render-worker): 9-2 chaos + throughput benchmark, full AC coverage"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + chaos test kill -9 chạy lặp trong CI nightly; benchmark so sánh trước/sau tách (không regression 1-worker).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/9-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/9-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
