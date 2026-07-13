# Task 6-4: Benchmark & chốt NFR

**Points:** 3đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 6-2 · **FR:** NFR-1
**State file:** [`state/6-4.json`](state/6-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/6-4-benchmark-chot-nfr` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a team, I want số đo hiệu năng thật trên máy chuẩn, so that NFR là cam kết có cơ sở và quyết định tối ưu dựa trên dữ liệu.

## Why
SRS v3 cố ý để NFR "chốt sau benchmark" — đây là điểm chốt. Kết quả quyết định nhánh `docs/plan.md` §5 (cắt 10-2 lấy chỗ tối ưu hay không).

## Scope
**In:** script benchmark (render/cảnh mỗi layout ×2 format, video 60s, preview load-time); định nghĩa "máy chuẩn" ghi vào ARCHITECTURE.md; chạy 3 lần lấy median; cập nhật NFR-1 số thật; profiling nếu >2× mục tiêu; báo cáo go/no-go với PO trước tuần 11.
**Out:** load test đa user (10-5); tối ưu thực thi (task riêng nếu cần).

## Business Rules
1. Kết quả xấu không im lặng — bắt buộc issue nguyên nhân + phương án + estimate.
2. Benchmark script vào repo, chạy lại được 1 lệnh (dùng lại ở 9-2 AC-1 và 10-5).

## Acceptance Criteria
1. **(happy)** Bảng số liệu (median 3 runs) commit; NFR-1 cập nhật kèm cấu hình máy chuẩn.
2. **(biên/BR-1)** Nếu 60s-video > 6 phút → issue phân tích (bundling? codec? concurrency?) + quyết định PO ghi lại.
3. **(BR-2)** `make benchmark` chạy lại ra kết quả cùng định dạng.

## Data & API
N/A. Output: bảng số liệu trong ARCHITECTURE.md + NFR-1 SRS cập nhật.

## Decisions already locked
- ⏳ Máy chuẩn = máy dev GPU hiện có (ghi cấu hình cụ thể khi chạy).

## Execution Steps

Work these in order. Update `state/6-4.json` after **every** step. This task edits `docs/` normative specs (`ARCHITECTURE.md`, `SRS.md` NFR-1) — per `CLAUDE.md` §7 that's a product/architecture handoff change owned by BA/PO process: propose the exact edit, flag it explicitly for PO confirmation, but per [rules/autonomy-policy.md](../rules/autonomy-policy.md) async-escalation, don't block the rest of the run waiting for that confirmation — land the proposed edit, note it in `memory/project-memory.md` Open Questions as PO-pending, and keep going.

### Step 1: Scaffold the benchmark harness as a single reusable command (BR-2)
- **Files:** `scripts/benchmark/render_benchmark.py`, `Makefile` (`benchmark` target)
- **Do:** build a script wrapping the 6-2 `render_orchestrator` + `video_merge` that measures: render time per scene for each layout class × 2 formats, a full 60s-video render, and Player preview load-time. Must be invocable as one command (`make benchmark`) so it's reusable by 9-2 AC-1 and 10-5 later without modification.
- **Verify:** `make benchmark -- --dry-run` (or equivalent flag) → exits 0 without doing a full run, prints the planned measurement matrix.
- **On failure:** transient → retry 3×; logic/config → `systematic-debugging` skill; still failing → mark `blocked`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add scripts/benchmark/render_benchmark.py Makefile && git commit -m "feat(benchmark): 6-4 scaffold reusable render benchmark harness (BR-2)" && git push`

### Step 2: Define and record the reference machine ("máy chuẩn")
- **Files:** `docs/ARCHITECTURE.md`
- **Do:** record the actual CPU/RAM/GPU/OS of the dev machine used to run the benchmark (Decisions already locked: "máy dev GPU hiện có" — write the concrete specs, not the placeholder). This is a `docs/` edit — propose it, flag for PO confirmation per the note above, continue.
- **Verify:** diff reviewed for placement consistent with `ARCHITECTURE.md`'s existing structure.
- **On failure:** same policy as Step 1 for the scripting part; the doc content itself isn't a "failure," just PO-pending.
- **Commit:** `git commit -m "docs(architecture): 6-4 record benchmark reference machine spec"`

### Step 3: Run the benchmark 3× and take the median
- **Files:** benchmark output under `docs/benchmarks/` (new location — if it doesn't already exist, add it and update `docs/README.md`'s reading-order table per [rules/documentation.md](../rules/documentation.md))
- **Do:** run `make benchmark` three times; compute the median per metric (render/scene per layout×format, full 60s video, preview load-time).
- **Verify:** a results table exists with all 3 raw runs + a median row.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "chore(benchmark): 6-4 record 3-run median benchmark results"`

### Step 4: Update NFR-1 in SRS.md with real numbers
- **Files:** `docs/SRS.md` (NFR-1 section)
- **Do:** replace the placeholder/estimated NFR-1 targets with the measured median numbers + the reference machine config from Step 2. This is a `docs/` normative-spec edit — propose the exact wording, flag explicitly for PO confirmation (per `CLAUDE.md` §7's "propose → user confirms" workflow, since prior decisions here are PO-dated), and continue without blocking per async-escalation.
- **Verify:** diff reviewed; numbers match Step 3's median row exactly, no silent rounding/adjustment.
- **On failure:** same policy as Step 1 for the update mechanics.
- **Commit:** `git commit -m "docs(srs): 6-4 update NFR-1 with measured benchmark numbers (PO-pending confirmation)"`

### Step 5: BR-1 — bad results don't stay silent
- **Files:** `memory/project-memory.md` (Open Questions), plus a written analysis artifact if the threshold is breached
- **Do:** if any measured 60s-video render time exceeds 6 minutes (AC-2 threshold), write a root-cause analysis (bundling? codec? concurrency?) with a proposed remediation and rough estimate — don't accept a bad number silently. If the threshold is **not** breached, explicitly record "within target" rather than omitting the check.
- **Verify:** either an analysis artifact exists (breach case) or an explicit "within target" note exists (pass case) — one of the two, never neither.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "docs(benchmark): 6-4 BR-1 result analysis (breach or within-target note)"`

### Step 6: Confirm reusability + assemble go/no-go report
- **Files:** `scripts/benchmark/render_benchmark.py`, `docs/benchmarks/` summary
- **Do:** rerun `make benchmark` end-to-end and confirm output matches Step 3's format exactly (BR-2); assemble the go/no-go summary for PO review ahead of week 11, per Scope — this decides whether `docs/plan.md` §5's 10-2 gets cut for optimization time.
- **Verify:** `make benchmark` rerun → output format identical structure to Step 3's artifact (AC-3).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "chore(benchmark): 6-4 verify make benchmark reusability + go/no-go summary"`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + không phải test — là đo đạc; script tái dùng làm smoke perf về sau. Update [context/testing-strategy.md](../context/testing-strategy.md) with real numbers once measured, per CLAUDE.md §11 known-gaps policy. NFR-1/ARCHITECTURE.md edits are PO-pending confirmation per `docs/` change policy — don't treat as final until confirmed.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/6-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/6-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
