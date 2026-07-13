# Task 1-5: Versioning engine

**Points:** 5đ · **Epic:** 1 — Nền tảng · **Depends:** 1-4 · **FR:** SRS §6
**State file:** [`state/1-5.json`](state/1-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/1-5-versioning-engine` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want mọi bước có phiên bản với quan hệ nguồn gốc và khôi phục an toàn, so that tôi thử nghiệm nội dung thoải mái mà không sợ mất gì.

## Why
"Mọi dữ liệu có version và khôi phục được" là nguyên tắc thiết kế #4 của SRS. Quy tắc cascade-stale là cốt lõi — xem [patterns/scene-versioning.md](../patterns/scene-versioning.md) và [anti-patterns/overwrite-version.md](../anti-patterns/overwrite-version.md).

## Scope
**In:** bảng `step_versions`; service: create (auto-increment, parent_version), current (max không-stale), restore (cascade stale xuôi dòng theo thứ tự step), compare (text diff outline/script; scene-diff theo scene_id cho storyboard/scene_set); API §3 api-spec.
**Out:** UI VersionSwitcher/So sánh (5-9); visual diff preview (v1.1); nén/dọn version cũ (v1.1).

## Business Rules
1. Không bao giờ UPDATE content — chỉ INSERT version mới (see [anti-patterns/overwrite-version.md](../anti-patterns/overwrite-version.md)).
2. Restore tạo bản ghi hành động (actor) — không xoá, không sửa version nào.
3. Stale chỉ đánh xuôi dòng (restore research không stale chính nó).
4. Current = max(version) WHERE NOT stale; nếu tất cả stale → max(version) kèm cờ `all_stale`.
5. Regenerate khi user đã sửa tay → version mới `parent_version` = bản user-sửa.
6. Compare chỉ trong cùng step; khác step → 400.

## Acceptance Criteria
1. **(happy)** research v1,v2 + script v1(parent rv2): restore rv1 → script stale; response `staled_steps=[script]`.
2. **(biên/BR-5)** User sửa script v2 → regenerate → v3 parent=v2; diff v2↔v3 đúng phần AI đổi.
3. **(biên/BR-4)** Mọi version script stale → current trả max + cờ all_stale.
4. **(biên)** Compare 2 scene_set khác số cảnh → added/removed/changed đúng theo scene_id.
5. **(lỗi)** Restore version không tồn tại → 404; restore khi project RUNNING → 409.

## Data & API
Bảng: `step_versions`. Contract change: **có** — response restore thêm `staled_steps: []`; compare scene_set `{added[], removed[], changed[{scene_id, fields[]}]}` → cập nhật api-spec §3.

## Decisions already locked
- Giữ version vô hạn trong v1 (không auto-prune) — PO 2026-07-10.

## Execution Steps

Work these in order. Update `state/1-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: step_versions table + migration
- **Files:** `backend/app/models/step_version.py`, `backend/alembic/versions/xxxx_step_versions.py`
- **Do:** implement `StepVersion` per `docs/specs/database-schema.md` §2.3 (step, version, parent_version, content JSONB, stale flag, created_by).
- **Verify:** `cd backend && alembic upgrade head` → exit 0.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/models backend/alembic && git commit -m "feat(versioning): 1-5 step_versions table"` → `git push`

### Step 2: create() / current() service methods
- **Files:** `backend/app/services/versioning_service.py`
- **Do:** implement `create(project_id, step, content, parent_version=None, actor)` — INSERT-only, auto-increments `version` per `(project_id, step)`, never `UPDATE`s content (BR-1, see [anti-patterns/overwrite-version.md](../anti-patterns/overwrite-version.md)); implement `current(project_id, step)` — `max(version) WHERE NOT stale`, or `max(version)` with `all_stale=true` if every version of that step is stale (BR-4).
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_versioning_create_current.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/versioning_service.py && git commit -m "feat(versioning): 1-5 create() + current() (insert-only, all_stale flag)"` → `git push`

### Step 3: restore() with cascade-stale
- **Files:** `backend/app/services/versioning_service.py`
- **Do:** implement `restore(project_id, step, version, actor)` per [patterns/scene-versioning.md](../patterns/scene-versioning.md) — writes an action record (BR-2), never mutates any version row; marks every **downstream** step's current version stale in step order, never marking the restored step itself stale (BR-3); returns `staled_steps: []`; raises 404 if the version doesn't exist, 409 if the project is `RUNNING`.
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_versioning_restore.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/versioning_service.py && git commit -m "feat(versioning): 1-5 restore() cascade-stale (contract change: staled_steps)"` → `git push`

### Step 4: Regenerate parent-tracking (BR-5) + compare()
- **Files:** `backend/app/services/versioning_service.py`
- **Do:** ensure a post-manual-edit regenerate creates a new version whose `parent_version` is the user-edited version (BR-5), so the manual edit is never lost; implement `compare(project_id, step, v1, v2)` — text diff for outline/script steps, scene-diff by `scene_id` for storyboard/scene_set producing `{added[], removed[], changed[{scene_id, fields[]}]}`; raise 400 if `v1`/`v2` belong to different steps (BR-6).
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_versioning_compare.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/versioning_service.py && git commit -m "feat(versioning): 1-5 compare() diff (contract change: scene_set diff shape)"` → `git push`

### Step 5: API §3 endpoints + api-spec update
- **Files:** `backend/app/api/versions.py`, `docs/specs/api-spec.md` §3
- **Do:** wire create/current/restore/compare to routes exactly per api-spec §3; update `docs/specs/api-spec.md` §3 in this same change for both contract changes (`staled_steps`, scene_set diff shape) per `rules/documentation.md`.
- **Verify:** `curl` smoke test of each endpoint against a seeded project.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/versions.py docs/specs/api-spec.md && git commit -m "feat(versioning): 1-5 API §3 endpoints + api-spec updated"` → `git push`

### Step 6: Wire up tests — property test cascade + all Acceptance Criteria
- **Files:** `backend/tests/unit/test_versioning_create_current.py`, `backend/tests/unit/test_versioning_restore.py`, `backend/tests/unit/test_versioning_compare.py`, `backend/tests/property/test_versioning_cascade.py`
- **Do:** property test — a random sequence of create/restore operations preserves the invariants "current is always determinable" and "no version is ever lost" (per Test Notes), using a fixture chain of 3 steps × 3 versions; explicit tests for AC-1 through AC-5.
- **Verify:** `cd backend && uv run pytest tests/ -v` → all pass, including the property test.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests && git commit -m "test(versioning): 1-5 tests covering AC 1-5 + cascade property test"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + property test cascade (bất biến "current luôn xác định được", "không mất version nào").

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/1-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/1-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
