# Task 10-5: Load test + backup drill + nghiệm thu local-first

**Points:** 3đ · **Epic:** 10 — Release · **Depends:** 9-2, 9-5 · **FR:** NFR-2/3/6, FR-21
**State file:** [`state/10-5.json`](state/10-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/10-5-load-test-backup-drill` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a team, I want bằng chứng hệ chịu tải mục tiêu, khôi phục được từ backup, và chạy đủ với 0 API key, so that release dựa trên kiểm chứng chứ không hy vọng.

## Why
3 mục "Vận hành" của Release Checklist. BR-1 (người không viết code làm drill) kiểm luôn chất lượng runbook — tài liệu chưa ai làm theo là tài liệu chưa xong.

## Scope
**In:** k6/locust: 5 render đồng thời + 20 user UI trên staging → số liệu vào ARCHITECTURE.md; đánh giá autoscale cần/chưa (quyết định cho v1.1); restore drill máy sạch theo runbook (đo thời gian, do người không viết code thực hiện); CI job E2E `.env` 0 key (nightly với Ollama thật).
**Out:** stress đến gãy; multi-region.

## Business Rules
1. Drill do người không viết code làm theo runbook — mọi chỗ tắc = bug tài liệu → sửa runbook trong task này.
2. Load test chạy trên staging cấu hình = production (không test trên dev).
3. Nightly 0-key phải xanh 3 đêm liên tiếp mới tick (chống may mắn).

## Acceptance Criteria
1. **(load)** 5 render + 20 user: không lỗi, p95 API <1s (⏳ ngưỡng), số liệu commit.
2. **(drill/BR-1)** Restore máy sạch thành công bởi người không viết code; thời gian ghi runbook; chỗ tắc đã sửa docs.
3. **(local-first/BR-3)** Nightly 0-key xanh 3 đêm liên tiếp — nghiệm thu FR-21/NFR-6 chính thức.

## Data & API
N/A. Output: số liệu ARCHITECTURE.md; thời gian restore vào runbook; CI job mới.

## Decisions already locked
- ⏳ p95 API < 1s dưới tải mục tiêu.

## Execution Steps

Work these in order. Update `state/10-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit. This task is measurement + operational verification, not feature code — several steps require a human ("người không viết code") to execute per BR-1; where the executing agent cannot itself act as that person, it prepares everything needed and explicitly flags the step as pending human execution rather than skipping or faking it.

### Step 1: k6 load test script — 5 concurrent renders + 20 UI users
- **Files:** `scripts/loadtest/k6-render.js`, `scripts/loadtest/k6-ui.js` (or `locust/` equivalent), `Makefile` (`loadtest` target).
- **Do:** Write a k6 (or locust) script simulating 5 concurrent render jobs plus 20 concurrent UI users against a staging-equivalent environment (BR-2 — must run on staging config = production, never dev). Wire it into `make loadtest`.
- **Verify:** `make loadtest` runs against a local/staging target and produces a report file without erroring on the tooling itself (content/thresholds checked in Step 2).
- **On failure:** transient (staging unreachable) → retry 3× with backoff; script logic error → `systematic-debugging`; still failing after 3 → block, log in `memory/project-memory.md`.
- **Commit:** `git add scripts/loadtest Makefile && git commit -m "feat(loadtest): 10-5 k6 script for 5 concurrent renders + 20 UI users (make loadtest)" && git push`

### Step 2: Run load test on staging, capture p95 + error rate (AC1, BR-2)
- **Files:** `docs/ARCHITECTURE.md` (results table), CI/staging run artifacts.
- **Do:** Execute the load test against staging (production-equivalent config, per BR-2 — do not substitute dev). Capture p95 API latency and error rate. Compare against the locked target (p95 < 1s, per Decisions already locked — still ⏳ pending final PO confirmation, flag if the measured number requires renegotiating that threshold).
- **Verify:** run completes with zero request errors and p95 < 1s; numbers committed into `docs/ARCHITECTURE.md`.
- **On failure:** errors under load or p95 breach → not transient, this is a genuine performance finding — investigate root cause (per `rules/performance.md` scaling guidance: replica count before single-worker optimization) before re-running; if still failing after 3 attempts, block and escalate the threshold question to the user (PO-owned per `rules/autonomy-policy.md`, since the ⏳ target itself may need renegotiation).
- **Commit:** `git add docs/ARCHITECTURE.md && git commit -m "docs(perf): 10-5 load test results — 5 render + 20 UI users, p95/error rate committed (AC1)" && git push`

### Step 3: Autoscale needed/not-needed assessment
- **Files:** `docs/ARCHITECTURE.md` (or `docs/plan.md` v1.1 backlog notes).
- **Do:** Based on Step 2's headroom data, write an explicit assessment of whether autoscaling is needed now or can be deferred to v1.1 — this is a decision *input* for v1.1 planning, not a decision this task makes unilaterally (product-scheduling calls stay PO-owned per `rules/autonomy-policy.md`).
- **Verify:** assessment paragraph committed with data-backed reasoning (current headroom vs. target load).
- **On failure:** N/A (documentation/analysis step).
- **Commit:** `git add docs/ARCHITECTURE.md && git commit -m "docs(perf): 10-5 autoscale needed/not-needed assessment for v1.1" && git push`

### Step 4: Prepare restore-drill runbook for a non-developer operator (BR-1)
- **Files:** `docs/runbook.md` (backup/restore section).
- **Do:** Review and tighten the existing restore runbook so every step is followable by someone who did not write the code — no assumed context, no shorthand commands without explanation. This step is prep; the actual drill execution is Step 5 and requires a real non-developer to run it.
- **Verify:** self-review checklist — every command in the restore section has enough context (what it does, expected output) that a non-author could execute it without asking a question.
- **On failure:** standard retry/debugging policy (documentation clarity issues are logic, not transient).
- **Commit:** `git add docs/runbook.md && git commit -m "docs: 10-5 tighten restore runbook for non-developer executor (prep for BR-1 drill)" && git push`

### Step 5: Execute restore drill on a clean machine, timed, by a non-developer (BR-1, AC2)
- **Files:** `docs/runbook.md` (drill record section).
- **Do:** Have someone who did not write the code follow the runbook from Step 4 to restore the system on a clean machine, timing the process. Every point where they get stuck is treated as a runbook bug and fixed in this same task, not deferred (per BR-1 — "mọi chỗ tắc = bug tài liệu"). **This step requires a human operator and cannot be simulated by the executing agent alone** — if no such operator is available in this session, mark this step `blocked` with reason "awaiting non-developer drill operator" and continue with other unblocked steps/tasks, per `rules/autonomy-policy.md` async escalation.
- **Verify:** drill completes successfully; restore time recorded in the runbook; every friction point has a corresponding runbook fix committed.
- **On failure:** operator gets stuck → not a "failure" to retry, it's the signal to fix docs — fix and re-verify with the same operator if possible; if no operator available after reasonable attempts, block per above and flag in `memory/project-memory.md` Open Questions.
- **Commit:** `git add docs/runbook.md && git commit -m "docs: 10-5 restore drill executed by non-developer, timing + fixes recorded (BR-1/AC2)" && git push`

### Step 6: Nightly 0-key E2E CI job (local-first verification)
- **Files:** CI workflow config for a scheduled/nightly job, `.env.nightly-0key` (or equivalent fixture with zero API keys set), `tests/e2e/zero_key_pipeline_test.*`.
- **Do:** Add a nightly CI job that runs a full E2E pipeline (research → factcheck → script → storyboard → render) using real Ollama + local providers only, zero paid API keys — this is the FR-21/NFR-6 local-first promise, verified continuously rather than asserted once.
- **Verify:** job runs to completion locally/in CI with `ALLOW_PAID` unset/false and no paid keys present, producing a valid video output.
- **On failure:** transient (Ollama not warmed up, resource contention) → retry same night's run isn't meaningful here (BR-3 needs *separate* nights) — instead fix the transient cause and let the next scheduled run count; genuine pipeline failure with 0 keys → not transient, this is exactly what NFR-6 is meant to catch — `systematic-debugging`, fix the code path that has a hidden paid-provider dependency.
- **Commit:** `git add .github/workflows tests/e2e && git commit -m "feat(ci): 10-5 nightly 0-key E2E pipeline job (FR-21/NFR-6 continuous verification)" && git push`

### Step 7: Confirm 3 consecutive green nightly runs (BR-3, AC3)
- **Files:** CI run history (link in PR/state file), `memory/project-memory.md` (milestone note).
- **Do:** Track the nightly job from Step 6 across 3 consecutive nights. This step cannot be compressed into one session — it is time-gated by design (BR-3: "chống may mắn"). Record each night's run link. On the 3rd consecutive green run, this constitutes the official FR-21/NFR-6 local-first acceptance (AC3).
- **Verify:** 3 consecutive nightly CI runs green, links recorded.
- **On failure:** any red run in the streak → the streak resets to zero per BR-3's intent (a single lucky pass doesn't count, and neither does breaking the "consecutive" requirement) — root-cause the failure via `systematic-debugging`, fix, and restart the 3-night count. Mark this step `blocked` with reason "nightly streak in progress, N/3" between sessions — this is expected, not an error state, while the streak accumulates.
- **Commit:** `git add memory/project-memory.md && git commit -m "docs: 10-5 3 consecutive green nightly 0-key runs — FR-21/NFR-6 accepted (BR-3/AC3)" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + [checklists/before-release.md](../checklists/before-release.md) + k6 script vào repo (`make loadtest`); drill có biên bản ngắn (ai, bao lâu, vướng gì). This is measurement + operational verification, not just code.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/10-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/10-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task, or another night's nightly run just landed) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
