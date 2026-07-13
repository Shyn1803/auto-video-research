# Task 7-3: Gate config + thống kê chính xác

**Points:** 3đ · **Epic:** 7 — Automation · **Depends:** 7-2, 8-3 · **FR:** Mode 1 gate
**State file:** [`state/7-3.json`](state/7-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/7-3-gate-config-thong-ke` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.
>
> **Non-negotiable gate note (autonomy-policy.md "What this does NOT change"):** `MODE1_AUTOPUBLISH` (`off → pass_only → on`) is intentional business logic guarding the product's biggest risk (auto-publishing wrong content), not agent-workflow friction. Execution Steps below must enforce the gate faithfully at the publish step — `on` still requires `PASS` for auto-publish and always stops `WARN` for human review (BR-3); no step may relax this to "auto-publish more" without an explicit PO decision recorded in `docs/`. Raising the gate level itself already requires an admin confirm + audit (BR-4/AC-audit) — that human checkpoint must not be bypassed by any automation added here.

## User story
As an Admin, I want nâng mức tự động của Mode 1 dựa trên thống kê độ chính xác thực tế, so that quyết định "cho máy tự đăng" dựa trên dữ liệu chứ không cảm tính.

## Why
Cơ chế "earn trust" của SRS §2: `off → pass_only → on` theo tỉ lệ PASS-đúng 30 ngày ≥95%. Câu trả lời cho rủi ro lớn nhất của sản phẩm (auto-publish nội dung sai).

## Scope
**In:** enforcement `MODE1_AUTOPUBLISH` 3 mức tại bước publish; đo "PASS có đúng không": approve nguyên trạng = đúng, sửa fact = sai (định nghĩa BR-1); thống kê 30 ngày + banner khuyến nghị trên tab Providers; đổi gate = admin action có confirm + audit.
**Out:** auto-publish thực tế cần 8-3 (trước đó nghiệm thu logic với platform download); ML threshold tự điều chỉnh.

## Business Rules
1. "sửa fact" đo được = sau READY user sửa số liệu/tên/ngày trong script HOẶC override claim; sửa hình/chữ trang trí/timing không tính.
2. Nâng gate chặn khi mẫu <20 video ("chưa đủ dữ liệu").
3. Gate `on` → chỉ PASS auto-publish; WARN luôn dừng (đúng SRS).
4. Hạ gate luôn được phép không điều kiện (chiều an toàn).

## Acceptance Criteria
1. **(happy)** pass_only: video PASS → auto-publish; WARN → READY chờ.
2. **(biên/BR-1)** Sau READY sửa số trong script → ghi nhận "sai"; sửa màu chữ → không ghi nhận.
3. **(biên/BR-2)** 12 video → nút nâng disabled "cần ≥20"; đủ 20 + ≥95% → enabled.
4. **(audit)** Đổi gate ghi ai/lúc/từ→đến; confirm nêu hệ quả.
5. **(BR-4)** Hạ on→off luôn được, không điều kiện.

## Data & API
Bảng: thêm `accuracy_events(project_id, was_correct, detected_by, at)`; endpoint stats + đổi gate 🅐 → cập nhật api-spec §9 (+DB schema). Contract change: **có**.

## Decisions already locked
- Ngưỡng 95% / 30 ngày / tối thiểu 20 mẫu (SRS §2 + bổ sung mẫu tối thiểu).

## Execution Steps

Work these in order. Update `state/7-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: `accuracy_events` table + migration (contract change)
- **Files:** `backend/alembic/versions/{rev}_accuracy_events.py`, `backend/app/models/accuracy_event.py`, `docs/specs/database-schema.md` (update in same PR — contract change per "Data & API")
- **Do:** `accuracy_events(project_id, was_correct, detected_by, at)` per Data & API. Update `docs/specs/database-schema.md` and note the change in the PR description's **Contract changes** section, per `rules/documentation.md`.
- **Verify:** `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head` → clean; `docs/specs/database-schema.md` diff present in the same commit.
- **On failure:** transient (DB) → retry 3×; schema/logic error → `systematic-debugging` skill; still failing → `blocked`.
- **Commit:** `git add backend/alembic backend/app/models/accuracy_event.py docs/specs/database-schema.md && git commit -m "feat(gate): 7-3 add accuracy_events table (contract change)"` → `git push`

### Step 2: "Was PASS correct?" detection (BR-1 — the contentious branch logic)
- **Files:** `backend/app/services/accuracy_tracking.py`
- **Do:** implement exactly the BR-1 definition: after `READY`, an approve-as-is → `was_correct=true`; a user edit to a **number/name/date in the script** OR a claim override → `was_correct=false`; edits to decorative text/images/timing do **not** count and must not write an event at all. Detection must hook into the existing edit-tracking mechanism (versioning engine, task 1-5) rather than re-parsing diffs ad hoc — reuse, don't reinvent.
- **Verify:** `cd backend && pytest backend/tests/unit/services/test_accuracy_tracking.py -v` → one test per branch: approve-as-is (correct), script number edit (incorrect), claim override (incorrect), color/decorative edit (no event written), timing-only edit (no event written). This is the "chỗ dễ cãi nhau nhất" per Test Notes — each branch needs its own explicit test, not a combined one. Covers AC2.
- **On failure:** ambiguous classification bug → `systematic-debugging` skill, and if the BR-1 definition itself is ambiguous for a real edge case encountered, that's a scope-ambiguity escalation per `rules/autonomy-policy.md` (flag with a recommended default, keep working other steps) rather than guessing silently.
- **Commit:** `git commit -m "feat(gate): 7-3 was_correct detection per BR-1 definition"` → `git push`

### Step 3: 30-day stats endpoint + gate change endpoint (contract change)
- **Files:** `backend/app/api/gate.py`, `backend/app/schemas/gate.py`, `docs/specs/api-spec.md` §9 (update in same PR)
- **Do:** `GET /gate/stats` → 30-day PASS-correct rate + sample count. `POST /gate/config` → change `MODE1_AUTOPUBLISH` level; raising is blocked when sample size <20 ("chưa đủ dữ liệu", BR-2) and requires confirm; lowering is always allowed unconditionally (BR-4). Every change writes an audit row: actor, timestamp, from→to (audit AC). Enforce the gate at the actual publish step (see the non-negotiable note above): `on` still requires `PASS`, `WARN` always stops for review (BR-3).
- **Verify:** `cd backend && pytest backend/tests/unit/api/test_gate.py -v` → 12-sample fixture → raise blocked with "cần ≥20" message; 20-sample + ≥95% fixture → raise allowed; lower on→off always succeeds regardless of sample size; audit row shape matches spec. Covers AC3, AC4 (audit), AC5.
- **On failure:** same retry policy.
- **Commit:** `git add backend/app/api/gate.py backend/app/schemas/gate.py docs/specs/api-spec.md && git commit -m "feat(gate): 7-3 gate stats + config endpoints (contract change)"` → `git push`

### Step 4: Publish-step gate enforcement
- **Files:** `backend/app/pipeline/nodes/publish.py` or equivalent publish-trigger point (reuse existing publish node/service, do not fork a second publish path)
- **Do:** at the actual point where a video would auto-publish, read `MODE1_AUTOPUBLISH` and the verdict; `pass_only` → only `PASS` auto-publishes, `WARN` stays `READY`; `on` → still only `PASS` auto-publishes per SRS (WARN always dstops — this project's SRS §2 does not grant `on` an unconditional WARN auto-publish; re-verify against `docs/SRS.md` §2 before implementing and flag immediately if the text there is read differently, per CLAUDE.md §4's "ambiguous vs docs" escalation).
- **Verify:** `cd backend && pytest backend/tests/integration/test_gate_publish.py -v` → `pass_only` + PASS → auto-published; `pass_only`/`on` + WARN → stays `READY`. Covers AC1.
- **On failure:** if `docs/SRS.md` §2 text is ambiguous about `on` + WARN behavior, stop and report the inconsistency (CLAUDE.md §4) rather than resolving it silently — this is exactly the kind of ambiguity that must not be guessed per the non-negotiable gate note above.
- **Commit:** `git commit -m "feat(gate): 7-3 enforce MODE1_AUTOPUBLISH at publish step"` → `git push`

### Step 5: Providers tab banner + admin gate UI
- **Files:** `frontend/src/app/admin/providers/page.tsx` (extend), `frontend/src/components/admin/GateStatsBanner.tsx`
- **Do:** stats banner (e.g. "96.4% + Nâng chế độ" per wireframe) with states default/empty (<20 samples → "12/20 video" progress)/disabled (BR-2); raise/lower action opens a confirm dialog stating consequences before calling the Step 3 endpoint; banner has `role=status` per a11y note.
- **Verify:** exercise in a real running browser (per `rules/testing.md`) — dev server, navigate to `/admin/providers`, confirm banner states and confirm-dialog flow against the Step 3 API.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(gate): 7-3 providers tab gate stats banner + confirm UI"` → `git push`

### Step 6: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/...`, `backend/tests/integration/...`
- **Do:** simulate 30 days of `accuracy_events` via a seed fixture per Test Notes; one test per AC (already built incrementally above) — this step is the consolidation pass confirming nothing regressed across the whole flow (seed → stats → gate change → publish enforcement).
- **Verify:** `cd backend && pytest tests/ -k "gate or accuracy" -v` → all AC-mapped tests pass.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "test(gate): 7-3 full AC coverage incl. 30-day seed simulation"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + simulate 30 ngày dữ liệu bằng seed; định nghĩa BR-1 cần test kỹ từng nhánh (chỗ dễ cãi nhau nhất).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/7-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/7-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
