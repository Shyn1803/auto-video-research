# Task 10-6: Release — docs, checklist, go-live

**Points:** 2đ · **Epic:** 10 — Release · **Depends:** 10-4, 10-5 · **FR:** Release plan §1
**State file:** [`state/10-6.json`](state/10-6.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/10-6-release-docs-checklist-go-live` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task. This task also follows [agents/release-manager.md](../agents/release-manager.md)'s decision rule: a release blocks if any Release Checklist item is unverified — no exceptions without explicit user (PO) sign-off.

## User story
As a team, I want quy trình release có gate rõ và theo dõi 48h đầu, so that v1.0 ra production có kiểm soát và học được gì đó cho v1.1.

## Why
Điểm kết của `docs/plan.md`. BR-1 (không ngoại lệ cho Bảo mật/Vận hành) là cam kết kỷ luật — release trễ 1 tuần rẻ hơn sự cố production tuần đầu.

## Scope
**In:** rà docs khớp code (specs/CONFIGURATION/runbook theo staging thật); Release Checklist `docs/plan.md` §6 — mỗi mục người tick + bằng chứng; tag v1.0.0; deploy prod theo runbook §1; bật lịch Mode 1; theo dõi 48h (alert channel + phân công trực); retro release → backlog v1.1.
**Out:** marketing/công bố; v1.1 planning chi tiết (sau retro).

## Business Rules
1. Mục checklist nhóm Bảo mật/Vận hành không đạt → không release; không có "fix sau".
2. Deploy prod đúng runbook — lệch = sửa runbook trước rồi làm lại theo.
3. 48h đầu: mọi alert có người nhận trong 30' (phân công ghi rõ).

## Acceptance Criteria
1. **(gate)** Checklist 100% có bằng chứng; nhóm Bảo mật/Vận hành không mục nào waive.
2. **(go-live)** Prod chạy 48h không Sev-1; Mode 1 sáng đầu tiên trên prod thành công.
3. **(retro)** Biên bản retro + danh sách v1.1 (TikTok/FB kích hoạt, visual diff, A/B prompt, autoscale…) commit vào docs.

## Data & API
N/A. Output: tag, checklist hoàn chỉnh, biên bản retro.

## Decisions already locked
- ⏳ Định nghĩa Sev-1: mất khả năng tạo/duyệt/đăng video hoặc lộ dữ liệu.

## Execution Steps

Work these in order. Update `state/10-6.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. This task executes and records rather than writing new code/tests (per its own DoD) — "Verify" below means "evidence exists and is attached," and "Commit" still applies to every doc/checklist artifact produced.

### Step 1: Docs-vs-code reality check
- **Files:** `docs/specs/*.md`, `docs/CONFIGURATION.md`, `docs/runbook.md`.
- **Do:** Walk every normative doc (`docs/` per `CLAUDE.md` §2 loading order) against the actual staging deployment and confirm they match — env var defaults, API endpoints, DB schema, runbook commands. Fix any drift found (in the doc, not by changing running behavior to match a stale doc, unless the doc itself is wrong).
- **Verify:** each `docs/` file checked off against staging; any drift found has a corresponding fix commit.
- **On failure:** drift found → not a "failure," it's the expected output of this step — fix the doc (or flag a genuine behavior bug found via drift, per `rules/documentation.md`); if a fix itself fails to land after 3 attempts, block with a specific reason.
- **Commit:** `git add docs && git commit -m "docs: 10-6 reconcile docs with staging reality pre-release" && git push`

### Step 2: Release Checklist (docs/plan.md §6) — evidence for every item (AC1, BR-1)
- **Files:** `docs/plan.md` §6, [checklists/before-release.md](../checklists/before-release.md), evidence artifacts (screenshots/logs/CI links).
- **Do:** Tick every Release Checklist item with attached evidence — no item marked done on assertion alone. Per BR-1, any Bảo mật (Security, from 10-4) or Vận hành (Operations, from 10-5) item that is not fully passing is a **hard release block** — there is no "fix sau" exception, this is the one place in the whole backlog where autonomy-policy's "decide and continue" explicitly does NOT apply; a failing Security/Operations item must stop the release, not just get logged and continued past.
- **Verify:** `checklists/before-release.md` fully ticked with evidence; `docs/plan.md` §6 fully ticked with evidence; zero waived items in Bảo mật/Vận hành groups.
- **On failure:** any Bảo mật/Vận hành item failing → **block the whole release task**, escalate to the user (PO) per the release-manager decision rule — this is a genuine hard stop, not an async-escalate-and-continue situation, since nothing downstream (tag, deploy) can proceed without it.
- **Commit:** `git add docs/plan.md && git commit -m "docs(release): 10-6 release checklist evidence pass, zero waived Security/Ops items (AC1/BR-1)" && git push`

### Step 3: Tag v1.0.0
- **Files:** git tag (annotated).
- **Do:** Once Step 2 passes with zero blocks, create annotated tag `v1.0.0` on the release commit on `main`. Tagging a release commit on `main` is a release-manager-owned publish action — confirm the checklist gate (Step 2) is genuinely clean before tagging; this step still uses standard git tooling, not force-push or history rewriting.
- **Verify:** `git tag -a v1.0.0 -m "..."` succeeds; `git show v1.0.0` shows the correct commit.
- **On failure:** N/A — this step only proceeds once Step 2 is unblocked; do not tag with a known-open Security/Ops item.
- **Commit:** `git push origin v1.0.0` (tag push — reversible, deletable if a mistake is caught immediately; still flag to the user before pushing since this is the release-publish moment referenced in `workflows/autonomous-task-execution.md`'s "publish" carve-out).

### Step 4: Deploy to production per runbook §1 (BR-2)
- **Files:** `docs/runbook.md` §1.
- **Do:** Deploy exactly per the runbook's documented steps (BR-2 — any deviation means fix the runbook first, then redo the deploy per the corrected runbook, not "deploy differently and document it later"). Enable the Mode 1 (Daily AI News) schedule as part of this deploy per Scope.
- **Verify:** production deployment succeeds; runbook §1 steps followed with no undocumented manual intervention; Mode 1 schedule confirmed active.
- **On failure:** deploy step doesn't match runbook reality → stop, fix runbook, redo the deploy from the corrected runbook (BR-2) — this is not a retry-the-same-step case, it's "the instructions were wrong," handled the same way as a Step 1 docs-drift fix.
- **Commit:** `git add docs/runbook.md && git commit -m "docs: 10-6 runbook corrections found during v1.0.0 production deploy (BR-2)" && git push`

### Step 5: 48h monitoring with 30-minute alert response assignment (BR-3, AC2)
- **Files:** `docs/runbook.md` (on-call/alert assignment section), alert channel config.
- **Do:** Set up explicit on-call assignment for the first 48h post-deploy with alert-channel routing, such that any alert has a named responder within 30 minutes (BR-3). Monitor through the window; Mode 1's first scheduled morning run on production must succeed (AC2).
- **Verify:** 48h elapses with zero Sev-1 incidents (Sev-1 defined in Decisions already locked: loss of ability to create/approve/publish video, or data exposure); Mode 1's first prod run succeeds; on-call assignment log shows responses within 30 min for any alert that did fire.
- **On failure:** a Sev-1 occurs → this blocks go-live sign-off per AC2 — do not mark this step done; work the incident per `agents/` incident process if one exists, then restart the 48h clock once resolved and redeployed if the incident required a fix.
- **Commit:** `git add docs/runbook.md && git commit -m "docs(release): 10-6 48h post-deploy monitoring record, zero Sev-1 (BR-3/AC2)" && git push`

### Step 6: Release retro + v1.1 backlog seed (AC3)
- **Files:** `docs/decisions/` or `docs/retro-v1.0.md` (per existing template conventions), `docs/backlog/` (v1.1 candidate list).
- **Do:** Run and commit a release retrospective (biên bản retro) covering what went well/poorly across the whole release. Seed the v1.1 backlog with known deferred items: TikTok/FB activation (10-3 Out-of-scope note), visual diff, A/B prompt testing, autoscale decision (from 10-5 Step 3's assessment).
- **Verify:** retro doc committed; v1.1 candidate list committed, includes at minimum the 4 items named in AC3.
- **On failure:** N/A (documentation step).
- **Commit:** `git add docs && git commit -m "docs: 10-6 v1.0 release retro + v1.1 backlog seed (AC3)" && git push`

### Step 7: Final memory update — v1.0 milestone (DoD)
- **Files:** [memory/project-memory.md](../memory/project-memory.md).
- **Do:** This is the final task in the 230-point backlog. Update `memory/project-memory.md` with the v1.0 milestone reached, retro findings summary, and any Open Questions carried into v1.1 — per `CLAUDE.md` §8 Continuous Learning Policy. This step is itself the Retrospective gate for this task, not a separate afterthought.
- **Verify:** `memory/project-memory.md` reflects v1.0 shipped state and retro findings.
- **On failure:** N/A.
- **Commit:** `git add memory/project-memory.md && git commit -m "docs: 10-6 v1.0 milestone recorded in project memory" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + [checklists/before-release.md](../checklists/before-release.md) + không test mới — thực thi và ghi nhận. This is the final task in the 230-point backlog — after this, update [memory/project-memory.md](../memory/project-memory.md) with the v1.0 milestone and retro findings per CLAUDE.md §8 Continuous Learning Policy.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/10-6.json` → `status: done`, mark `done` in `sprint-status.yaml`. This is the final task in the backlog — there is no next task to move to; confirm the full backlog is `done` in `sprint-status.yaml` and report v1.0 completion.

## Resuming after interruption

If `state/10-6.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked` (most likely at Step 2 on an open Security/Ops item, or Step 5 mid-48h-window), first check whether `blocked_reason` is now resolved before retrying; if still blocked for the same reason, leave it blocked — this task's Step 2/Step 5 blocks are genuine hard stops per BR-1/AC2, not something to route around by picking a different task, since this is the last task in the backlog and depends on 10-4/10-5 already being `done`.
