# Task 4-1: LangGraph skeleton + checkpoint + human gate

**Points:** 5đ · **Epic:** 4 — Pipeline AI · **Depends:** 1-4, 1-5, 1-6, 3-2 · **FR:** AR-2
**State file:** [`state/4-1.json`](state/4-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-1-langgraph-skeleton-checkpoint-human-gate` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a system, I want pipeline có checkpoint bền và điểm dừng chờ người duyệt, so that crash không mất việc đã làm và user kiểm soát từng bước như SRS cam kết.

## Why
Bộ khung của toàn bộ giá trị sản phẩm (human-in-the-loop + resume). Mọi node sau chỉ là "điền thịt" vào khung này — see [patterns/langgraph-pipeline-node.md](../patterns/langgraph-pipeline-node.md).

## Scope
**In:** graph 6 node (produce/render stub); state Pydantic→JSONB; checkpoint `langgraph-checkpoint-postgres`; interrupt sau mỗi node (Mode 2); map node↔state machine (1-4); API `steps/{step}/run` + `approve` + `GET runs/{id}`; retry backoff/node (3 lần); correlation_id = run_id xuyên log/event.
**Out:** logic node thật (4-3–4-6); cancel (4-7); mode không-interrupt (7-2).

## Business Rules
1. Một project chỉ 1 run active — POST run khi đang chạy → 409.
2. Approve chỉ hợp lệ khi run interrupt đúng node đó (chống double-approve/race).
3. Node hoàn thành → checkpoint + step_version ghi **cùng transaction** (atomic — không bao giờ lệch nhau).
4. Retry hết 3 lần → project FAILED(reason=node lỗi cuối), giữ previous_status (1-4 BR-3).

## Acceptance Criteria
1. **(happy)** Run → interrupt sau research → project NEED_REVIEW → approve → node kế chạy; SSE đủ chuỗi sự kiện.
2. **(biên)** Kill process giữa node write → restart → resume đúng write; research không chạy lại.
3. **(lỗi/BR-1,2)** POST run khi đang chạy → 409; approve node đã qua → 409.
4. **(biên/BR-3)** Giả lập crash giữa "node xong, đang ghi" → sau restart: checkpoint và step_version nhất quán.
5. **(CI)** Integration skeleton node-stub xanh.

## Data & API
Bảng: `langgraph_checkpoints` (lib tự tạo qua migration); runs tracked qua checkpoint + status_history. Endpoints: api-spec §2. Contract change: không.

## Decisions already locked
- ⏳ Interrupt sau **mọi** node ở Mode 2 kể cả produce (user có thể muốn xem asset/audio trước render).

## Execution Steps

Work these in order. Update `state/4-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Pipeline state schema + graph skeleton
- **Files:** `backend/app/pipeline/state.py`, `backend/app/pipeline/graph.py`, `backend/app/pipeline/nodes/__init__.py`
- **Do:** define the LangGraph `PipelineState` as a Pydantic model (per `rules/architecture.md` — every node interface is Pydantic from day one) covering fields needed by all 6 nodes (research/ranking-factcheck/write/storyboard/produce-stub/render-stub). Build `graph.py` wiring 6 node stubs (produce/render are no-op stubs per Scope Out) in sequence, following [patterns/langgraph-pipeline-node.md](../patterns/langgraph-pipeline-node.md) for node shape.
- **Verify:** `python -c "from app.pipeline.graph import build_graph; build_graph()"` → no import/compile error.
- **On failure:** transient → retry 3x; logic error → invoke `systematic-debugging` skill; still failing → mark step+task `blocked`, log in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add app/pipeline && git commit -m "feat(pipeline): 4-1 add pipeline state schema and graph skeleton"` → `git push`

### Step 2: Postgres checkpointer wiring
- **Files:** `backend/app/pipeline/checkpoint.py`, migration for `langgraph_checkpoints` (via `langgraph-checkpoint-postgres`, per Data & API section)
- **Do:** wire `PostgresSaver`/`AsyncPostgresSaver` from `langgraph-checkpoint-postgres`; run its own migration/setup on app startup per `docs/dev-guide.md` conventions. No adapter should read env directly — checkpoint DSN flows through existing config layer (`rules/configuration-env.md`).
- **Verify:** `alembic upgrade head` (or project's migration command) → `langgraph_checkpoints` table exists; a smoke test writes+reads one checkpoint round-trip.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/pipeline/checkpoint.py alembic/ && git commit -m "feat(pipeline): 4-1 wire postgres checkpointer" && git push`

### Step 3: Interrupt-after-every-node (Mode 2) + node↔state-machine mapping
- **Files:** `backend/app/pipeline/graph.py`, `backend/app/pipeline/status_map.py`
- **Do:** configure `interrupt_after` for every node (per "Decisions already locked" — interrupt after ALL nodes including produce/render stubs in Mode 2). Map each node's completion to the project state machine (1-4) transitions (e.g. research done → `NEED_REVIEW`).
- **Verify:** unit test asserting graph config has `interrupt_after` set for all 6 nodes.
- **On failure:** same policy as Step 1.
- **Commit:** as above, message `4-1 interrupt-after-node + state machine mapping`.

### Step 4: Atomic checkpoint + step_version write (BR-3)
- **Files:** `backend/app/pipeline/nodes/base.py` (or shared node wrapper), `backend/app/services/step_version.py`
- **Do:** wrap node completion so checkpoint write and `step_version` row insert happen in **one DB transaction** — never one without the other (BR-3, high-blast-radius per `rules/error-handling.md` idempotency requirement). Use the pattern in [patterns/langgraph-pipeline-node.md](../patterns/langgraph-pipeline-node.md).
- **Verify:** unit test asserting both writes share a transaction (e.g. inspect via a test double / savepoint).
- **On failure:** same policy as Step 1.
- **Commit:** `4-1 atomic checkpoint + step_version write`.

### Step 5: API — run / approve / get run (BR-1, BR-2)
- **Files:** `backend/app/api/routes/runs.py`, `backend/app/services/run_service.py` (no business logic in routers per `rules/code-style.md`)
- **Do:** implement `POST steps/{step}/run`, `POST runs/{id}/approve`, `GET runs/{id}` per api-spec §2. Enforce BR-1 (409 if project already has an active run) and BR-2 (approve only valid if run is interrupted at exactly that node — guards against double-approve/race).
- **Verify:** integration test: second `run` POST while active → 409; `approve` on wrong/past node → 409.
- **On failure:** same policy as Step 1.
- **Commit:** `4-1 run/approve/get-run API + BR-1/BR-2 guards`.

### Step 6: Retry-with-backoff per node (BR-4) + correlation_id
- **Files:** `backend/app/pipeline/nodes/base.py`, `backend/app/core/logging.py`
- **Do:** wrap node execution with retry (3 attempts, backoff) per `rules/error-handling.md`; on exhaustion set project `FAILED(reason=<last node error>)` while preserving `previous_status` (1-4 BR-3). Set `correlation_id = run_id` on every log line/event emitted during a run (`rules/logging.md`).
- **Verify:** unit test: node raising 3x → project `FAILED` with correct `reason` and `previous_status` preserved.
- **On failure:** same policy as Step 1.
- **Commit:** `4-1 retry backoff + correlation_id + FAILED transition`.

### Step 7: SSE event chain for happy path (AC1)
- **Files:** `backend/app/api/routes/events.py` or existing SSE infra from 1-6
- **Do:** ensure a full run→interrupt→approve→next-node cycle emits the expected SSE event sequence (reuses 1-6 event bus — no new transport).
- **Verify:** integration test asserting SSE event sequence for AC1's happy path.
- **On failure:** same policy as Step 1.
- **Commit:** `4-1 SSE event chain for run lifecycle`.

### Step 8: Fault injection test — crash mid-write (AC2, AC4, BR-3)
- **Files:** `backend/tests/integration/pipeline/test_checkpoint_atomicity.py`
- **Do:** simulate process kill mid-node-write (raise after writing one of the two — checkpoint or step_version — per Step 4's transaction) and mid-node execution (AC2: kill during research, restart, resume without re-running research — assert via a call counter). This is the most important test in the task per the DoD note below.
- **Verify:** `pytest backend/tests/integration/pipeline/test_checkpoint_atomicity.py` → both fault-injection cases pass; consistent all-or-nothing state confirmed.
- **On failure:** non-transient by nature (this IS the correctness test) → invoke `systematic-debugging` skill immediately, do not blind-retry.
- **Commit:** `4-1 fault injection tests for checkpoint atomicity`.

### Step 9: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `backend/tests/integration/pipeline/test_run_lifecycle.py`, `backend/tests/unit/pipeline/...`
- **Do:** one test per Acceptance Criterion tagged above (happy/biên/lỗi/CI); mock HTTP with `respx` for any adapter touched per `rules/testing.md`.
- **Verify:** `pytest backend/tests/unit/pipeline backend/tests/integration/pipeline` → all AC-mapped tests pass, including the CI skeleton node-stub test (AC5).
- **On failure:** same policy as above.
- **Commit:** `4-1 complete AC test coverage`.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fault injection test cho BR-3 (raise sau ghi 1 trong 2); resume test chạy trong CI mỗi PR đụng pipeline (quan trọng nhất task này).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
