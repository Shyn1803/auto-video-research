# Task 3-1: Adapter base + registry + config layer

**Points:** 3đ · **Epic:** 3 — Provider framework · **Depends:** 1-1 · **FR:** FR-21
**State file:** [`state/3-1.json`](state/3-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/3-1-adapter-base-registry-config-layer` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a developer, I want khung adapter chuẩn cho mọi năng lực bên ngoài, so that thêm provider mới là 1 file + 1 decorator, không đụng business logic.

## Why
FR-21 là yêu cầu trung tâm của SRS ("local-first, kích hoạt bằng key"). Pattern adapter là việc lặp lại nhiều nhất toàn dự án (≥15 adapter đến release) — see [patterns/provider-adapter.md](../patterns/provider-adapter.md).

## Scope
**In:** base class 7 capability (LLM/TTS/Search/ImageGen/AssetStock/Storage/Publish) + `@register_{cap}(name)`; hợp nhất TTSAdapter 2-4 vào khung; `ProviderSettings` (env override DB); `ProviderError(retryable)`; adapter mẫu + test mẫu làm chuẩn copy.
**Out:** router chain (3-2); adapter cụ thể (3-3+); notification adapter (7-4 — dùng cùng khung).

## Business Rules
1. Adapter không đọc env/DB trực tiếp — nhận `ProviderSettings`.
2. Adapter không ghi usage/log nghiệp vụ — chỉ raise/return (việc của router). See [anti-patterns/direct-provider-call.md](../anti-patterns/direct-provider-call.md).
3. Registry trùng tên → fail startup (không ghi đè lặng lẽ).
4. Mỗi adapter khai báo `is_paid` tĩnh — quên khai = mặc định True (an toàn chi phí).

## Acceptance Criteria
1. **(happy)** Provider demo mới: 1 file + decorator → có trong registry, gọi được qua router mock.
2. **(lỗi/BR-3)** 2 adapter trùng tên → app không start, message chỉ rõ 2 file.
3. **(BR-4)** Adapter không khai is_paid → được coi paid (test).
4. **(chuẩn)** mypy strict pass; test mẫu chạy không network.

## Decisions already locked
- 7 capability cố định v1 — thêm capability mới cần ADR nhỏ.

## Execution Steps

Work these in order. Update `state/3-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: ProviderError + capability base classes
- **Files:** `backend/app/adapters/base.py`
- **Do:** Define `ProviderError(Exception)` with a `retryable: bool` field (per [rules/error-handling.md](../rules/error-handling.md) — adapters only ever raise this, never a raw HTTP/SDK exception). Define one ABC per capability — `LLMAdapter`, `TTSAdapter`, `SearchAdapter`, `ImageGenAdapter`, `AssetStockAdapter`, `StorageAdapter`, `PublishAdapter` — each with `name: str`, `is_paid: bool = True` (BR-4: default is paid so a forgotten override is cost-safe, not cost-unsafe), an abstract `async def available(self) -> bool`, and the one capability-specific abstract method (e.g. `call_structured` for LLM, `synthesize` for TTS) per [patterns/provider-adapter.md](../patterns/provider-adapter.md).
- **Verify:** `python -c "import app.adapters.base"` (or `uv run python -c ...` once `backend/pyproject.toml` exists) → no import error, all 7 classes present.
- **On failure:** transient (env/tooling) → retry 3×; logic error → `systematic-debugging` skill; still failing → mark step `blocked` in state file, log in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/adapters/base.py && git commit -m "feat(adapters): 3-1 add ProviderError and 7 capability base classes" && git push`

### Step 2: Registry decorator with duplicate-name fail-startup (BR-3)
- **Files:** `backend/app/adapters/registry.py`
- **Do:** Implement a registry `dict[(capability, name), type]` plus `register_llm(name)`, `register_tts(name)`, ... decorator factories (one per capability, or one generic `register(capability, name)` used by 7 thin wrappers). Registering a `(capability, name)` pair that already exists raises at decoration/import time with a message naming both the new and the already-registered module/file (AC2) — never silently overwrites.
- **Verify:** unit test asserting a duplicate registration raises with both file names in the message text.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/registry.py && git commit -m "feat(adapters): 3-1 registry decorator with duplicate-name guard" && git push`

### Step 3: `ProviderSettings` config layer (BR-1)
- **Files:** `backend/app/core/config.py`
- **Do:** `ProviderSettings` (pydantic-settings) that resolves each capability's config with precedence env > `api_keys` DB table > default, per [rules/configuration-env.md](../rules/configuration-env.md). Adapters receive a `ProviderSettings` instance through their constructor/call signature — never call `os.environ`/`os.getenv` directly (BR-1, [rules/code-style.md](../rules/code-style.md)).
- **Verify:** unit test instantiating `ProviderSettings` from a fake env dict and asserting precedence order.
- **On failure:** same policy.
- **Commit:** `git add backend/app/core/config.py && git commit -m "feat(core): 3-1 ProviderSettings env/DB precedence layer" && git push`

### Step 4: Align story 2-4's TTS adapter with the new base (if it exists yet)
- **Files:** `backend/app/adapters/tts/base.py`, `backend/app/adapters/tts/*.py`
- **Do:** Check `sprint-status.yaml` / the repo for story 2-4's TTS adapter. If it already exists as a standalone class, refactor it to inherit `TTSAdapter` from `backend/app/adapters/base.py` and register via `@register_tts(...)` — this is the "hợp nhất TTSAdapter 2-4 vào khung" scope item. If 2-4 has not landed yet (likely, this is a pre-code repo), skip the merge and instead leave a one-line note in `memory/project-memory.md` Open Questions that 2-4's adapter must inherit this base when it lands — do not block this task on work that doesn't exist yet.
- **Verify:** if merged: existing TTS tests (if any) still pass. If skipped: note is present in memory file.
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/tts/ .claude/memory/project-memory.md && git commit -m "chore(adapters): 3-1 align TTS adapter with base framework" && git push` (only if there were file changes to commit)

### Step 5: Sample adapter + sample test (the copy-paste template, AC1)
- **Files:** `backend/app/adapters/llm/demo.py`, `backend/tests/unit/adapters/llm/test_demo.py`
- **Do:** A minimal demo LLM adapter (1 file, `@register_llm("demo")`) that is the literal template future adapters copy — per [patterns/provider-adapter.md](../patterns/provider-adapter.md) and dev-guide.md §3. It must be reachable through a mocked router call in the test (registry lookup → instantiate → call). This file is treated as a living document per this task's DoD — keep it exemplary, it is the review bar for ~15 future adapters.
- **Verify:** `pytest backend/tests/unit/adapters/llm/test_demo.py -v` → passes, no network call.
- **On failure:** same policy.
- **Commit:** `git add backend/app/adapters/llm/demo.py backend/tests/unit/adapters/llm/test_demo.py && git commit -m "feat(adapters): 3-1 demo adapter as copy-paste template" && git push`

### Step 6: BR-4 default-paid test + registry duplicate-startup test (AC2, AC3)
- **Files:** `backend/tests/unit/adapters/test_registry.py`
- **Do:** Test 1: an adapter subclass that omits `is_paid` is treated as `is_paid=True` (BR-4/AC3). Test 2: registering two adapters under the same `(capability, name)` raises at startup with a message naming both files (BR-3/AC2) — simulate via two dummy classes in the test module, assert on the exception message content.
- **Verify:** `pytest backend/tests/unit/adapters/test_registry.py -v` → both tests pass.
- **On failure:** same policy.
- **Commit:** `git add backend/tests/unit/adapters/test_registry.py && git commit -m "test(adapters): 3-1 BR-4 default-paid and BR-3 duplicate-registry tests" && git push`

### Step 7: mypy strict + docs/CONFIGURATION.md entry
- **Files:** `backend/pyproject.toml` (mypy strict scope), `docs/CONFIGURATION.md`
- **Do:** Ensure `backend/app/adapters/`, `backend/app/core/config.py` are covered by mypy strict (AC4). Add the `demo` adapter to `docs/CONFIGURATION.md`'s provider table as the documented example entry, per [rules/dependency-management.md](../rules/dependency-management.md) rule "new provider entry added to CONFIGURATION.md's provider table in the same PR."
- **Verify:** `mypy --strict backend/app/adapters backend/app/core/config.py` → exit 0.
- **On failure:** logic/type error → fix types, don't loosen strictness; still failing after 3 attempts → block per policy.
- **Commit:** `git add backend/pyproject.toml docs/CONFIGURATION.md && git commit -m "docs(config): 3-1 CONFIGURATION.md demo provider entry + mypy strict scope" && git push`

### Step 8: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/adapters/`
- **Do:** One test per AC tagged above (happy/lỗi/BR-4/chuẩn); confirm no test makes a network call (respx mock if any HTTP is exercised, per [rules/testing.md](../rules/testing.md)).
- **Verify:** `pytest backend/tests/unit/adapters -v` → all AC-mapped tests pass; `mypy --strict backend/app/adapters` → exit 0.
- **On failure:** same policy as above.
- **Commit:** `git add backend/tests/unit/adapters && git commit -m "test(adapters): 3-1 full AC coverage for adapter base/registry/config" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + test mẫu là tài liệu sống, review PR đầu tiên khắt khe (là khuôn cho ~15 adapter sau).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/3-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/3-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
