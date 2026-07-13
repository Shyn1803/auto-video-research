# Task 3-3: LLM adapters — ollama, gemini, groq, openrouter + mock + embedding

**Points:** 5đ · **Epic:** 3 — Provider framework · **Depends:** 3-2 · **FR:** FR-18
**State file:** [`state/3-3.json`](state/3-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/3-3-llm-adapters` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a pipeline, I want gọi LLM local lẫn cloud free-tier qua cùng một interface có structured output, so that đổi model chỉ là đổi config và output luôn parse được.

## Why
Hiện thực chiến lược "local-first, free-tier-second" của SRS §1.2. Structured output + retry parse là điều kiện để pipeline chạy ổn với model local.

## Scope
**In:** 4 adapter (ollama/gemini/groq/openrouter) + `mock` (fixture theo prompt name — deterministic CI); `call_structured(tier, prompt_name, schema)` (JSON mode ollama, responseSchema gemini; retry parse 2); token counting + cost estimate; embedding `bge_m3_local` + `gemini_embedding`.
**Out:** mistral (1 file sau, pattern sẵn); model routing per-task nâng cao.

## Business Rules
1. Parse fail lần 3 → non-retryable kèm raw output trong log debug.
2. Mock adapter chỉ chạy `APP_ENV` development/test — guard cứng.
3. Provider free ghi cost=0 nhưng vẫn ghi tokens (theo dõi quota).
4. openrouter lọc model `:free` cho `openrouter_free`; `openrouter_paid` cần cả key + ALLOW_PAID.

## Acceptance Criteria
1. **(happy)** Chỉ OLLAMA_URL → ma trận đúng; call_structured trả Pydantic hợp lệ trên ollama.
2. **(biên)** Thêm GEMINI key qua UI → health pass → chain nhận không restart.
3. **(biên/BR-1)** Model trả JSON hỏng 3 lần (mock) → fail kèm raw output.
4. **(embedding)** 2 đoạn Việt cùng chủ đề → cosine > ngưỡng; khác chủ đề < ngưỡng.
5. **(BR-2)** `APP_ENV=production` + chain chứa mock → app từ chối start.

## Data & API
Bảng giá: file config `pricing.yaml` (không hardcode); llm_usage ghi qua router.

## Decisions already locked
- ⏳ BGE-M3 chạy trong process backend v1 (không service riêng) — tách khi 9-3 nếu nghẽn.

## Execution Steps

Work these in order. Update `state/3-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Ollama adapter (local, free, always-available baseline)
- **Files:** `backend/app/adapters/llm/ollama.py`, `backend/tests/unit/adapters/llm/test_ollama.py`
- **Do:** `@register_llm("ollama")` class inheriting `LLMAdapter` from 3-1's base, `is_paid=False`. `available()` checks `OLLAMA_URL` reachability. Implement JSON-mode structured calls (Ollama's native JSON mode) as the concrete half of `call_structured`.
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_ollama.py -v` → passes, HTTP mocked with `respx`, no live network call (per [rules/testing.md](../rules/testing.md)).
- **On failure:** transient → retry 3×; logic error → `systematic-debugging` skill; still failing → mark step/task `blocked`, log in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/adapters/llm/ollama.py backend/tests/unit/adapters/llm/test_ollama.py && git commit -m "feat(adapters): 3-3 ollama LLM adapter" && git push`

### Step 2: Gemini adapter (free tier + paid)
- **Files:** `backend/app/adapters/llm/gemini.py`, `backend/tests/unit/adapters/llm/test_gemini.py`
- **Do:** `@register_llm("gemini")`, structured output via `responseSchema`. `available()` = key present (env or DB, via `ProviderSettings`). Add entry to `docs/CONFIGURATION.md` provider table per [rules/dependency-management.md](../rules/dependency-management.md).
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_gemini.py -v` → passes, respx-mocked.
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/llm/gemini.py backend/tests/unit/adapters/llm/test_gemini.py docs/CONFIGURATION.md && git commit -m "feat(adapters): 3-3 gemini LLM adapter" && git push`

### Step 3: Groq adapter
- **Files:** `backend/app/adapters/llm/groq.py`, `backend/tests/unit/adapters/llm/test_groq.py`
- **Do:** `@register_llm("groq")`, free-tier, `is_paid=False`. Add `docs/CONFIGURATION.md` entry.
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_groq.py -v` → passes, respx-mocked.
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/llm/groq.py backend/tests/unit/adapters/llm/test_groq.py docs/CONFIGURATION.md && git commit -m "feat(adapters): 3-3 groq LLM adapter" && git push`

