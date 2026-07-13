# Task 4-8: Điểm vào "Có sẵn kịch bản"

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-4, 4-6, 1-3 · **FR:** FR-06, Mode 2
**State file:** [`state/4-8.json`](state/4-8.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-8-diem-vao-co-san-kich-ban` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want dán kịch bản tôi đã viết sẵn và đi thẳng tới dựng cảnh, so that video từ script có sẵn mất vài phút thay vì đi qua 2 bước nghiên cứu–viết không cần thiết.

## Why
Use case thực tế phổ biến. Quyết định giữ nguyên hàng rào: **fact-check vẫn chạy trên script dán vào** — không có đường nào ra video mà bỏ qua kiểm chứng.

## Scope
**In:** nhánh "Có sẵn kịch bản" trong modal Tạo dự án (thay nhánh "tạo trống" — đã bỏ); graph entry thứ 2: script → extract claims → factcheck (evidence tìm qua search với claim làm query) → gate như thường → storyboard; script dán lưu thành script v1 (created_by=user); title/description/tags sinh bằng AI từ script; trạm Nghiên cứu + Nội dung trên stepper hiển thị trạng thái "bỏ qua có kiểm chứng".
**Out:** import file docx/URL (v1.1); dịch script ngôn ngữ khác; nhảy thẳng tới scene JSON (storyboard vẫn chạy).

## Business Rules
1. Fact-check bắt buộc — claim FAIL vẫn chặn như luồng thường; evidence tìm bằng search chain.
2. Script dán 100-3000 ký tự; ngoài khoảng → validate với hướng dẫn.
3. Stepper: Nghiên cứu hiển thị "— bỏ qua", Nội dung hiển thị "✓ từ kịch bản của bạn" — user vẫn click vào Nội dung để sửa script.
4. project đánh dấu `entry_point=script` (phân tích 8-7 tách nhóm này khi so hiệu quả).

## Acceptance Criteria
1. **(happy)** Dán script 800 ký tự → kiểm chứng chạy → Phân cảnh có scene_set; title/tags đã sinh; script v1 created_by=user.
2. **(biên/BR-1)** Script chứa claim sai (fixture) → FAIL → NEED_REVIEW, xử lý bằng UI 5-6 như luồng thường.
3. **(biên/BR-3)** Click trạm Nội dung sau khi vào từ script → sửa được, tạo v2, storyboard stale đúng cascade.
4. **(lỗi/BR-2)** Script 50 ký tự → chặn kèm hướng dẫn.
5. **(quyền)** Như luồng tạo project thường.

## Data & API
`projects.entry_point` (cột mới, migration); `POST /projects` nhận `script_text?` → cập nhật api-spec §2 + database-schema. Graph: conditional entry (LangGraph branch) — không node mới. Contract change: **có**.

## Decisions already locked
- Thay nhánh "tạo trống" bằng nhánh này (PO duyệt 2026-07-11).
- Fact-check không thể bỏ qua kể cả entry này.

## Execution Steps

Work these in order. Update `state/4-8.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: projects.entry_point column + contract-change to api-spec/database-schema
- **Files:** migration under `alembic/versions/`, `backend/app/models/project.py`, `docs/specs/api-spec.md` §2, `docs/specs/database-schema.md`
- **Do:** add `entry_point` column to `projects` (values include `research`/`script`, per BR-4). `POST /projects` accepts optional `script_text`. Contract change — update both specs in the same PR per `rules/documentation.md`.
- **Verify:** `alembic upgrade head` → column exists; api-spec/database-schema diffs present.
- **On failure:** transient → retry 3x; logic/config → `systematic-debugging` skill; still failing → block task, log in `memory/project-memory.md`.
- **Commit:** `git add alembic/ backend/app/models/project.py docs/specs/api-spec.md docs/specs/database-schema.md && git commit -m "feat(pipeline): 4-8 projects.entry_point column + POST /projects script_text" && git push`

### Step 2: script_text validation (BR-2)
- **Files:** `backend/app/schemas/project.py`
- **Do:** validate pasted `script_text` length is 100-3000 characters; outside that range → 400 with guidance text (BR-2).
- **Verify:** unit test: 50-char script → 400 with guidance message (AC4); 3500-char script → 400.
- **On failure:** same policy as Step 1.
- **Commit:** `4-8 script_text length validation (100-3000 chars)`.

### Step 3: Second graph entry point — script → extract_claims → factcheck (BR-1)
- **Files:** `backend/app/pipeline/graph.py` (conditional entry per LangGraph branch, no new node), `backend/app/pipeline/nodes/factcheck/evidence.py` (reuse from 4-4, extend evidence search to accept claim-as-query when no existing sources)
- **Do:** wire a LangGraph conditional entry: when `entry_point=script`, skip the research node and go straight to claim extraction (reusing 4-4's `factcheck.extract_claims`) then factcheck, where evidence is found via the search chain using each claim as the query (since there are no pre-existing `sources` rows from a research node). Reuse existing factcheck/storyboard nodes — do not create new node files (per Scope: "không node mới").
- **Verify:** integration test: project created with `entry_point=script` → graph executes extract_claims→factcheck without ever invoking the research node (assert via a call counter).
- **On failure:** same policy as Step 1.
- **Commit:** `4-8 script-entry graph branch (extract_claims -> factcheck, claim-as-query evidence)`.

### Step 4: Fact-check gate applies unchanged (BR-1 continued)
- **Files:** `backend/app/pipeline/graph.py`
- **Do:** confirm the same FAIL→NEED_REVIEW gate from 4-4 applies on this entry path with zero bypass — this is the core guarantee of the task ("không có đường nào ra video mà bỏ qua kiểm chứng").
- **Verify:** integration test: fixture script with 2 claims (1 correct, 1 wrong) → FAIL claim triggers `NEED_REVIEW`, resolved via the existing 5-6 UI/API path (AC2).
- **On failure:** same policy as Step 1.
- **Commit:** `4-8 confirm unbypassable factcheck gate on script entry`.

### Step 5: Script saved as v1 (created_by=user) + AI-generated title/description/tags
- **Files:** `backend/app/services/project_service.py`, `backend/app/pipeline/nodes/write/metadata.py` (small sub-step, reuses write-node prompt infra from 4-5/4-2)
- **Do:** persist the pasted script as `step_versions` v1 with `created_by=user` (not `created_by=ai`, since the user wrote it). Generate title/description/tags via a lightweight AI sub-step from the script content (editable afterward).
- **Verify:** integration test: after entry, script version has `created_by=user`; title/tags populated and non-empty (AC1).
- **On failure:** same policy as Step 1.
- **Commit:** `4-8 script-as-v1(user) + AI title/description/tags sub-step`.

### Step 6: Stepper display — "bỏ qua có kiểm chứng" states (BR-3)
- **Files:** frontend stepper component (existing PipelineStepper, extend per `rules/folder-structure.md`)
- **Do:** Research station shows "— bỏ qua"; Content station shows "✓ từ kịch bản của bạn"; user can still click into Content to edit (returns to the normal versioning flow, cascading `stale` to storyboard per 1-5 semantics).
- **Verify:** exercise in a real running browser per `rules/testing.md` UI rule; click Content station post-script-entry → edit succeeds, creates v2, storyboard marked stale (AC3).
- **On failure:** same policy as Step 1.
- **Commit:** `4-8 stepper skip/from-script states + edit-cascades-stale`.

### Step 7: "Có sẵn kịch bản" branch in Create Project modal (replaces "tạo trống")
- **Files:** frontend Create Project modal component
- **Do:** replace the removed "tạo trống" branch with the "Có sẵn kịch bản" branch per wireframe (textarea with label + character counter for a11y); on submit → RunningState "Đang kiểm chứng kịch bản…" → Phân cảnh.
- **Verify:** exercise in a real running browser; submit valid script → lands on RunningState then Phân cảnh with scene_set present (AC1 UI half).
- **On failure:** same policy as Step 1.
- **Commit:** `4-8 create-project modal "co san kich ban" branch UI`.

### Step 8: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `backend/tests/integration/pipeline/test_script_entry.py`, `tests/fixtures/script_entry_two_claims.json`
- **Do:** one test per Acceptance Criterion; build the 2-claim (1 correct, 1 wrong) script fixture as a reusable asset per DoD; add this integration test to the existing MockLLM CI pipeline bundle alongside the other entry-branch tests.
- **Verify:** `pytest backend/tests/integration/pipeline/test_script_entry.py` → all AC-mapped tests pass, and the test is included in the project's MockLLM CI suite run.
- **On failure:** same policy as above.
- **Commit:** `4-8 complete AC test coverage + 2-claim fixture in CI pipeline bundle`.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture script có 2 claim (1 đúng 1 sai); integration entry-branch với MockLLM thêm vào bộ CI pipeline.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-8.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-8.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
