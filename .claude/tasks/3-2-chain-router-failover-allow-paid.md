# Task 3-2: Chain router + failover + ALLOW_PAID

**Points:** 5đ · **Epic:** 3 — Provider framework · **Depends:** 3-1 · **FR:** FR-18, FR-21
**State file:** [`state/3-2.json`](state/3-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/3-2-chain-router-failover-allow-paid` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a system, I want mọi call ra ngoài đi qua chuỗi ưu tiên có failover tự động, so that một provider chết hay hết quota không bao giờ dừng cả hệ thống.

## Why
Trái tim của chiến lược free-tier: xoay giữa Gemini/Groq/OpenRouter/local theo tình trạng thực. Cũng là nơi thực thi `ALLOW_PAID` — hàng rào chống phát sinh chi phí ngoài ý muốn.

## Scope
**In:** router đọc `*_CHAIN` theo capability/tier; available check mỗi call (cache 30s: key tồn tại/health/paid-policy); failover: QuotaError→xoay key→next; Timeout/5xx→next; event `provider.failover`; ghi usage tại router; health check định kỳ + on-demand; `AllProvidersFailed` giàu thông tin.
**Out:** UI ma trận (3-5); adapters thật (3-3); daily cap (3-5).

## Business Rules
1. `ALLOW_PAID=false` loại provider `is_paid` khỏi chain kể cả có key — kiểm tại router, không tin adapter.
2. Lỗi 4xx non-retryable (prompt sai, content policy) → **không** failover — fail ngay kèm nguyên nhân.
3. `AllProvidersFailed` chứa `[{provider, reason}]` — nguồn dữ liệu cho error state RunningState (5-8 BR-2).
4. Mỗi call đi qua chain tối đa 1 vòng — không loop.
5. Health check fail → provider tạm loại 60s (circuit breaker đơn giản), event phát 1 lần (không spam).

## Acceptance Criteria
1. **(happy)** gemini mock 500 → groq trả lời + event failover đúng payload.
2. **(biên/BR-2)** gemini 400 invalid → fail ngay không gọi groq.
3. **(biên/BR-1)** fpt có key + ALLOW_PAID=false → counter fpt = 0 vĩnh viễn.
4. **(lỗi/BR-3)** Cả chain chết → AllProvidersFailed đủ danh sách lý do; node retry backoff.
5. **(BR-5)** Provider fail health → 60s không được gọi → tự thử lại; event 1 lần.

## Data & API
Bảng: `llm_usage` ghi tại đây. Events: `provider.failover`, `provider.exhausted`. Contract change: không.

## Decisions already locked
- ⏳ Circuit breaker 60s cố định v1 (không exponential).

## Execution Steps

Work these in order. Update `state/3-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Router skeleton reading `*_CHAIN` per capability/tier
- **Files:** `backend/app/core/router.py`
- **Do:** Implement `ProviderRouter` (or equivalent service, not a FastAPI router) that, for a given capability + tier, reads the matching `*_CHAIN` env var (e.g. `LLM_CHAIN_CHEAP`) via `ProviderSettings` (from 3-1) and resolves it to an ordered list of adapter instances from the registry (from 3-1). No provider-specific logic here — this stays generic across all 7 capabilities per [patterns/provider-adapter.md](../patterns/provider-adapter.md).
- **Verify:** unit test with 2 dummy registered adapters + a fake chain env value → router returns them in declared order.
- **On failure:** transient → retry 3×; logic error → `systematic-debugging` skill; still failing → mark step/task `blocked`, log in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/core/router.py && git commit -m "feat(router): 3-2 chain router reads *_CHAIN per capability/tier" && git push`

### Step 2: Availability check with 30s cache + ALLOW_PAID enforcement (BR-1)
- **Files:** `backend/app/core/router.py`
- **Do:** Before calling a provider, check availability = in chain AND (key present OR local service reachable) AND (free OR `ALLOW_PAID=true`), cached 30s per provider (avoid re-checking health every call). Enforce `ALLOW_PAID=false` **at the router**, not by trusting the adapter's `is_paid` flag (BR-1) — a paid provider with a valid key still must not be called when `ALLOW_PAID=false`.
- **Verify:** unit test: `is_paid=True` adapter with a valid key + `ALLOW_PAID=false` → never selected, call counter stays 0 (maps to AC3).
- **On failure:** same policy.
- **Commit:** `git add backend/app/core/router.py && git commit -m "feat(router): 3-2 availability cache + ALLOW_PAID gate at router" && git push`

### Step 3: Failover logic — QuotaError/Timeout/5xx vs. non-retryable 4xx (BR-2, BR-4)
- **Files:** `backend/app/core/router.py`
- **Do:** Walk the chain: `QuotaError` → rotate key (delegates to 3-4's key rotation once it exists; for now, next adapter instance if multiple keys aren't yet modeled) or move to next provider; `TimeoutError`/5xx `ProviderError(retryable=True)` → move to next provider + emit `provider.failover` event; a non-retryable 4xx (`ProviderError(retryable=False)`, e.g. invalid prompt/content policy) → fail immediately, do **not** failover (BR-2). Cap the walk at exactly one pass through the chain — never loop back to an already-tried provider (BR-4).
- **Verify:** unit test AC1 (mock 500 on provider A → provider B answers + failover event fired with correct payload) and AC2 (mock 400 invalid on provider A → fails immediately, provider B never called).
- **On failure:** same policy.
- **Commit:** `git add backend/app/core/router.py && git commit -m "feat(router): 3-2 failover on retryable errors, no failover on 4xx" && git push`

### Step 4: `AllProvidersFailed` + usage logging at router
- **Files:** `backend/app/core/router.py`, `backend/app/core/exceptions.py`
- **Do:** When the chain is exhausted, raise `AllProvidersFailed` carrying `[{provider, reason}]` for every attempted provider (BR-3 — this feeds RunningState's error display per story 5-8 BR-2). Write `llm_usage` rows **in the router**, never inside an adapter, per [rules/logging.md](../rules/logging.md) ("usage/cost logging happens in the router/service layer, never inside an adapter").
- **Verify:** unit test: all providers in chain mocked to fail → `AllProvidersFailed` raised with one reason entry per provider (AC4).
- **On failure:** same policy.
- **Commit:** `git add backend/app/core/router.py backend/app/core/exceptions.py && git commit -m "feat(router): 3-2 AllProvidersFailed with per-provider reasons + usage logging" && git push`

### Step 5: Circuit breaker — 60s exclusion after health-check fail (BR-5)
- **Files:** `backend/app/core/router.py`
- **Do:** On a health-check failure for a provider, exclude it from the chain for a fixed 60s window (no exponential backoff — decision already locked ⏳), then automatically allow retry after the window. Emit the exclusion event exactly once per failure episode, not once per skipped call (BR-5 "không spam").
- **Verify:** unit test: provider health fails → excluded for 60s (simulate with a fake clock) → auto re-included after → event count is exactly 1 for the episode (AC5).
- **On failure:** same policy.
- **Commit:** `git add backend/app/core/router.py && git commit -m "feat(router): 3-2 60s circuit breaker on health-check failure" && git push`

### Step 6: Events — `provider.failover`, `provider.exhausted`
- **Files:** `backend/app/events/provider.py`
- **Do:** Define Pydantic event schemas `ProviderFailoverEvent` and `ProviderExhaustedEvent` with `schema_version`, per [rules/type-safety.md](../rules/type-safety.md). Wire router to emit these at the failover/exhaustion points from Steps 3–5. Confirm no Scene JSON/DB contract changes needed (Data & API says "không" — verify by checking event-catalog already lists these per epic-03).
- **Verify:** unit test asserting event payload shape on a triggered failover (AC1 payload check).
- **On failure:** same policy.
- **Commit:** `git add backend/app/events/provider.py backend/app/core/router.py && git commit -m "feat(events): 3-2 provider.failover and provider.exhausted event schemas" && git push`

### Step 7: Health check — periodic + on-demand
- **Files:** `backend/app/core/router.py`, `backend/app/workers/health_check.py` (or equivalent scheduled task)
- **Do:** Implement an on-demand health-check callable (used by 3-5's Admin health-check button later) and a periodic check loop that refreshes the 30s availability cache / feeds the circuit breaker from Step 5.
- **Verify:** unit test calling the on-demand health-check function directly against a mocked adapter.
- **On failure:** same policy.
- **Commit:** `git add backend/app/core/router.py backend/app/workers/health_check.py && git commit -m "feat(router): 3-2 periodic + on-demand health check" && git push`

### Step 8: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/core/test_router.py`
- **Do:** One test per AC (happy/biên/lỗi/BR-5) plus the "đủ bảng nhánh test-plan §1.1" branch table referenced in Test Notes. All mock adapters, zero network calls, per [rules/testing.md](../rules/testing.md).
- **Verify:** `pytest backend/tests/unit/core/test_router.py -v` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** `git add backend/tests/unit/core/test_router.py && git commit -m "test(router): 3-2 full AC + branch-table coverage for chain router" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + toàn bộ test bằng mock adapter (không network) — code được test kỹ nhất hệ thống.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/3-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/3-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
