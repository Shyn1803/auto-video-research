# Task 8-1: Publish adapter interface + luồng chung

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 6-3 · **FR:** FR-12
**State file:** [`state/8-1.json`](state/8-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/8-1-publish-adapter-interface` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a developer, I want một interface publish chuẩn với capabilities từng nền tảng, so that thêm nền tảng mới là một adapter, và UI tự phản ánh nền tảng nào dùng được.

## Why
FR-12 kiến trúc tầng. Capabilities check (BR-3) chặn cả lớp lỗi "đăng video ngang lên nền tảng dọc" trước khi chúng thành lỗi API khó hiểu.

## Scope
**In:** `PublishAdapter` base (upload/get_status/capabilities: max_duration, formats, disclosure_supported); chuẩn hoá adapter `download` (6-3); vòng đời publishes đầy đủ; API publish/preview §8; retry backoff upload; UI tab Xuất bản mở rộng: bảng nền tảng theo provider state, form metadata prefill, khối hẹn giờ (UI — job 8-4).
**Out:** adapter YouTube (8-2), TikTok/FB/LinkedIn (10-3); analytics (8-5).

## Business Rules
1. Platform inactive không ẩn — hiện kèm lý do + hướng dẫn.
2. Metadata sửa tại màn publish chỉ áp cho lần đăng đó — không sửa script version.
3. Capabilities check trước đăng (format/duration/disclosure) → chặn kèm giải thích + gợi ý.
4. Retry upload tối đa 3 với backoff; hết → failed + notify; retry tay được.

## Acceptance Criteria
1. **(happy)** Chỉ download active → bảng đúng wireframe; vòng đời pending→published ghi đủ.
2. **(biên/BR-3)** Đăng 16:9 lên platform dọc-only (mock) → chặn + gợi ý bản 9:16.
3. **(lỗi/BR-4)** Upload fail 3 lần (mock) → failed + notify; nút retry chạy lại.
4. **(quyền)** 🅞 đúng; creator khác 403.
5. **(BR-2)** Sửa title lúc đăng → publishes.title khác script; script version nguyên vẹn.

## Data & API
Bảng: publishes. Endpoints §8. Contract change: không.

## Decisions already locked
- Vòng đời publish: pending→scheduled→uploading→published/failed (schema sẵn) — không thêm trạng thái.

## Execution Steps

Work these in order. Update `state/8-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: PublishAdapter base + registry
- **Files:** `backend/app/adapters/publish/base.py`, `backend/app/adapters/publish/__init__.py` (registry decorator)
- **Do:** define `PublishAdapter(ABC)` per [patterns/provider-adapter.md](../patterns/provider-adapter.md): `name`, `is_paid`, `async available()`, `async upload(req) -> PublishResult` (raises `ProviderError(retryable: bool)`), `async get_status(external_id)`, and a `capabilities` property/model (`max_duration`, `formats`, `disclosure_supported`). Add `@register_publish("{provider}")` decorator mirroring the TTS example in the pattern doc.
- **Verify:** `mypy backend/app/adapters/publish/base.py --strict` → 0 errors.
- **On failure:** transient (env/tooling) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/adapters/publish/ && git commit -m "feat(publish): 8-1 add PublishAdapter base + registry"` → `git push`

### Step 2: Mock adapter "fakeplatform"
- **Files:** `backend/app/adapters/publish/fakeplatform.py`, `tests/fixtures/publish/fakeplatform.py`
- **Do:** implement `FakePlatform(PublishAdapter)` with configurable capabilities (vertical-only formats, max_duration, disclosure_supported toggles) so BR-3 branches (format/duration/disclosure block) can be exercised in tests here and reused by 10-3.
- **Verify:** `pytest backend/tests/unit/adapters/publish/test_fakeplatform.py -q` → passes (write a minimal smoke test alongside the fixture).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/publish/fakeplatform.py tests/fixtures/publish/ && git commit -m "feat(publish): 8-1 add fakeplatform mock adapter"` → `git push`

### Step 3: publishes lifecycle service
- **Files:** `backend/app/services/publish_service.py`, `backend/app/schemas/publish.py`
- **Do:** implement the full `publishes` lifecycle (`pending→scheduled→uploading→published/failed` — no new states per "Decisions already locked"); capabilities pre-check (BR-3) before calling adapter `upload()`, returning an explanation + suggestion (e.g. "dùng bản 9:16") on block; metadata edits (BR-2) write to `publishes.title`/etc without touching script version; retry-with-backoff on upload failure, max 3 attempts, then `failed` + notify (BR-4), with a manual retry entrypoint.
- **Verify:** `mypy backend/app/services/publish_service.py --strict` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/publish_service.py backend/app/schemas/publish.py && git commit -m "feat(publish): 8-1 add publishes lifecycle service"` → `git push`

### Step 4: Publish/preview API endpoints
- **Files:** `backend/app/api/routes/publish.py` (per §8 api-spec), router registration
- **Do:** implement publish/preview endpoints per `docs/specs/api-spec.md` §8; router calls `publish_service` only, no business logic in the router (per `rules/code-style.md`); enforce ownership (creator 403 on others' resources, admin 🅞 allowed) per AC4.
- **Verify:** `pytest backend/tests/integration/api/test_publish_routes.py -q` → passes (write integration tests covering ownership).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/routes/publish.py && git commit -m "feat(publish): 8-1 add publish/preview API endpoints"` → `git push`

### Step 5: Xuất bản tab UI — platform table, metadata form, schedule block
- **Files:** frontend route/components under `src/app/projects/[id]/` per `rules/folder-structure.md` (publish tab), matching wireframe **Xuất bản**
- **Do:** platform table reflecting provider state (BR-1: inactive shown with reason, not hidden), row states (default/loading/empty N/A/error with retry/disabled), metadata form prefilled from script, scheduling block UI shell (job wiring is 8-4's scope — this step is UI only). Standardize the `download` step (6-3) as the adapter's shared input contract.
- **Verify:** exercise the tab in a real running browser (per `rules/testing.md` UI rule) — take a screenshot confirming table/states match wireframe; run `npm run typecheck` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add src/app/... && git commit -m "feat(publish): 8-1 add Xuất bản tab UI"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `tests/unit/adapters/publish/`, `backend/tests/unit/services/test_publish_service.py`, `backend/tests/integration/api/test_publish_routes.py`
- **Do:** one test per Acceptance Criterion (AC1 happy lifecycle, AC2 BR-3 capabilities block, AC3 BR-4 retry-exhaustion, AC4 ownership 403, AC5 BR-2 metadata-edit-doesn't-touch-script-version); mock HTTP with `respx` for the fakeplatform adapter per `rules/testing.md`.
- **Verify:** `pytest backend/tests/unit/adapters/publish backend/tests/unit/services/test_publish_service.py backend/tests/integration/api/test_publish_routes.py -q` → all AC-mapped tests pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests/ && git commit -m "test(publish): 8-1 cover all acceptance criteria"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock adapter "fakeplatform" với capabilities cấu hình được (dùng test BR-3 đủ nhánh, tái dùng ở 10-3).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/8-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/8-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
