# Task 4-4: Node Ranking + FactCheck

**Points:** 5đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-3 · **FR:** FR-03, FR-04
**State file:** [`state/4-4.json`](state/4-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-4-node-ranking-factcheck` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want mọi thông tin quan trọng được kiểm chéo giữa các nguồn độc lập, so that video không bao giờ nói sai tên, số, ngày — thứ giết uy tín kênh nhanh nhất.

## Why
FR-03/04 — lý do tồn tại của sản phẩm so với "ChatGPT viết kịch bản". Gate PASS/WARN/FAIL đã đặc tả định lượng trong SRS.

## Scope
**In:** ranking (prompt `ranking.score`, trọng số config) → score/reason vào source; factcheck: extract claims (`factcheck.extract_claims`) → gom evidence (embedding search) → verdict/claim (`factcheck.verify_claim`); verdict tổng + gate (FAIL→NEED_REVIEW+notify); API claims + override (§5); fixture kịch bản mâu thuẫn.
**Out:** UI (5-6); notify channel thật (7-4 — tạm log); re-check tự động theo chu kỳ.

## Business Rules
1. PASS cần ≥2 nguồn **độc lập** — khác root domain; 2 bài cùng blog = 1 nguồn.
2. Evidence từ source `partial_content` không đủ cho PASS (tối đa WARN).
3. Override ghi audit, không xoá evidence; verdict tổng tính lại đồng bộ trong cùng request.
4. Claim không tìm được evidence → WARN "không tìm thấy nguồn xác nhận".
5. Disable/xoá source → mọi claim có evidence từ nó tính lại verdict (đồng bộ, cùng response).
6. Claim types theo spec (model_name/benchmark/release_date/paper/github/version/other); extraction bỏ ý kiến chủ quan.

## Acceptance Criteria
1. **(happy)** Fixture 2 nguồn lệch ngày → claim FAIL + evidence 2 phía; project NEED_REVIEW; notify (log) bắn.
2. **(biên/BR-1)** 2 bài cùng openai.com xác nhận → WARN, không PASS.
3. **(biên/BR-5)** Disable nguồn evidence duy nhất của claim PASS → claim WARN, response chứa affected_claims.
4. **(override/BR-3)** Chọn giá trị đúng + lý do → verdict đổi + overall mới; audit query được.
5. **(BR-4)** Claim mồ côi → WARN đúng message.
6. **(quyền)** Creator không owner → 403.

## Data & API
Bảng: claims. Contract change: **có** — response override/patch-source thêm `overall_verdict` + `affected_claims[]` → cập nhật api-spec §5.

## Decisions already locked
- WARN không chặn duyệt; video tự thêm "theo nguồn chưa xác nhận" (PO 2026-07-10).
- ⏳ Trọng số ranking mặc định: mới 0.3 / liên quan 0.3 / tin cậy 0.25 / xác nhận chéo 0.15.

## Execution Steps

Work these in order. Update `state/4-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: claims schema + contract-change to api-spec §5
- **Files:** `backend/app/models/claim.py`, migration under `alembic/versions/`, `docs/specs/api-spec.md` §5 (or wherever api-spec lives)
- **Do:** create `claims` table per Data & API. This task is flagged a "đổi contract" change (response for override/patch-source adds `overall_verdict` + `affected_claims[]`) — update the matching `docs/` spec **in the same PR**, per `rules/documentation.md`.
- **Verify:** `alembic upgrade head` → `claims` table exists; `docs/specs/api-spec.md` §5 diff shows the new response fields.
- **On failure:** transient → retry 3x; logic/config → `systematic-debugging` skill; still failing → block task, log in `memory/project-memory.md`.
- **Commit:** `git add backend/app/models/claim.py alembic/ docs/specs/api-spec.md && git commit -m "feat(factcheck): 4-4 claims schema + api-spec contract update" && git push`

### Step 2: Ranking node (ranking.score prompt, configurable weights)
- **Files:** `backend/app/pipeline/nodes/ranking/node.py`
- **Do:** call `get_active_prompt("ranking.score")` (from 4-2) with configurable weights (recency/relevance/trust/cross-confirm, defaults per "Decisions already locked"); write `score`/`reason` back onto each source.
- **Verify:** unit test with fixture sources → scores + reasons populated, weights read from config not hardcoded.
- **On failure:** same policy as Step 1.
- **Commit:** `4-4 ranking node with configurable weights`.

### Step 3: Claim extraction (factcheck.extract_claims prompt)
- **Files:** `backend/app/pipeline/nodes/factcheck/extract.py`
- **Do:** call `get_active_prompt("factcheck.extract_claims")`; classify each claim by type (model_name/benchmark/release_date/paper/github/version/other per BR-6); extraction must exclude subjective opinions (BR-6).
- **Verify:** unit test: fixture text with 1 subjective sentence + N factual claims → only factual claims extracted, correctly typed.
- **On failure:** same policy as Step 1.
- **Commit:** `4-4 claim extraction node + claim type classification`.

### Step 4: Evidence gathering (embedding search) + verify_claim verdicts (BR-1, BR-2, BR-4)
- **Files:** `backend/app/pipeline/nodes/factcheck/evidence.py`, `backend/app/pipeline/nodes/factcheck/verify.py`
- **Do:** gather evidence via embedding similarity search over sources; call `get_active_prompt("factcheck.verify_claim")` per claim. Enforce BR-1 (PASS needs ≥2 **independent** sources — different root domain; same-blog articles count as 1), BR-2 (`partial_content` evidence caps verdict at WARN, never PASS), BR-4 (claim with zero evidence → WARN "không tìm thấy nguồn xác nhận").
- **Verify:** unit tests: (a) 2 sources same root domain → WARN not PASS (AC2); (b) evidence source is `partial_content` → capped at WARN; (c) orphan claim → WARN with exact message (AC5).
- **On failure:** same policy as Step 1.
- **Commit:** `4-4 evidence gathering + verify_claim + BR-1/BR-2/BR-4 gates`.

### Step 5: Overall verdict + gate (FAIL → NEED_REVIEW + notify)
- **Files:** `backend/app/pipeline/nodes/factcheck/node.py` (registered in graph)
- **Do:** compute overall verdict from per-claim verdicts; on any FAIL, transition project to `NEED_REVIEW` and fire a notify event (logged only in this task per Scope Out — 7-4 wires the real channel later).
- **Verify:** integration test: fixture with 2 sources disagreeing on a date → claim FAIL, project `NEED_REVIEW`, notify log entry present (AC1).
- **On failure:** same policy as Step 1.
- **Commit:** `4-4 factcheck node overall verdict + NEED_REVIEW gate + notify log`.

### Step 6: Override endpoint — audit + synchronous verdict recompute (BR-3)
- **Files:** `backend/app/api/routes/claims.py`, `backend/app/services/claim_service.py`
- **Do:** override endpoint writes an audit row (no evidence deletion), and recomputes `overall_verdict` + `affected_claims[]` synchronously in the same response (BR-3). RBAC: non-owner Creator → 403 (AC6).
- **Verify:** integration test: override with correct value + reason → verdict flips, response contains new `overall_verdict`; audit queryable (AC4).
- **On failure:** same policy as Step 1.
- **Commit:** `4-4 claim override endpoint + audit + sync recompute`.

### Step 7: Disable/delete source cascade (BR-5)
- **Files:** `backend/app/api/routes/sources.py`, `backend/app/services/claim_service.py`
- **Do:** disabling/deleting a source triggers synchronous recompute of every claim that had evidence from it (same response, per BR-5 — consumed by 5-6 BR-4 later).
- **Verify:** integration test: disable the sole evidence source of a PASS claim → claim becomes WARN, response includes `affected_claims` (AC3).
- **On failure:** same policy as Step 1.
- **Commit:** `4-4 source disable/delete cascade recompute`.

### Step 8: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `tests/unit/pipeline/nodes/factcheck/...`, `backend/tests/integration/pipeline/test_factcheck_node.py`, `tests/fixtures/factcheck_conflict.json`
- **Do:** one test per Acceptance Criterion; build the contradictory-scenario fixture (2 sources disagreeing on a date) as a reusable long-lived asset per DoD (also used by 5-6, 7-2, E2E).
- **Verify:** `pytest backend/tests/unit/pipeline/nodes/factcheck backend/tests/integration/pipeline/test_factcheck_node.py` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** `4-4 complete AC test coverage + conflicting-sources fixture`.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture mâu thuẫn là tài sản test dùng lại ở 5-6, 7-2, E2E.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