### Step 4: OpenRouter adapter — `openrouter_free` / `openrouter_paid` split (BR-4)
- **Files:** `backend/app/adapters/llm/openrouter.py`, `backend/tests/unit/adapters/llm/test_openrouter.py`
- **Do:** Two registered names, `@register_llm("openrouter_free")` (`is_paid=False`, filters model list to `:free`-suffixed models only) and `@register_llm("openrouter_paid")` (`is_paid=True`, requires both a key and `ALLOW_PAID=true` per the router's BR-1 gate from 3-2). Add `docs/CONFIGURATION.md` entries for both.
- **Verify:** unit test confirming `openrouter_free` never selects a non-`:free` model.
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/llm/openrouter.py backend/tests/unit/adapters/llm/test_openrouter.py docs/CONFIGURATION.md && git commit -m "feat(adapters): 3-3 openrouter free/paid split adapters" && git push`

### Step 5: Mock adapter with `APP_ENV` hard guard (BR-2)
- **Files:** `backend/app/adapters/llm/mock.py`, `backend/tests/unit/adapters/llm/test_mock.py`
- **Do:** `@register_llm("mock")`, returns deterministic fixtures keyed by `prompt_name` for CI determinism. Hard-guard: raise at startup if `APP_ENV=production` and `mock` appears in any resolved chain (AC5) — this belongs in router/startup validation (3-2), not just the adapter; wire the check where chain resolution happens.
- **Verify:** unit test: `APP_ENV=production` + chain containing `mock` → app startup validation raises/refuses (AC5).
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/llm/mock.py backend/tests/unit/adapters/llm/test_mock.py && git commit -m "feat(adapters): 3-3 mock LLM adapter with production guard" && git push`

### Step 6: `call_structured` retry-parse policy (BR-1) + token/cost accounting (BR-3)
- **Files:** `backend/app/adapters/llm/base.py` (or shared helper), `backend/app/config/pricing.yaml`
- **Do:** Shared `call_structured(tier, prompt_name, schema)` retries parse failures up to 2 additional times (3 total attempts); on the 3rd failure, raise non-retryable with raw output attached to the debug log (never swallowed, per [rules/error-handling.md](../rules/error-handling.md) — BR-1/AC3). Token counting + cost estimate read from `pricing.yaml` (never hardcoded, per Data & API note) — free providers record `cost=0` but still record token counts for quota tracking (BR-3).
- **Verify:** unit test with a mock provider returning malformed JSON 3× → fails on 3rd with raw output in the log capture; separate test asserting a free-provider call logs tokens with cost=0.
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/llm/base.py backend/app/config/pricing.yaml && git commit -m "feat(adapters): 3-3 structured-call retry-parse + pricing.yaml cost estimate" && git push`

### Step 7: Embedding adapters — `bge_m3_local` + `gemini_embedding`
- **Files:** `backend/app/adapters/llm/embedding_bge_m3.py`, `backend/app/adapters/llm/embedding_gemini.py`, `backend/tests/unit/adapters/llm/test_embedding.py`
- **Do:** `bge_m3_local` runs in-process in the backend (decision already locked ⏳, not a separate service). `gemini_embedding` calls the Gemini embedding endpoint. Use the fixture set (6 labeled Vietnamese sentence pairs) for the cosine-similarity threshold test.
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_embedding.py -v` → same-topic pairs cosine > threshold, different-topic pairs < threshold (AC4).
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/llm/embedding_bge_m3.py backend/app/adapters/llm/embedding_gemini.py backend/tests/unit/adapters/llm/test_embedding.py && git commit -m "feat(adapters): 3-3 bge_m3_local and gemini_embedding adapters" && git push`

### Step 8: Nightly `@external` smoke marker
- **Files:** `backend/tests/integration/test_llm_smoke.py`
- **Do:** Add `@external`-marked tests, one real call per provider that has a configured key, per Test Notes ("nightly @external: 1 call thật mỗi provider có key"). These are excluded from the default `pytest` run (marker config in `backend/pyproject.toml`).
- **Verify:** `pytest -m external --collect-only` → lists exactly the provider smoke tests; default `pytest` run does not execute them.
- **On failure:** same policy.
- **Commit:** `git add backend/tests/integration/test_llm_smoke.py backend/pyproject.toml && git commit -m "test(adapters): 3-3 nightly @external smoke tests per provider" && git push`

### Step 9: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/adapters/llm/`
- **Do:** Confirm one test exists per AC (1–5); run the full matrix scenario for AC1 (only `OLLAMA_URL` set → ollama ✓, rest "thiếu key").
- **Verify:** `pytest backend/tests/unit/adapters/llm -v` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** `git add backend/tests/unit/adapters/llm && git commit -m "test(adapters): 3-3 full AC coverage for LLM adapters" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + nightly `@external` smoke (1 call thật/provider có key).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/3-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/3-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
