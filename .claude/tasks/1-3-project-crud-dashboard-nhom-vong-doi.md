# Task 1-3: Project CRUD + Dashboard nhóm vòng đời

**Points:** 5đ (PO 2026-07-11: +1đ thumbnail/nhóm) · **Epic:** 1 — Nền tảng · **Depends:** 1-2 · **FR:** FR-01
**State file:** [`state/1-3.json`](state/1-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/1-3-project-crud-dashboard` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want tạo/sửa/clone/lưu trữ dự án và thấy ngay việc cần làm tiếp trên mỗi dự án, so that quản lý nhiều video cùng lúc không sót việc.

## Why
Dashboard là màn vào ra nhiều nhất mỗi ngày. "Hành động tiếp theo click được" (BR-3) biến dashboard từ danh sách thành hàng đợi việc.

## Scope
**In:** CRUD projects (api-spec §2) + ownership 🅞; modal Tạo dự án (topic bắt buộc; format mặc định 9:16, chọn thêm 16:9; giọng mặc định nữ + nghe thử); Dashboard khối "Dự án của tôi" (card: tên + StatusBadge + hành động tiếp theo), filter/paging/search; clone; archive/unarchive; empty state first-run.
**Out:** khối "Chờ duyệt hôm nay" (7-5); mini-stepper trên card; xoá vĩnh viễn dữ liệu (chỉ archive trong v1).

## Business Rules
1. DELETE chỉ khi DRAFT chưa có step_version; ngược lại 409 + UI gợi ý Lưu trữ.
2. Clone copy version mới nhất mọi step + asset refs; không copy renders/publishes; tên mặc định "{tên} (bản sao)".
3. "Hành động tiếp theo" suy từ status: NEED_REVIEW→"Mở duyệt ▸", RUNNING→"● {bước} x%", READY→"Xem & đăng", FAILED→"Xem lỗi & chạy tiếp".
4. Archive ẩn khỏi list mặc định; "Xem tất cả" gồm lưu trữ + khôi phục; project archive read-only.
5. Nghe thử giọng trong modal tạo gọi tts-preview với câu mẫu cố định (cache).
6. **(PO 2026-07-11)** Dashboard nhóm theo vòng đời, thứ tự: Chờ duyệt (7-5) → Đang chạy → Đang làm dở → Đã đăng 7 ngày; nhóm rỗng ẩn; card có thumbnail (frame cảnh 1) + "bước x/5 · tên trạm", **không** mini-stepper.
7. Filter theo Mode (Tất cả / Của tôi / Tự động).

## Acceptance Criteria
1. **(happy)** Tạo topic "GPT-5.5" (9:16, giọng nữ) → card DRAFT; mở → workspace stepper chỉ Nghiên cứu mở.
2. **(biên/BR-2)** Clone project 8 cảnh → đủ version+scene, DRAFT, không renders; tên "(bản sao)".
3. **(lỗi/BR-1)** DELETE project có script → 409; toast gợi ý Lưu trữ.
4. **(quyền)** Creator A không thấy project B (403).
5. **(empty)** User mới → empty state đúng wireframe.
6. **(BR-3)** Seed 4 project 4 status → 4 nhãn hành động đúng, click đến đúng nơi.

## Data & API
Bảng: `projects`. Contract change: **có** — thêm `next_action {label, href}` vào response list → cập nhật api-spec §2.

## UI/UX
Wireframe Dashboard + Tạo dự án (modal). States: default/loading(skeleton)/empty(CTA)/error/disabled N/A. A11y: card link, modal focus-trap ESC, search label.

## Decisions already locked
- Giọng đọc là thuộc tính project (per-scene override vẫn có ở editor).
- ⏳ Giới hạn 50 project active/user.

## Execution Steps

Work these in order. Update `state/1-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: projects table + migration
- **Files:** `backend/app/models/project.py`, `backend/alembic/versions/xxxx_create_projects.py`
- **Do:** implement the `Project` model exactly per `docs/specs/database-schema.md` §2.2 (status, owner_id, format, voice, etc.) — don't invent columns not in that spec.
- **Verify:** `cd backend && alembic upgrade head` → exit 0.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/models backend/alembic && git commit -m "feat(projects): 1-3 projects table"` → `git push`

### Step 2: Project CRUD service + ownership enforcement
- **Files:** `backend/app/services/project_service.py`, `backend/app/api/projects.py`
- **Do:** implement create/get/list/update/delete/clone/archive/unarchive per api-spec §2; enforce ownership 🅞 so a creator only ever sees their own projects; `DELETE` allowed only when `status == DRAFT` and no `step_version` exists, else 409 with a "gợi ý Lưu trữ" hint (BR-1); `clone` copies the latest non-stale version of every step + asset refs, excludes renders/publishes, defaults the name to `"{tên} (bản sao)"` (BR-2).
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_project_service.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/project_service.py backend/app/api/projects.py && git commit -m "feat(projects): 1-3 CRUD service + ownership + clone/archive"` → `git push`

### Step 3: next_action computation (BR-3) — contract change
- **Files:** `backend/app/services/project_service.py`, `docs/specs/api-spec.md` §2
- **Do:** derive `next_action {label, href}` server-side from status per the BR-3 mapping (NEED_REVIEW→"Mở duyệt ▸", RUNNING→"● {bước} x%", READY→"Xem & đăng", FAILED→"Xem lỗi & chạy tiếp"); add the field to the list-response schema; update `docs/specs/api-spec.md` §2 in this same change (đổi contract, per `rules/documentation.md`).
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_next_action.py -v` parametrized over the 4 statuses (AC-6).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend docs/specs/api-spec.md && git commit -m "feat(projects): 1-3 next_action field (contract change, api-spec §2 updated)"` → `git push`

### Step 4: Dashboard lifecycle grouping (BR-6) + Mode filter (BR-7)
- **Files:** `backend/app/api/projects.py`, `backend/app/services/project_service.py`
- **Do:** group the list response by lifecycle in order Chờ duyệt → Đang chạy → Đang làm dở → Đã đăng 7 ngày, hiding empty groups; support `archived=true` query param and a `mode` filter (Tất cả/Của tôi/Tự động).
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_dashboard_grouping.py -v`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app && git commit -m "feat(projects): 1-3 dashboard lifecycle grouping + mode filter"` → `git push`

### Step 5: TTS preview via adapter (BR-5)
- **Files:** `backend/app/adapters/tts/base.py`, `backend/app/services/project_service.py` (or a dedicated `tts_preview_service.py`)
- **Do:** implement the `tts-preview` call used by the Create-project modal by going through an adapter interface per [patterns/provider-adapter.md](../patterns/provider-adapter.md) — never call a TTS SDK/HTTP API directly from `project_service`; synthesize a fixed sample sentence, cache the result (BR-5). If the real `TTSAdapter` base class / edge-tts provider (tasks 2-4/3-1) doesn't exist yet, implement the minimal `TTSAdapter` ABC here so the adapter boundary is respected, and record a `decisions[]` entry in the state file noting 2-4/3-1 should reconcile with it later — this is a reversible, locally-scoped call per `rules/autonomy-policy.md`, not a blocker.
- **Verify:** `cd backend && uv run pytest backend/tests/unit/test_tts_preview.py -v` (HTTP mocked via `respx` per `rules/testing.md`).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/tts backend/app/services && git commit -m "feat(projects): 1-3 tts-preview via adapter (cached)"` → `git push`

### Step 6: Dashboard + Create-project modal UI
- **Files:** `frontend/src/app/projects/page.tsx`, `frontend/src/components/projects/CreateProjectModal.tsx`, `frontend/src/components/projects/ProjectCard.tsx`
- **Do:** implement the Dashboard "Dự án của tôi" grouped list, card (name + StatusBadge + next_action, thumbnail from scene-1 frame with placeholder fallback, "bước x/5 · tên trạm", no mini-stepper per BR-6), filter/paging/search, first-run empty-state CTA; Create Project modal (topic required, format default 9:16 + 16:9 option, voice default nữ + nghe thử via the Step 5 endpoint); all 5 UI states (default/loading skeleton/empty CTA/error banner/disabled N/A) matching `docs/design/wireframe.html` Dashboard + Tạo dự án; a11y: card is a link (Enter opens), modal focus-trap + ESC closes, search has a label.
- **Verify:** `cd frontend && npm run build` → exit 0; manually diff against `docs/design/wireframe.html` Dashboard/Tạo dự án sections.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src && git commit -m "feat(frontend): 1-3 Dashboard + Create Project modal"` → `git push`

### Step 7: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/integration/test_projects_crud.py`, `backend/tests/integration/test_projects_permissions.py`, `frontend/tests/e2e/create-project.spec.ts`
- **Do:** one test per Acceptance Criterion — AC-1 create+open flow, AC-2 clone (8-cảnh fixture), AC-3 delete-conflict 409 + toast, AC-4 cross-tenant 403 (2-user fixture from 1-2), AC-5 empty-state first-run, AC-6 next_action seed-4-status; Playwright "tạo → thấy card → mở" per DoD.
- **Verify:** `cd backend && uv run pytest tests/ -v` && `cd frontend && npx playwright test create-project.spec.ts` → all pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests frontend/tests && git commit -m "test(projects): 1-3 tests covering AC 1-6"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + Playwright: tạo → thấy card → mở.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/1-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/1-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
