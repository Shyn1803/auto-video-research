# Task 5-10: ProjectDrawer — Thông tin & Cài đặt dự án

**Points:** 2đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1, 1-3, 3-5 (llm_usage) · **FR:** FR-01
**State file:** [`state/5-10.json`](state/5-10.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-10-projectdrawer` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want mở nhanh thông tin tổng quan và cài đặt của dự án từ bất kỳ màn nào, so that quay lại project cũ vẫn nắm ngay tình trạng và chỉnh cấu hình không phải rời workspace.

## Why
Gap kép từ review luồng: (1) FR-01 cho sửa project nhưng không màn nào chứa PATCH; (2) vào project 2 tuần tuổi mất phương hướng. Một drawer giải cả hai, không thêm trạm/route.

## Scope
**In:** drawer trượt phải (design-system §3.7), mở từ tên project ⓘ topbar; tab **Thông tin**: tóm tắt 2 câu (AI sinh 1 lần sau research, cache), verdict tổng + link, thời lượng/số cảnh/format/giọng/theme, chi phí AI ước tính (sum llm_usage), nguồn count, hoạt động gần đây (5 dòng); tab **Cài đặt**: đổi tên/format/giọng mặc định/theme (PATCH), Nhân bản, Lưu trữ (chuyển từ dashboard card menu vào đây).
**Out:** ghi chú/comment (v1.1); chia sẻ project (ngoài scope); chỉnh sâu chi phí (màn Vận hành lo).

## Business Rules
1. Đổi giọng mặc định → cảnh chưa produce dùng giọng mới; cảnh đã produce giữ nguyên — nêu rõ trong UI khi đổi.
2. Đổi format/theme → cảnh báo hệ quả render lại (tái dùng pattern 10-2 BR-2).
3. Lưu trữ từ drawer confirm như dashboard; project archive mở drawer chỉ-đọc + nút Khôi phục.
4. Chi phí hiển thị nhãn "ước tính" (nhất quán 3-5 BR-4).

## Acceptance Criteria
1. **(happy)** Mở drawer từ màn Phân cảnh → đủ thông tin đúng dữ liệu; đóng ESC quay đúng focus.
2. **(biên/BR-1)** Đổi giọng khi 5/8 cảnh đã produce → thông báo rõ phạm vi ảnh hưởng; produce lại chỉ 3 cảnh mới dùng giọng mới.
3. **(biên/BR-3)** Project archive → drawer read-only + Khôi phục hoạt động.
4. **(lỗi)** Endpoint cost lỗi → khối chi phí hiện "không tải được" + thử lại, phần khác nguyên vẹn.
5. **(quyền)** 🅞 — creator khác 403.

## Data & API
Endpoint mới `GET /projects/{id}/summary` (gộp metadata+verdict+cost+activity) → cập nhật api-spec §2; PATCH sẵn có. Tóm tắt AI thêm output nhẹ vào node research (tier cheap, cache). Contract change: **có**.

## Decisions already locked
- ⏳ Tóm tắt 2 câu sinh 1 lần sau research (không realtime).

## Execution Steps

Work these in order. Update `state/5-10.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Backend summary endpoint (contract change)
- **Files:** `backend/app/api/projects.py` (`GET /projects/{id}/summary`), `backend/app/services/project_summary.py`, `backend/tests/unit/api/test_project_summary.py`, `docs/specs/api-spec.md` §2
- **Do:** New endpoint aggregating metadata + verdict + cost (sum of `llm_usage` for the project, tagged "ước tính" per BR-4, consistent with 3-5 BR-4) + source count + last 5 activity entries. This is a **đổi contract** change — update `docs/specs/api-spec.md` §2 in the same PR, note it in the **Contract changes** section per `rules/pull-requests.md`. Role check: creators other than the project owner get 403 (AC-5, 🅞 permission marker).
- **Verify:** `pytest backend/tests/unit/api/test_project_summary.py -q` → covers aggregation correctness against seeded `llm_usage`, and the 403-for-other-creator case.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/api/projects.py backend/app/services/project_summary.py backend/tests/unit/api/test_project_summary.py docs/specs/api-spec.md && git commit -m "feat(projects): 5-10 summary endpoint" && git push`

### Step 2: AI-generated 2-sentence summary (cheap tier, cached, post-research)
- **Files:** `backend/app/pipeline/nodes/research.py` (or the node owning research completion, existing from 4-x), `backend/app/schemas/scene.py` or a dedicated summary field — check existing project schema first, do not duplicate
- **Do:** Add a lightweight output to the research node: a 2-sentence project summary, generated once after research completes and cached (locked decision — not realtime, not regenerated on every drawer open). LLM call must declare `tier: cheap` per `rules/performance.md`.
- **Verify:** `pytest backend/tests/unit/pipeline/test_research_summary.py -q` (respx-mocked LLM, no live network) → summary generated once, cached on subsequent calls.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/pipeline/nodes/research.py && git commit -m "feat(research): 5-10 cached 2-sentence project summary, cheap tier" && git push`

### Step 3: ProjectDrawer shell + Thông tin tab
- **Files:** `frontend/src/components/workspace/ProjectDrawer.tsx`, `frontend/src/components/workspace/ProjectDrawerTabs/InfoTab.tsx`
- **Do:** Slide-in-right drawer (design-system §3.7) opened from the project name ⓘ in the topbar (extends 5-1). Thông tin tab: 2-sentence summary, verdict + link, duration/scene-count/format/voice/theme, cost (from Step 1's summary endpoint, "ước tính" label), source count, last-5 activity. ESC closes and restores focus to the ⓘ trigger (AC-1, focus-trap). If the cost portion of the summary endpoint fails, that block alone shows "không tải được" + retry while the rest of the drawer renders normally (AC-4 — partial-failure isolation, don't let one field's error blank the whole drawer).
- **Verify:** `pnpm --filter frontend vitest run ProjectDrawer InfoTab` → covers full-render, ESC-restores-focus, cost-block-partial-failure-isolated cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/ProjectDrawer.tsx frontend/src/components/workspace/ProjectDrawerTabs/InfoTab.tsx && git commit -m "feat(workspace): 5-10 ProjectDrawer shell + Thong tin tab" && git push`

### Step 4: Cài đặt tab — PATCH rename/format/voice/theme (BR-1, BR-2)
- **Files:** `frontend/src/components/workspace/ProjectDrawerTabs/SettingsTab.tsx`
- **Do:** Form for rename, default format, default voice, theme — PATCH via the generated API client (never hand-write a duplicate type, per `rules/code-style.md`). Changing the default voice explains that already-produced scenes keep their existing voice and only not-yet-produced scenes pick up the new one (BR-1, AC-2). Changing format/theme warns about re-render consequences, reusing the same warning pattern as 10-2 BR-2 (BR-2) — don't invent a new wording for the same warning.
- **Verify:** `pnpm --filter frontend vitest run SettingsTab` → covers PATCH-success, voice-change-scope-message (5/8 produced → 3 new use new voice), format-change-rerender-warning cases (AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/ProjectDrawerTabs/SettingsTab.tsx && git commit -m "feat(workspace): 5-10 Cai dat tab, PATCH + BR-1/BR-2 warnings" && git push`

### Step 5: Nhân bản + Lưu trữ actions (BR-3, moved from dashboard card menu)
- **Files:** `frontend/src/components/workspace/ProjectDrawerTabs/SettingsTab.tsx` (actions section), remove/redirect the old dashboard card menu entry if one already exists from an earlier epic
- **Do:** Duplicate project action; Archive action with the same confirm dialog already used on the dashboard card (reuse the component, don't fork a second confirm dialog). When the project is already archived, the whole drawer opens read-only with a "Khôi phục" button instead of the Cài đặt form (BR-3, AC-3).
- **Verify:** `pnpm --filter frontend vitest run SettingsTab -- --grep archive` → covers archive-confirm-reused-component, archived-project-readonly-with-restore cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/ProjectDrawerTabs && git commit -m "feat(workspace): 5-10 duplicate + archive actions, BR-3 readonly archived state" && git push`

### Step 6: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/components/ProjectDrawer*.test.tsx`, `backend/tests/integration/test_project_summary_endpoint.py`
- **Do:** One test per AC above; integration test comparing the summary endpoint's cost total against seeded `llm_usage` fixture rows (must match exactly, not approximately). Then **exercise the feature in a real running browser (dev server)**: open the drawer from the Phân cảnh screen, confirm all Thông tin fields populate, switch to Cài đặt, change the default voice on a project with some scenes already produced, confirm the scope message, then archive the project and confirm the drawer reopens read-only with Khôi phục.
- **Verify:** `pytest backend/tests/integration/test_project_summary_endpoint.py -q` and `pnpm --filter frontend vitest run ProjectDrawer` → all AC-mapped tests pass; manual dev-server walkthrough confirms focus-trap and ESC behavior.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-10 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + vitest tab/focus-trap; integration summary endpoint (so khớp seed llm_usage).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-10.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-10.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
