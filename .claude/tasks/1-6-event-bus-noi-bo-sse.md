# Task 1-6: Event bus nội bộ + SSE

**Points:** 2đ · **Epic:** 1 — Nền tảng · **Depends:** 1-4 · **FR:** NFR-1, AR-5
**State file:** [`state/1-6.json`](state/1-6.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/1-6-event-bus-sse` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a frontend, I want nhận tiến độ pipeline realtime, so that user luôn thấy hệ thống đang sống và đang làm gì.

## Why
RunningState (5-8) sống bằng dữ liệu của task này. Interface bus phải giống NATS ngay từ đầu để 9-1 swap không đổi call-site.

## Scope
**In:** in-process async bus (publish/subscribe, interface = NATS publisher tương lai); `GET /events/stream` SSE (auth one-time-token qua query); hook FE `useEventStream(projectId)` + reconnect; fallback polling `GET runs/{run_id}`.
**Out:** NATS thật (9-1); notification ngoài (7-4); event persistence (fire-and-forget, FE tự sync bằng polling).

## Business Rules
1. Event format đúng api-spec §10 + envelope event-catalog từ ngày 1.
2. Stream filter theo quyền — creator chỉ nhận event project mình; admin nhận tất.
3. One-time-token TTL 60s, dùng 1 lần.
4. FE reconnect → gọi polling 1 lần để sync trạng thái bị lỡ.

## Acceptance Criteria
1. **(happy)** Run chạy → FE nhận step.progress ≤1s, đúng format.
2. **(biên/BR-4)** Ngắt mạng 10s giữa run → reconnect + sync → UI đúng trạng thái hiện tại.
3. **(quyền/BR-2)** 2 session creator khác nhau → không nhận chéo event.
4. **(lỗi/BR-3)** Token quá 60s / dùng lần 2 → 401.

## Data & API
Endpoint mới: `POST /events/token` + `GET /events/stream?token=` → cập nhật api-spec §10. Events: `project.status`, `step.progress`.

## Decisions already locked
- ⏳ Fire-and-forget chấp nhận được vì polling bù (ảnh hưởng UX mất mạng dài).

## Execution Steps

Work these in order. Update `state/1-6.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: In-process async event bus
- **Files:** `backend/app/events/bus.py`
- **Do:** implement an async in-process publish/subscribe bus shaped to match the future NATS publisher (AR-5) — e.g. `async def publish(subject: str, payload: BaseModel)`, `def subscribe(subject_pattern) -> AsyncIterator[...]`; fire-and-forget, no persistence (per Scope Out) — a restart loses in-flight events by design.
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_event_bus.py -v`.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/events/bus.py && git commit -m "feat(events): 1-6 in-process async event bus"` → `git push`

### Step 2: Event envelope + wire into state_machine.transition()
- **Files:** `backend/app/events/schemas.py`, `backend/app/services/state_machine.py`
- **Do:** implement the event envelope per event-catalog + api-spec §10 (BR-1); replace the Step-3 stub publish call added in task 1-4 with the real `bus.publish("project.status", envelope)`; also define the `step.progress` event schema for future pipeline nodes to use.
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_event_envelope.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/events/schemas.py backend/app/services/state_machine.py && git commit -m "feat(events): 1-6 event envelope + wire into state machine"` → `git push`

### Step 3: One-time-token issuance
- **Files:** `backend/app/api/events.py`, `backend/app/services/event_token_service.py`
- **Do:** implement `POST /events/token` issuing a one-time token, TTL 60s, single-use (BR-3), stored in a short-lived in-memory store with expiry (no new infra dependency for this task).
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_event_token.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/events.py backend/app/services/event_token_service.py && git commit -m "feat(events): 1-6 one-time SSE auth token"` → `git push`

### Step 4: SSE endpoint with permission filter
- **Files:** `backend/app/api/events.py`
- **Do:** implement `GET /events/stream?token=` — validates and consumes the one-time token, subscribes to the bus filtered by project ownership (creator: own projects only; admin: all, BR-2), streams `text/event-stream`.
- **Verify:** `cd backend && uv run pytest backend/tests/integration/test_sse_stream.py -v` (2-client permission test).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/events.py && git commit -m "feat(events): 1-6 GET /events/stream SSE endpoint + permission filter"` → `git push`

### Step 5: Frontend useEventStream hook + reconnect + polling fallback
- **Files:** `frontend/src/lib/sse.ts`, `frontend/src/hooks/useEventStream.ts`
- **Do:** hook opens an `EventSource` against `/events/stream` after fetching a fresh one-time token; auto-reconnects on drop; on reconnect calls `GET runs/{run_id}` once to resync missed state (BR-4).
- **Verify:** `cd frontend && npm run build` → exit 0.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/lib/sse.ts frontend/src/hooks/useEventStream.ts && git commit -m "feat(frontend): 1-6 useEventStream hook + reconnect + polling fallback"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/integration/test_sse_stream.py`, `backend/tests/contract/test_event_catalog_contract.py`
- **Do:** one test per Acceptance Criterion — AC-1 `step.progress` delivered ≤1s in the correct format, AC-2 10s network drop → reconnect + resync to correct UI state, AC-3 two creator sessions never cross-leak events, AC-4 a token older than 60s or reused a 2nd time → 401; contract test asserting emitted events validate against the event-catalog schema.
- **Verify:** `cd backend && uv run pytest tests/ -v` → all pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests && git commit -m "test(events): 1-6 tests covering AC 1-4 + event-catalog contract test"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + integration 2-client test; contract test format event so với event-catalog schema.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/1-6.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/1-6.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
