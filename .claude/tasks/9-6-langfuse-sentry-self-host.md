# Task 9-6: Langfuse + Sentry self-host

**Points:** 2đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 3-2 · **FR:** NFR-5
**State file:** [`state/9-6.json`](state/9-6.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/9-6-langfuse-sentry-self-host` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

> **Sequencing note:** part of Epic 9, started only after Epic 6 (M4) is `done` (ADR-0001, see `tasks/README.md`). Depends on `3-2` (LLM router — this is what gets traced) — verify it is `done` in `sprint-status.yaml` before claiming.

## User story
As a developer, I want trace mọi LLM call và error tracking có release tag, so that debug "AI trả lời lạ" và "lỗi ở đâu" bằng dữ liệu thay vì đoán.

## Why
LLM observability là điều kiện tune prompt có căn cứ (nối 4-2 eval); Sentry rút ngắn vòng phát hiện lỗi production khi dogfooding.

## Scope
**In:** Langfuse self-host: trace mỗi LLM call từ router 3-2 (prompt name+version, tokens, latency, tier, correlation_id); Sentry/GlitchTip: backend+FE+workers, release tag theo git; compose profile monitoring.
**Out:** trace UI trong app (dùng Langfuse UI); alert từ Sentry (7-4 đủ kênh).

## Business Rules
1. Trace không chứa key/token (chỉ prompt/response nghiệp vụ). See [rules/logging.md](../rules/logging.md).
2. Langfuse/Sentry down → fire-and-forget, pipeline không ảnh hưởng, warning 1 lần.
3. Env không cấu hình → tắt sạch (không lỗi, không noise).

## Acceptance Criteria
1. **(happy)** Mở 1 run trong Langfuse → chuỗi call đủ node, đúng prompt version, lọc theo correlation_id.
2. **(biên/BR-2)** Tắt Langfuse giữa run → pipeline xong bình thường, 1 warning.
3. **(Sentry)** Lỗi ném thử FE+BE+worker → hiện đúng release tag.
4. **(BR-1)** Trace sample kiểm không có secret (test denylist như 9-4).

## Data & API
Env LANGFUSE_*/SENTRY_DSN. Contract change: không.

## Decisions already locked
- ⏳ GlitchTip thay Sentry nếu resource server hạn chế — quyết khi dựng.

## Execution Steps

Work these in order. Update `state/9-6.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Langfuse self-host compose service
- **Files:** `docker/docker-compose.prod.yml`, `docker/monitoring/langfuse/` (env/config per compose convention)
- **Do:** Add Langfuse (self-hosted) to the `monitoring` compose profile alongside Prometheus/Grafana from `9-5`, per `context/folder-structure.md` (`docker-compose.prod.yml # + nats, workers, monitoring`). Config via `LANGFUSE_*` env vars per `docs/CONFIGURATION.md` §9 (`.claude/rules/configuration-env.md`: never invent an undocumented env var — if `docs/CONFIGURATION.md` §9 doesn't already list every var this step needs, flag the gap in `memory/project-memory.md` Open Questions rather than inventing names).
- **Verify:** `docker compose --profile monitoring up -d langfuse && curl localhost:3002/api/public/health` (or documented port) → healthy response.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add docker/docker-compose.prod.yml docker/monitoring/langfuse/ && git commit -m "feat(observability): 9-6 Langfuse self-host compose service"` → `git push`

### Step 2: LLM router trace instrumentation (3-2 integration)
- **Files:** `backend/app/adapters/llm/tracing.py`, `backend/app/adapters/llm/router.py` (3-2 integration point)
- **Do:** Wrap every LLM call in the `3-2` router with a Langfuse trace span carrying prompt name + version, token counts, latency, `tier` (cheap/strong/embedding per `rules/performance.md`), and `correlation_id` (per `rules/logging.md`: "Every event and log line tied to a pipeline run should carry `correlation_id`"). Tracing lives in `backend/app/adapters/llm/tracing.py`, called from the router — not duplicated per-provider adapter, so a new provider added later gets tracing for free. If `LANGFUSE_*` env is unset, this must be a true no-op (BR-3) — verified in Step 4, not assumed here.
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_tracing.py -k span_fields` → a traced call produces a span with all required fields (prompt name+version, tokens, latency, tier, correlation_id) populated correctly.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/llm/tracing.py backend/app/adapters/llm/router.py && git commit -m "feat(observability): 9-6 Langfuse trace spans on LLM router calls (3-2 integration)"` → `git push`

### Step 3: Fire-and-forget failure handling (BR-2)
- **Files:** `backend/app/adapters/llm/tracing.py`
- **Do:** Langfuse client calls wrapped so any failure (unreachable, timeout, auth error) never propagates into the pipeline — catch, emit exactly one warning log per run (not per call, to avoid log spam), and continue (BR-2, AC-2: "Tắt Langfuse giữa run → pipeline xong bình thường, 1 warning"). This mirrors the same fire-and-forget discipline already required of notification channels (`7-4`) — reuse that pattern if one already exists rather than inventing a second one.
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_tracing.py -k langfuse_down` → simulated Langfuse outage mid-run → pipeline run completes successfully, exactly 1 warning logged for the whole run (not per LLM call).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/llm/tracing.py && git commit -m "feat(observability): 9-6 fire-and-forget Langfuse failure handling, 1 warning per run (BR-2)"` → `git push`

### Step 4: Clean disable when env unconfigured (BR-3)
- **Files:** `backend/app/adapters/llm/tracing.py`, `backend/app/core/config.py` (or wherever `ProviderSettings`-equivalent config lives)
- **Do:** When `LANGFUSE_*` env vars are absent, tracing must be a true no-op — no connection attempt, no warning, no log noise (BR-3: "env không cấu hình → tắt sạch"). Same rule applies to Sentry DSN absence in Steps 5-6. Config check happens once at startup via the typed settings object, not `os.environ` read inline in the adapter (`rules/code-style.md`: "No adapter reads `os.environ`/`process.env` directly").
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_tracing.py -k no_env_configured` → with `LANGFUSE_*` unset, no outbound call attempted (mock asserts zero calls), no log line emitted.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/llm/tracing.py backend/app/core/config.py && git commit -m "feat(observability): 9-6 clean no-op when LANGFUSE_* unconfigured (BR-3)"` → `git push`

### Step 5: Sentry/GlitchTip backend + worker integration
- **Files:** `backend/app/core/sentry.py`, `render-worker/src/sentry.ts`, `backend/app/produce/sentry.py` (or wherever the `9-3` voice/asset worker entrypoint lives)
- **Do:** Initialize Sentry (or GlitchTip if the "Decisions already locked" fallback is exercised — the DSN endpoint shape is compatible either way, no code branching needed) in the backend API, the `9-2` render-worker, and the `9-3` voice/asset worker, each tagged with a `release` matching the current git SHA/tag (AC-3). `SENTRY_DSN` absent → clean disable, same BR-3 discipline as Step 4 — don't write a second disable pattern, reuse the same "check typed config once at startup" shape.
- **Verify:** `pytest backend/tests/unit/core/test_sentry.py -k release_tag` → initialized client reports the expected release tag; `-k no_dsn_configured` → absent DSN produces zero init calls.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/core/sentry.py render-worker/src/sentry.ts backend/app/produce/ && git commit -m "feat(observability): 9-6 Sentry/GlitchTip backend+worker init with git release tag"` → `git push`

### Step 6: Sentry frontend integration
- **Files:** `frontend/src/lib/sentry.ts`, `frontend/next.config.js` (or equivalent per the FE framework's Sentry SDK setup)
- **Do:** Initialize the Sentry browser SDK in the frontend, same release-tag discipline as Step 5 (AC-3), same clean-disable-when-unconfigured behavior (BR-3). Confirm no PII/secret ends up in FE error reports by default (breadcrumb scrubbing) — this is the FE analog of BR-1's backend trace/log denylist requirement.
- **Verify:** manual/browser exercise per `rules/testing.md` ("UI/frontend stories require exercising the feature in a real running browser") — throw a test error in the running FE app → appears in Sentry/GlitchTip with correct release tag.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/lib/sentry.ts frontend/next.config.js && git commit -m "feat(observability): 9-6 Sentry frontend init with release tag, no-PII breadcrumbs"` → `git push`

### Step 7: Denylist secret-scrub test (BR-1, reuse 9-4 pattern) + full AC coverage
- **Files:** `backend/tests/integration/observability/test_langfuse_sentry.py`
- **Do:** Reuse the shared denylist module from `9-4` (`backend/app/core/denylist.py`) to assert Langfuse trace samples never contain a key/token-shaped string (BR-1, AC-4) — do not write a second denylist pattern list, import the one `9-4` already built. Cover the remaining ACs end-to-end: open a real run in Langfuse and confirm the full node call chain with correct prompt version, filterable by `correlation_id` (AC-1, may require a manual/documented check against the Langfuse UI if not API-queryable in this step); FE+BE+worker thrown-error smoke test shows correct release tag in Sentry/GlitchTip (AC-3, ties to Steps 5-6).
- **Verify:** `pytest backend/tests/integration/observability/test_langfuse_sentry.py -v` → all AC-tagged tests pass, including the reused-denylist assertion.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests/integration/observability/ && git commit -m "test(observability): 9-6 denylist secret-scrub (reuse 9-4 pattern) + full AC coverage"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + smoke trong compose monitoring; BR-1 test tự động cùng pattern 9-4.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/9-6.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/9-6.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
