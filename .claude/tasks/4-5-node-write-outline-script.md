# Task 4-5: Node Write — outline + script

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-4, 4-2 · **FR:** FR-05, FR-06
**State file:** [`state/4-5.json`](state/4-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-5-node-write-outline-script` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want dàn ý rồi kịch bản tiếng Việt có dẫn nguồn từng phần, so that tôi chỉ biên tập thay vì viết từ đầu, và luôn truy được mọi câu về nguồn.

## Why
FR-05/06. Ràng buộc "chỉ dùng fact đã kiểm chứng" là điểm nối giữa fact-check và nội dung — nơi hallucination bị chặn lần cuối trước khi thành lời đọc.

## Scope
**In:** outline (prompt §5 — 7 phần, dẫn [source_id], chỉ claim PASS/WARN-đã-duyệt); script (prompt §6 — giữ số liệu; check tự động tập số outline ⊆ script, lệch → retry 1 → cờ warning); 2 sub-step approve riêng; PUT version sửa tay.
**Out:** UI (5-7); tone/style tuỳ chọn (v1.1).

## Business Rules
1. Claim FAIL "loại khỏi video" → nội dung đó không xuất hiện outline/script (lọc context trước prompt).
2. voice_over viết số thành chữ đọc được; validator cảnh báo nếu còn ký hiệu (%/$) trong voice_over.
3. Title >70 ký tự → cắt thông minh tại ranh giới từ + cờ cho user xem.
4. Claim WARN dùng trong script → câu đó kèm "theo nguồn chưa xác nhận" (prompt yêu cầu + validator kiểm sự hiện diện).

## Acceptance Criteria
1. **(happy)** Outline 7 phần đủ [source_id]; script đúng cấu trúc; tập số khớp.
2. **(biên/BR-1)** Claim FAIL bị loại → không xuất hiện trong outline.
3. **(biên/BR-4)** Claim WARN được dùng → câu chứa "theo nguồn chưa xác nhận".
4. **(lỗi/BR-2,3)** Script lệch số sau retry → version có warnings; title dài → cắt + warning.
5. **(version)** Sửa outline tay → script sinh từ bản sửa (parent đúng — 1-5 BR-5).

## Data & API
Dữ liệu: step_versions (outline, script) + warnings trong content JSONB. Contract change: **có** — chuẩn hoá `warnings[]` trong content version → ghi vào api-spec §3.

## Decisions already locked
- ⏳ Không chặn cứng khi lệch số sau retry — con người quyết (cờ warning + UI nêu rõ).

## Execution Steps

Work these in order. Update `state/4-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: warnings[] contract normalization + contract-change to api-spec §3
- **Files:** `backend/app/schemas/step_version.py`, `docs/specs/api-spec.md` §3
- **Do:** define the normalized `warnings: [{type, detail}]` shape on `step_versions` content JSONB (BR-2/BR-3/BR-4 all emit warnings through this one shape). This is a "đổi contract" change — update `docs/specs/api-spec.md` §3 in the same PR per `rules/documentation.md`.
- **Verify:** Pydantic schema validates a sample `warnings[]` payload; api-spec §3 diff present.
- **On failure:** transient → retry 3x; logic/config → `systematic-debugging` skill; still failing → block task, log in `memory/project-memory.md`.
- **Commit:** `git add backend/app/schemas/step_version.py docs/specs/api-spec.md && git commit -m "feat(write): 4-5 normalize warnings[] content contract" && git push`

### Step 2: Claim filtering before prompt context (BR-1)
- **Files:** `backend/app/pipeline/nodes/write/context.py`
- **Do:** build outline/script prompt context by filtering out any content tied to a FAIL claim — filtering happens before the prompt call, not after (BR-1: FAIL content must never reach the LLM context, let alone the output).
- **Verify:** unit test: source content containing a FAIL claim's keyword → absent from built context.
- **On failure:** same policy as Step 1.
- **Commit:** `4-5 filter FAIL-claim content out of write context`.

### Step 3: Outline node (outline.generate prompt, §5)
- **Files:** `backend/app/pipeline/nodes/write/outline.py`
- **Do:** call `get_active_prompt("outline.generate")` (from 4-2, per `docs/specs/prompts.md` §5 — do not re-invent prompt content); require 7 sections, each citing `[source_id]`, using only PASS/approved-WARN claims.
- **Verify:** unit test: fixture research+factcheck output → outline has 7 sections, every section cites at least one `[source_id]`.
- **On failure:** same policy as Step 1.
- **Commit:** `4-5 outline node (7-section, source-cited)`.

### Step 4: Script node (script.generate prompt, §6) + number-set validator
- **Files:** `backend/app/pipeline/nodes/write/script.py`, `backend/app/pipeline/nodes/write/validators.py`
- **Do:** call `get_active_prompt("script.generate")` per `docs/specs/prompts.md` §6, preserving figures. Implement the "tập số outline ⊆ script" check as a **pure function** (`validators.py`) comparing normalized number sets (handle `92,5` vs `92.5` vs written-out forms — normalize before compare, per DoD note). On mismatch: retry once, then flag a warning (not a hard fail) per "Decisions already locked".
- **Verify:** `pytest backend/tests/unit/pipeline/nodes/write/test_number_set.py` → normalization + subset-check unit tests pass across all three number formats (this is called out as the highest-scrutiny unit test in this task).
- **On failure:** same policy as Step 1 for infra bugs; a genuine subset-check failure on real fixtures needs `systematic-debugging`, not blind retry.
- **Commit:** `4-5 script node + number-set subset validator (pure function)`.

### Step 5: voice_over readability validator (BR-2)
- **Files:** `backend/app/pipeline/nodes/write/validators.py`
- **Do:** validator warns if `voice_over` still contains raw symbols (`%`, `$`) instead of spoken-word numerals — the prompt is expected to spell numbers out, but the validator catches slip-throughs (BR-2).
- **Verify:** unit test: `voice_over` containing `%` → warning emitted with correct `type`.
- **On failure:** same policy as Step 1.
- **Commit:** `4-5 voice_over symbol-leak validator`.

### Step 6: Title length guard (BR-3)
- **Files:** `backend/app/pipeline/nodes/write/validators.py`
- **Do:** title >70 chars → truncate at a word boundary (not mid-word) and flag a warning for the user to see — never a silent cut (BR-3).
- **Verify:** unit test: 80-char title → truncated at word boundary, warning present with original length noted.
- **On failure:** same policy as Step 1.
- **Commit:** `4-5 title length truncation + warning`.

### Step 7: WARN-claim disclosure enforcement (BR-4)
- **Files:** `backend/app/pipeline/nodes/write/validators.py`
- **Do:** any script sentence built from a WARN claim must contain the phrase "theo nguồn chưa xác nhận" — the prompt is instructed to add it (BR-4), and the validator checks its actual presence rather than trusting the LLM.
- **Verify:** unit test: WARN claim used in script → validator confirms disclosure phrase present in that sentence; missing phrase → validator flags it.
- **On failure:** same policy as Step 1.
- **Commit:** `4-5 WARN-claim disclosure presence validator`.

### Step 8: Two sub-step approvals + PUT version manual edit + parent lineage (AC5)
- **Files:** `backend/app/api/routes/step_versions.py`
- **Do:** wire outline and script as two separately-approvable sub-steps; support `PUT` to manually edit a version; ensure editing outline by hand and regenerating script correctly sets `parent` lineage to the edited version (reuses 1-5 BR-5 versioning).
- **Verify:** integration test: manual outline edit → regenerate script → script version's parent points to the edited outline version, not an earlier one.
- **On failure:** same policy as Step 1.
- **Commit:** `4-5 sub-step approvals + manual edit + parent lineage`.

### Step 9: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `tests/unit/pipeline/nodes/write/...`, `backend/tests/integration/pipeline/test_write_node.py`
- **Do:** one test per Acceptance Criterion (happy/BR-1/BR-4/BR-2,3/version-lineage).
- **Verify:** `pytest backend/tests/unit/pipeline/nodes/write backend/tests/integration/pipeline/test_write_node.py` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** `4-5 complete AC test coverage`.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + check "tập số ⊆" là pure function, unit kỹ (định dạng 92,5 vs 92.5 vs chữ, so sánh sau chuẩn hoá).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
