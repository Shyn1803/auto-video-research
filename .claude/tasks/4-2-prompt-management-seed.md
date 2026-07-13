# Task 4-2: Prompt Management + seed

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-1 · **FR:** FR-14
**State file:** [`state/4-2.json`](state/4-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-2-prompt-management-seed` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As an Admin, I want prompt lưu DB có version và kích hoạt được không cần deploy, so that tune chất lượng tiếng Việt liên tục.

## Why
FR-14. Chất lượng nội dung Việt phụ thuộc prompt nhiều hơn model; chu kỳ tune phải tính bằng phút, không bằng ngày.

## Scope
**In:** bảng prompts/prompt_versions; seed 8 prompt từ `docs/specs/prompts.md`; Jinja2 render + validate biến khai báo; `get_active_prompt(name)` cache invalidate-on-activate; tab Quản trị › Prompts (list/editor/diff 2 version/activate/rollback); CLI `make prompt-eval`.
**Out:** A/B prompt (v1.1); eval tự chấm bằng LLM (v1.1); prompt per-project.

## Business Rules
1. Đúng 1 version active/prompt (DB partial unique index).
2. Activate bản chưa chạy eval → dialog cảnh báo, không chặn cứng (trust admin, ghi audit).
3. Template dùng biến ngoài `variables[]` → 400 khi lưu.
4. Node không hardcode prompt — CI grep chuỗi template trong `pipeline/` → fail. See [rules/dependency-management.md](../rules/dependency-management.md).
5. Rollback = activate version cũ (không tạo bản sao — lịch sử thẳng).

## Acceptance Criteria
1. **(happy)** Sửa script.generate → v2 → activate → call kế dùng v2 (không restart); rollback v1 OK.
2. **(biên/BR-3)** Lưu template có `{{ bien_la }}` → 400 nêu đúng biến.
3. **(quyền)** Creator → 403; audit ghi ai activate lúc nào.
4. **(eval)** `make prompt-eval PROMPT=script.generate V=2` xuất bảng so sánh 10 topic.
5. **(BR-1)** Race 2 activate đồng thời → 1 thắng, constraint giữ đúng 1 active.

## Data & API
Bảng: prompts/prompt_versions. Endpoints §9. Contract change: không.

## Decisions already locked
- Eval là bước khuyến nghị mạnh, không bắt buộc cứng — tốc độ tune quan trọng giai đoạn đầu.

## Execution Steps

Work these in order. Update `state/4-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: prompts / prompt_versions schema + migration
- **Files:** `backend/app/models/prompt.py`, migration under `alembic/versions/`
- **Do:** create `prompts` and `prompt_versions` tables per Data & API §9. Enforce BR-1 (exactly 1 active version per prompt) with a DB **partial unique index** (`WHERE is_active`), not application-level locking alone.
- **Verify:** `alembic upgrade head` → tables exist; inserting 2 active versions for the same prompt name → constraint violation.
- **On failure:** transient → retry 3x; logic/config → `systematic-debugging` skill; still failing → block task, log in `memory/project-memory.md`.
- **Commit:** `git add backend/app/models/prompt.py alembic/ && git commit -m "feat(prompts): 4-2 prompts/prompt_versions schema + unique-active constraint" && git push`

### Step 2: Seed 8 prompts from docs/specs/prompts.md
- **Files:** `backend/app/pipeline/prompts/seed.py` (or migration data seed), referencing `docs/specs/prompts.md` §1-8
- **Do:** seed `research.summarize`, `ranking.score`, `factcheck.extract_claims`, `factcheck.verify_claim`, `outline.generate`, `script.generate`, `storyboard.generate`, `asset.query` verbatim from `docs/specs/prompts.md` — do not re-invent prompt content, copy the spec's template text and declared variables exactly.
- **Verify:** seed script/migration run → `SELECT count(*) FROM prompts` = 8, each with exactly 1 active version.
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 seed 8 prompts from prompts.md spec`.

### Step 3: Jinja2 render + variable validation (BR-3)
- **Files:** `backend/app/services/prompt_render.py`
- **Do:** render templates with Jinja2; validate that a template only references variables declared in its `variables[]` — using an undeclared variable at save time → 400 naming the exact missing variable(s) (BR-3).
- **Verify:** unit test: template with `{{ bien_la }}` not in `variables[]` → save raises 400 naming `bien_la` (AC2).
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 jinja2 render + variable validation`.

### Step 4: get_active_prompt(name) with invalidate-on-activate cache
- **Files:** `backend/app/services/prompt_render.py`
- **Do:** implement `get_active_prompt(name)` with an in-process (or shared) cache that's invalidated the moment a version is activated — no restart needed for a new active prompt to take effect (AC1).
- **Verify:** unit test: activate v2 → immediate next `get_active_prompt` call returns v2 without process restart.
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 get_active_prompt cache with invalidate-on-activate`.

### Step 5: CI grep guard — no hardcoded prompt strings in pipeline/ (BR-4)
- **Files:** CI script/lint config per `rules/dependency-management.md`
- **Do:** add a CI check that greps `backend/app/pipeline/` for literal prompt template strings (e.g. long Vietnamese instruction blocks) and fails the build if found — nodes must always call `get_active_prompt`, never inline a prompt.
- **Verify:** CI check fails against a deliberately-inlined test string, passes against clean `pipeline/` tree.
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 CI guard against hardcoded prompts in pipeline/`.

### Step 6: Activate / rollback endpoints + audit (BR-2, BR-5)
- **Files:** `backend/app/api/routes/prompts.py`, `backend/app/services/prompt_service.py`
- **Do:** `activate` endpoint: warn-but-don't-block if the version hasn't run eval (BR-2, dialog-level warning, not a hard 4xx); write an audit row (who/when) per `rules/security.md`. `rollback` = activate an older version — never creates a copy (BR-5, straight-line history).
- **Verify:** integration test: activate unevaluated version succeeds with a warning flag in the response; rollback re-activates v1 without creating v3.
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 activate/rollback endpoints + audit trail`.

### Step 7: RBAC — Creator forbidden from admin prompt actions (AC3)
- **Files:** `backend/app/api/routes/prompts.py`
- **Do:** apply RBAC middleware (per `rules/security.md` — not opt-in) so a Creator role gets 403 on prompt admin routes; only Admin can list/edit/activate.
- **Verify:** integration test: Creator token → 403 on activate/edit.
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 RBAC guard on prompt admin routes`.

### Step 8: Admin UI tab — Quản trị › Prompts
- **Files:** frontend route per `rules/folder-structure.md` (`src/app/admin/...`), list/editor/diff/activate/rollback components
- **Do:** build list view, editor (textarea with label per a11y), diff view between 2 versions (additions/removals with text prefix, not color-only), activate button (disabled + tooltip when already active per wireframe states).
- **Verify:** exercise in a real running browser per `rules/testing.md` UI rule — not just type-check.
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 admin Prompts tab UI`.

### Step 9: CLI make prompt-eval + eval_topics.json fixture (AC4)
- **Files:** `Makefile` (`prompt-eval` target), `tests/fixtures/eval_topics.json`
- **Do:** build `make prompt-eval PROMPT=script.generate V=2` outputting a comparison table across 10 diverse topics (length, parse-ok, numbers preserved). The 10-topic fixture is a long-lived test asset per DoD — pick varied topics (new model, tool, concept, news).
- **Verify:** `make prompt-eval PROMPT=script.generate V=2` → table renders with 10 rows.
- **On failure:** same policy as Step 1.
- **Commit:** `4-2 prompt-eval CLI + eval_topics fixture`.

### Step 10: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/prompts/...`, `backend/tests/integration/prompts/...`
- **Do:** one test per Acceptance Criterion (happy/biên/quyền/eval/BR-1 race); include a concurrency test for BR-1 (2 simultaneous activate calls → exactly 1 wins, per AC5).
- **Verify:** `pytest backend/tests/unit/prompts backend/tests/integration/prompts` → all pass.
- **On failure:** same policy as above.
- **Commit:** `4-2 complete AC test coverage`.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture eval_topics.json 10 topic là tài sản dùng lâu dài.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
