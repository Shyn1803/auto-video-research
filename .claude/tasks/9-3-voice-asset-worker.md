# Task 9-3: Voice + Asset worker

**Points:** 3đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-1 · **FR:** NFR-2
**State file:** [`state/9-3.json`](state/9-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/9-3-voice-asset-worker` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

> **Sequencing note:** part of Epic 9, started only after Epic 6 (M4) is `done` (ADR-0001, see `tasks/README.md`). Depends directly on `9-1` for the event bus — verify it's `done` before claiming. This task can run in parallel with `9-2` once `9-1` is done — both depend only on `9-1`, not on each other.

## User story
As an operator, I want produce (TTS/asset) chạy worker riêng, tách được sang máy GPU, so that AI local nặng không tranh tài nguyên với API và scale độc lập.

## Why
NFR-2 phần media. Điểm giá trị thật: local TTS/SD cần GPU — worker tách host được (BR-2) mở đường "1 máy GPU + n máy CPU" của ARCHITECTURE §10.

## Scope
**In:** tách produce (6-1) thành consumer tts/asset.request trong worker Python (chung image backend, entrypoint riêng); bounded concurrency theo engine; compose profile GPU riêng (local TTS/SD).
**Out:** BGE-M3 tách service (chỉ khi nghẽn); autoscale.

## Business Rules
1. Cache audio/asset hiệu lực nguyên vẹn qua worker (6-1 BR-1).
2. Worker chạy host khác chỉ cần NATS_URL + MinIO + DB env — không phụ thuộc localhost.
3. Job TTS engine local khi GPU bận → xếp hàng theo semaphore, không OOM.

## Acceptance Criteria
1. **(happy)** Produce 10 cảnh qua worker; kill giữa chừng → resume không trùng audio (cache đo).
2. **(biên/BR-2)** Worker trên container network khác (giả lập host 2) → hoạt động đủ.
3. **(BR-3)** 10 job local TTS đồng thời, semaphore 2 → không OOM, xếp hàng đúng.
4. **(scale)** voice-worker=2 phân phối job.

## Data & API
Payload tts/asset.request-done theo event-catalog. Contract change: không.

## Decisions already locked
- ⏳ Voice và Asset chung 1 worker process v1 (2 consumer) — tách nữa khi số liệu đòi.

## Execution Steps

Work these in order. Update `state/9-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Worker entrypoint (shared backend image)
- **Files:** `backend/app/workers/voice_worker.py`, `backend/app/workers/asset_worker.py`, `backend/Dockerfile` (or a worker-specific entrypoint override)
- **Do:** Per `context/folder-structure.md`, these live at `backend/app/workers/` and reuse the existing backend image with a different entrypoint (not a new image, unlike `9-2`'s render-worker — per this task's own "Decisions already locked": voice + asset share one worker process v1 with 2 consumers).
- **Verify:** `docker build -f backend/Dockerfile --target worker .` (or equivalent) → exits 0; entrypoint starts without crashing against a local NATS.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/workers/ backend/Dockerfile && git commit -m "feat(workers): 9-3 scaffold voice/asset worker entrypoint on shared backend image"` → `git push`

### Step 2: Extract produce (6-1) logic into consumer handlers
- **Files:** `backend/app/workers/voice_worker.py`, `backend/app/workers/asset_worker.py`, `backend/app/pipeline/nodes/produce.py` (existing 6-1 node)
- **Do:** Move the TTS/asset generation logic invoked from `tts.request`/`asset.request` subjects into these worker consumer handlers, reusing the existing adapter calls from 6-1 unchanged (adapters stay in `backend/app/adapters/`, per `rules/architecture.md` — workers are callers, not a second adapter layer). Preserve the 6-1 cache behavior exactly (BR-1: "cache audio/asset hiệu lực nguyên vẹn qua worker").
- **Verify:** `pytest backend/tests/unit/workers/ -k produce_cache` → cache hit/miss behavior identical to the pre-worker 6-1 test.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/workers/ backend/app/pipeline/ && git commit -m "feat(workers): 9-3 move produce logic into voice/asset consumer handlers"` → `git push`

### Step 3: Bounded concurrency semaphore per engine (BR-3)
- **Files:** `backend/app/workers/voice_worker.py`
- **Do:** Add a per-engine `asyncio.Semaphore` (config-driven concurrency limit) so local TTS engine jobs queue instead of running unbounded when GPU is busy — this prevents OOM (BR-3, AC-3: "10 job local TTS đồng thời, semaphore 2 → không OOM, xếp hàng đúng").
- **Verify:** `pytest backend/tests/unit/workers/ -k semaphore` with a mock slow engine → exactly 2 concurrent executions at any time, remaining 8 queued in order.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/workers/voice_worker.py && git commit -m "feat(workers): 9-3 bounded concurrency semaphore per TTS engine (BR-3)"` → `git push`

### Step 4: Host-independence (BR-2) + GPU compose profile
- **Files:** `docker/docker-compose.yml`, `docker/docker-compose.gpu.yml` (profile), `backend/app/core/config.py`
- **Do:** Confirm worker startup requires only `NATS_URL` + MinIO + DB env — no `localhost` assumption anywhere in the worker code path (BR-2, so it can run on a separate GPU host per ARCHITECTURE §10). Add a compose profile for local TTS/SD GPU workers, separate from the default CPU profile.
- **Verify:** start the worker with env pointing at non-localhost NATS/MinIO/DB (simulate "host 2" via a separate docker network) → worker connects and processes a job (AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git add docker/ backend/app/core/config.py && git commit -m "feat(workers): 9-3 host-independent env config + GPU compose profile (BR-2)"` → `git push`

### Step 5: Replica scaling + resume-without-duplicate test
- **Files:** `docker/docker-compose.yml`, `backend/tests/integration/workers/`
- **Do:** Confirm `voice-worker=2` (compose scale) distributes jobs across replicas (AC-4). Write the kill-mid-produce-then-resume test: produce 10 scenes, kill worker mid-run, verify resumed run does not re-generate cached audio (AC-1, ties to BR-1 cache correctness under redelivery — same idempotency principle as `rules/error-handling.md`'s redelivery rule).
- **Verify:** `pytest backend/tests/integration/workers/ -k resume_no_duplicate` → cache-hit count confirms no duplicate audio generation after kill/resume.
- **On failure:** same policy as Step 1.
- **Commit:** `git add docker/ backend/tests/ && git commit -m "test(workers): 9-3 replica scale-out + kill-resume no-duplicate-audio test"` → `git push`

### Step 6: Full AC coverage via reused 6-1 test matrix
- **Files:** `backend/tests/unit/workers/`, `backend/tests/integration/workers/`
- **Do:** Reuse the existing 6-1 produce test suite, parameterized to also run in "worker mode" (matrix), per this task's own Definition of Done. Ensure every AC (1–4) maps to at least one passing test.
- **Verify:** `pytest backend/tests/ -k "produce and (worker or matrix)"` → all green.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests/ && git commit -m "test(workers): 9-3 reuse 6-1 produce matrix in worker mode, full AC coverage"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + reuse test 6-1 chạy chế độ worker (matrix); semaphore test với mock engine chậm.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/9-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/9-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
