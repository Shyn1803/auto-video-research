# Task 9-1: NATS JetStream + event library

**Points:** 5đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 1-6, 6-2 · **FR:** AR-5
**State file:** [`state/9-1.json`](state/9-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/9-1-nats-jetstream-event-library` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

> **Sequencing note:** Epic 9 is deliberately started only after Epic 6 (M4) is `done` — contract stability before extraction, per ADR-0001 (see [tasks/README.md](README.md) "Parallel execution tracks"). Verify `6-2` is `done` in `sprint-status.yaml` before claiming this task; if not, it is not yet unblocked — work a different task instead.

## User story
As a system, I want event bus bền với dedupe và DLQ, so that job phân phối tin cậy giữa các service và message lỗi không bao giờ biến mất lặng lẽ.

## Why
[decisions/0003-nats-jetstream.md](../decisions/0003-nats-jetstream.md). Nhờ 1-6 giữ interface từ đầu, task này là "swap transport" chứ không phải viết lại — trả cổ tức của kỷ luật contract. **Do not start this epic before Epic 6 (M4) is done — contract stability before extraction is deliberate sequencing, see [tasks/README.md](README.md).**

## Scope
**In:** NATS vào compose prod; provision streams/subjects idempotent theo `docs/specs/event-catalog.md`; event lib (envelope, publisher/consumer helper: ack, max_deliver=5, DLQ publish, dedupe Msg-Id); swap in-process bus khi `NATS_URL` set; CI matrix 2 chế độ.
**Out:** NATS cluster 3 node (v1.1); tách worker (9-2/9-3); UI queue (9-4).

## Business Rules
1. Unset NATS_URL → in-process, toàn test xanh (dev không cần NATS).
2. Envelope schema_version — consumer gặp major lạ → DLQ kèm lý do, không đoán.
3. NATS mất kết nối → publisher buffer + reconnect; quá ngưỡng (config) → lỗi rõ ràng, không nuốt event.
4. Provision script chạy lại an toàn (idempotent) — là một phần migrate/deploy.

## Acceptance Criteria
1. **(happy)** NATS_URL set → events qua JetStream; SSE bridge FE không đổi hành vi.
2. **(biên)** Consumer không ack → redeliver; 5 lần → DLQ; Msg-Id trùng → xử lý 1 lần.
3. **(biên/BR-1)** CI matrix in-process + NATS đều xanh.
4. **(lỗi/BR-3)** NATS down 30s giữa run → reconnect, đếm event 2 đầu khớp.
5. **(BR-2)** Event schema 2.0.0 giả → DLQ lý do "schema không hỗ trợ".

## Data & API
Hạ tầng: streams RENDER/MEDIA/PUBLISH/EVENTS. Contract change: không (catalog là spec sẵn).

## Decisions already locked
- ⏳ Buffer reconnect 100 events / 10s — quá → lỗi.

## Execution Steps

Work these in order. Update `state/9-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Event envelope + Pydantic schemas
- **Files:** `backend/app/events/envelope.py`, `backend/app/events/schemas.py`
- **Do:** Define `EventEnvelope` (Pydantic) with `schema_version` (semver string), `event_type`, `correlation_id`, `payload`, `msg_id` (for dedupe), matching `docs/specs/event-catalog.md`. Every event payload type is its own Pydantic model with `schema_version`, per `rules/type-safety.md` ("Event payloads (NATS, Phase 2+) are Pydantic schemas with `schema_version` — same semver discipline as Scene JSON"). Do not invent fields not in `docs/specs/event-catalog.md` — flag a gap instead of guessing (per `rules/autonomy-policy.md`).
- **Verify:** `mypy --strict backend/app/events/` → 0 errors.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/events/ && git commit -m "feat(events): 9-1 add event envelope + payload schemas"` → `git push`

### Step 2: In-process bus (existing) stays default; publisher/consumer abstraction
- **Files:** `backend/app/events/bus.py`, `backend/app/events/nats_bus.py`, `backend/app/events/inprocess_bus.py`
- **Do:** Extract a `EventBus` interface (publish/subscribe) that both the existing 1-6 in-process bus and a new NATS-backed implementation satisfy. Selection logic: `NATS_URL` unset → in-process (BR-1); set → NATS JetStream. This must be a drop-in swap behind the same interface consumed by SSE bridge and pipeline nodes — do not change call sites outside `backend/app/events/`.
- **Verify:** `pytest backend/tests/unit/events/ -k inprocess` → all pass, no NATS dependency required.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/events/ && git commit -m "feat(events): 9-1 extract EventBus interface, keep in-process default"` → `git push`

### Step 3: NATS JetStream publisher/consumer helper
- **Files:** `backend/app/events/nats_bus.py`
- **Do:** Implement publish with Msg-Id header for dedupe; consumer with explicit ack, `max_deliver=5` (BR redeliver-then-DLQ per AC-2), DLQ publish on exhaustion or unsupported `schema_version` major (BR-2, AC-5 — DLQ reason `"schema không hỗ trợ"`). Publisher buffers on disconnect and reconnects; buffer cap per "Decisions already locked" (100 events / 10s) — exceeding it is a clear error, never a silently dropped event (BR-3, AC-4).
- **Verify:** `pytest backend/tests/integration/events/ -k nats_reconnect` → reconnect + event-count-matches assertion passes (requires local NATS or testcontainers, see Step 6).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/events/nats_bus.py && git commit -m "feat(events): 9-1 NATS publisher/consumer with dedupe, redeliver, DLQ"` → `git push`

### Step 4: Idempotent stream/subject provisioning
- **Files:** `backend/app/events/provision.py`, `docker/nats/` (compose service definition)
- **Do:** Script that creates/updates streams `RENDER`/`MEDIA`/`PUBLISH`/`EVENTS` and their subjects per `docs/specs/event-catalog.md`, safe to re-run (checks existing stream config before creating, per BR-4). Add NATS service to prod compose (`docker/docker-compose.prod.yml` or equivalent per `context/folder-structure.md`).
- **Verify:** run provisioning script twice in a row against a fresh NATS container → second run exits 0 with no duplicate/error (idempotency check).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/events/provision.py docker/ && git commit -m "feat(events): 9-1 idempotent NATS stream provisioning + compose"` → `git push`

### Step 5: SSE bridge compatibility check
- **Files:** wherever the 1-6 SSE bridge consumes `EventBus` (see `backend/app/api/` SSE route)
- **Do:** Confirm the SSE bridge works unchanged against both bus implementations (AC-1: "SSE bridge FE không đổi hành vi"). If the bridge currently imports the in-process bus concretely, change it to depend on the `EventBus` interface from Step 2 instead.
- **Verify:** manual/integration test hitting the SSE endpoint with `NATS_URL` set vs unset → identical event stream shape in both.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/ && git commit -m "fix(events): 9-1 SSE bridge depends on EventBus interface, not bus impl"` → `git push`

### Step 6: CI matrix (in-process + NATS) + tests for every AC
- **Files:** `.github/workflows/*.yml` (or equivalent CI config per `context/build-process.md`), `backend/tests/integration/events/`
- **Do:** Two CI jobs/matrix legs: one with `NATS_URL` unset (in-process, BR-1/AC-3), one with a NATS testcontainer running (AC-1, AC-2, AC-4, AC-5). Write one test per Acceptance Criterion: redeliver-to-DLQ at 5 attempts (AC-2), Msg-Id dedupe (AC-2), reconnect with matching publisher/consumer counters (AC-4), schema_version 2.0.0 → DLQ with correct reason string (AC-5).
- **Verify:** `pytest backend/tests/integration/events/ -v` (both matrix legs) → all AC-tagged tests pass; CI config lints/validates.
- **On failure:** same policy as Step 1.
- **Commit:** `git add .github/ backend/tests/ && git commit -m "test(events): 9-1 CI matrix + AC coverage for NATS event lib"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + Testcontainers NATS trong integration; đo "đếm 2 đầu" bằng counter publisher/consumer.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/9-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/9-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
