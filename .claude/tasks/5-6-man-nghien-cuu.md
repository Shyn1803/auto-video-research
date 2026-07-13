# Task 5-6: Màn Nghiên cứu — nguồn + kiểm chứng

**Points:** 5đ · **Epic:** 5 — Workspace UI · **Depends:** 4-3, 4-4, 5-8 · **FR:** FR-02, FR-04
**State file:** [`state/5-6.json`](state/5-6.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-6-man-nghien-cuu` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## Status
Already `ready-for-dev` in [docs/backlog/stories/sprint-status.yaml](../../docs/backlog/stories/sprint-status.yaml) — full detailed story file exists at [docs/backlog/stories/story-5.6-research-review.md](../../docs/backlog/stories/story-5.6-research-review.md) (7 BR, 6 AC, states, data-api, decisions locked — the template exemplar every other story followed). **Read that file directly, apply as-is** — this stub only exists so this folder's index stays complete; do not duplicate its content here or let this file drift from it. The Execution Steps below operationalize that story's BR/AC set into a resumable checklist; if the story file and this list ever disagree, the story file wins — fix this list to match.

## Execution Steps

Work these in order. Update `state/5-6.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Nguồn tab — SourceCard list (pin/loại/xoá, badges)
- **Files:** `frontend/src/app/projects/[id]/research/page.tsx`, `frontend/src/components/workspace/SourceCard.tsx`, `frontend/tests/unit/components/SourceCard.test.tsx`
- **Do:** List of `SourceCard` (design-system §3.7) with pin/disable/delete actions, trust badge + score/reason, and partial-content badge. Pinned sources cannot be deleted (must unpin first — BR-5); pinned sources are always passed into later AI steps (verify via the request payload built for the next pipeline step, don't just check UI state).
- **Verify:** `pnpm --filter frontend vitest run SourceCard` → covers pin-blocks-delete and badge-rendering cases.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add frontend/src/app/projects/[id]/research frontend/src/components/workspace/SourceCard.tsx frontend/tests/unit/components/SourceCard.test.tsx && git commit -m "feat(workspace): 5-6 Nguon tab SourceCard list" && git push`

### Step 2: Add URL by hand (BR-6)
- **Files:** `frontend/src/components/workspace/AddSourceUrlForm.tsx`
- **Do:** Adding a URL matching an existing source's `url_hash` focuses that existing card instead of creating a duplicate; a crawl failure shows the source in an error state with a [Thử lại] retry button and does not block the rest of the screen.
- **Verify:** `pnpm --filter frontend vitest run AddSourceUrlForm` → covers dedupe-focus-existing and crawl-fail-retry-does-not-block cases (AC-3).
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/AddSourceUrlForm.tsx && git commit -m "feat(workspace): 5-6 add URL by hand, dedupe + retry" && git push`

### Step 3: Kiểm chứng tab — ClaimRow grouped by verdict
- **Files:** `frontend/src/components/workspace/ClaimRow.tsx`, `frontend/tests/unit/components/ClaimRow.test.tsx`
- **Do:** Claims grouped FAIL first, then WARN, then PASS (per story AC-1). Each `ClaimRow` is an accordion (`aria-expanded`) that expands to evidence; right-side panel of related sources with two-way highlight between claim ↔ source using **not just color** — border + 🔗 icon (a11y, per story UI/UX notes).
- **Verify:** `pnpm --filter frontend vitest run ClaimRow` → verdict grouping order and accordion a11y attributes verified.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/ClaimRow.tsx frontend/tests/unit/components/ClaimRow.test.tsx && git commit -m "feat(workspace): 5-6 ClaimRow grouped by verdict + evidence panel" && git push`

### Step 4: Override flow (BR-2, BR-3) + contract change
- **Files:** `frontend/src/components/workspace/ClaimOverrideDialog.tsx`, `backend/app/api/claims.py` (`POST claims/{cid}/override`), `docs/specs/api-spec.md` §5
- **Do:** Override = radio-select the correct evidence value (reason required, ≥10 chars) or exclude the claim from the video; both paths write an audit entry (actor, reason, timestamp) and never delete the original evidence. This is a **đổi contract** change: the override response must return the new `overall_verdict` plus the list of claims downgraded as a side effect (BR-3/BR-4) — update `docs/specs/api-spec.md` §5 in the same PR, note it in the PR's **Contract changes** section. Client applies the response directly (no reload needed) to re-render verdict state (BR-3).
- **Verify:** `pytest backend/tests/unit/api/test_claims_override.py -q` (respx-mocked where relevant) and `pnpm --filter frontend vitest run ClaimOverrideDialog` → reason-length validation, audit-write-without-deleting-evidence, response-drives-client-state cases all pass.
- **On failure:** same policy as Step 1; missing the api-spec update on this contract change is a review-reject per `rules/code-review.md` — don't skip it.
- **Commit:** `git add frontend/src/components/workspace/ClaimOverrideDialog.tsx backend/app/api/claims.py docs/specs/api-spec.md && git commit -m "feat(claims): 5-6 override flow + verdict recompute contract" && git push`

### Step 5: Cascading downgrade on source removal (BR-4)
- **Files:** `backend/app/services/factcheck.py` (or existing service module owning verdict recompute), `frontend/src/components/workspace/SourceCard.tsx` (toast wiring)
- **Do:** Disabling/deleting a source that is the sole evidence for a PASS claim immediately downgrades that claim to WARN and shows a toast naming the affected claim (BR-4); re-enabling the source restores PASS (AC-2).
- **Verify:** `pytest backend/tests/unit/services/test_factcheck_cascade.py -q` and `pnpm --filter frontend vitest run SourceCard -- --grep cascade` → downgrade-and-restore round-trip passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services frontend/src/components/workspace/SourceCard.tsx && git commit -m "feat(claims): 5-6 cascading PASS-to-WARN on source removal" && git push`

### Step 6: ApproveBar gate (BR-1) + stale banner (BR-7)
- **Files:** `frontend/src/components/workspace/ApproveBar.tsx` (reuse from 5-1), `frontend/src/components/workspace/StaleBanner.tsx` (shared pattern component)
- **Do:** "Duyệt & tiếp tục ▸" disabled with tooltip while any `FAIL` claim is unresolved (BR-1); WARN claims never block, but show an aggregate warning like "2 thông tin sẽ được nói kèm 'theo nguồn chưa xác nhận'". If the user re-enters this screen while later steps already exist, show the shared stale banner pattern; approving again confirms "3 bước sau sẽ đánh dấu lỗi thời" (BR-7).
- **Verify:** `pnpm --filter frontend vitest run ApproveBar -- --grep research` → disabled-with-tooltip and WARN-aggregate-message cases pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/ApproveBar.tsx frontend/src/components/workspace/StaleBanner.tsx && git commit -m "feat(workspace): 5-6 approve gate BR-1 + stale banner BR-7" && git push`

### Step 7: RunningState integration + all 5 UI states
- **Files:** `frontend/src/app/projects/[id]/research/page.tsx`
- **Do:** Wire the RunningState component (5-8 — must be `done` first per Depends) while research/factcheck runs, with message "Đang đọc nguồn X (4/12)" from real SSE progress (no invented percentages, per 5-8 BR-1). Implement all 5 states: default (wireframe), loading (RunningState), empty (0 sources → CTA "Thử từ khoá khác" / "Thêm URL tay"), error (chain-exhausted pattern §3.4), disabled (readonly when project not in NEED_REVIEW/REVISING).
- **Verify:** `pnpm --filter frontend vitest run research-page-states` → all 5 states render correctly per fixture.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/app/projects/[id]/research && git commit -m "feat(workspace): 5-6 RunningState integration + 5 UI states" && git push`

### Step 8: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `tests/unit/components/...`, `backend/tests/integration/test_claims_override_contract.py`, `tests/e2e/research-review.spec.ts`
- **Do:** One test per AC-1..AC-6 from the story file: vitest for BR-1/3/4 display logic, Playwright for AC-1 and AC-6 (part of the E2E journey, keyboard-only claim resolution + `Ctrl+Enter` approve), pytest contract test for the new override response shape. Manual pass: two-way claim↔source highlight, and a screen-reader read-through once (Test Notes). Then **exercise the feature in a real running browser (dev server)**: load a fixture project with 1 FAIL/1 WARN/5 PASS, resolve the FAIL claim via override, confirm the approve button enables and the WARN banner shows, then disable a source that's a PASS claim's sole evidence and confirm the toast + downgrade.
- **Verify:** `pnpm --filter frontend test:e2e -- research-review` and `pytest backend/tests/integration/test_claims_override_contract.py -q` → all AC-mapped tests pass; manual dev-server walkthrough matches AC-1/AC-2 exactly.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-6 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) as elaborated in the full story file.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-6.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-6.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
