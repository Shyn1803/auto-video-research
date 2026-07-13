# Task 7-2: Mode 1 pipeline tự hành + chọn topic

**Points:** 5đ · **Epic:** 7 — Automation · **Depends:** 7-1, 4-7 · **FR:** Mode 1 SRS §2
**State file:** [`state/7-2.json`](state/7-2.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/7-2-mode-1-pipeline-tu-hanh` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.
>
> **Non-negotiable gate note (autonomy-policy.md "What this does NOT change"):** the Mode 1 Fact Check gate is intentional business logic, not agent-workflow friction. Every Execution Step below that touches the graph must preserve the `interrupt` on the Fact Check node (SRS §2: `Research → Ranking → Fact Check (gate) → Outline → Script → Storyboard → Scene JSON → Render → Publish`). No step may make the pipeline skip, auto-pass, or bypass fact-checking to "get to READY faster" — a `FAIL` verdict always produces `NEED_REVIEW`, never a silent auto-continue (BR-2).

## User story
As a PO, I want hệ thống tự chọn chủ đề AI đáng nói nhất hôm nay và làm video hoàn chỉnh, so that sáng nào cũng có video chờ duyệt mà không ai phải động tay.

## Why
Mode 1 là nửa giá trị của SRS ("Daily AI News"). Quy tắc "không ép ra video rác" (BR-3) bảo vệ chất lượng kênh — thà không đăng còn hơn đăng nhạt.

## Scope
**In:** graph mode không-interrupt (trừ gate factcheck); topic selection: quét trending (HN top/arXiv mới/RSS 24h) → ranking → chọn top chưa làm (dedupe 7 ngày bằng embedding); auto-approve kèm validation máy (script parse ok, scene strict-valid, produce đủ); dừng READY theo gate; topic cố định qua schedules.config; timeout tổng 30'.
**Out:** auto-publish (7-3 + 8-3); nhiều video/ngày (config sẵn, default 1); chọn topic bằng vote cộng đồng.

## Business Rules
1. Mọi auto-approve ghi actor=system + validation pass nào (audit đầy đủ như người duyệt).
2. FAIL factcheck → NEED_REVIEW + notify; giữ mọi bước đã xong cho người xử lý tiếp bằng Mode 2 UI.
3. Không topic nào đạt ngưỡng điểm (config) → kết thúc "hôm nay không có gì đáng làm" + notify nhẹ — không ép.
4. Quá 30' → cancel (4-7) + FAILED(timeout) + notify.
5. Dedupe topic 7 ngày bằng embedding similarity (không chỉ string match).

## Acceptance Criteria
1. **(happy)** Run sáng (fixture trending) → project READY ≤30'; mọi step_version đủ; mở sửa được như Mode 2.
2. **(biên/BR-3)** Fixture trending nghèo → kết thúc sạch không project; notify "không có gì đáng làm".
3. **(biên/BR-5)** Topic cùng nghĩa khác chữ với video 3 ngày trước → bị dedupe, chọn topic kế.
4. **(lỗi/BR-4)** Node treo giả lập → 30' cancel + FAILED(timeout) + notify.
5. **(BR-2)** Fixture mâu thuẫn → dừng NEED_REVIEW; xử lý bằng UI 5-6 → chạy tiếp tới READY.

## Data & API
projects.mode=daily_news; schedules.config (topic/gate/ngưỡng). Contract change: không.

## Decisions already locked
- ⏳ Ngưỡng điểm topic khởi điểm 70/100 — tune theo dogfooding.
- 1 video/ngày mặc định.

## Execution Steps

Work these in order. Update `state/7-2.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Trending scan + topic ranking
- **Files:** `backend/app/pipeline/nodes/topic_scan.py`, `backend/app/adapters/search/` (reuse existing search adapters, no new capability)
- **Do:** implement trending scan sources (HN top, arXiv new, RSS last 24h) behind the existing adapter pattern (`patterns/provider-adapter.md`) — no direct HTTP calls from the node. Rank candidates against the config threshold (`schedules.config.topic_threshold`, starting default 70/100 per "Decisions already locked" — value must be read from config, never hardcoded, since it's marked ⏳ tune-by-dogfooding).
- **Verify:** `cd backend && pytest backend/tests/unit/pipeline/nodes/test_topic_scan.py -v` → ranking produces deterministic ordering given a fixture trending set.
- **On failure:** transient (adapter network mock flaky) → retry 3×; ranking logic bug → `systematic-debugging` skill; still failing → `blocked`.
- **Commit:** `git add backend/app/pipeline/nodes/topic_scan.py && git commit -m "feat(mode1): 7-2 trending scan + topic ranking node"` → `git push`

### Step 2: Dedupe by embedding similarity (7-day window)
- **Files:** `backend/app/pipeline/nodes/topic_dedupe.py`
- **Do:** embed candidate topic + last 7 days of `daily_news` project topics (embedding-tier LLM call per `rules/performance.md`), reject candidates above similarity threshold, fall through to next-ranked candidate (BR-5) — must catch semantically-equivalent, differently-worded topics ("GPT-5.5 ra mắt" vs "OpenAI phát hành GPT-5.5"), not just string match.
- **Verify:** `cd backend && pytest backend/tests/unit/pipeline/nodes/test_topic_dedupe.py -k semantic_dedupe` → paraphrased topic vs 3-day-old video is rejected, distinct topic passes. Covers AC3.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(mode1): 7-2 embedding-based topic dedupe"` → `git push`

### Step 3: Non-interrupt graph mode with Fact Check gate preserved
- **Files:** `backend/app/pipeline/graph.py` (extend, don't fork — reuse the Mode 2 graph per `docs/dev-guide.md`), `backend/app/pipeline/nodes/auto_approve.py`
- **Do:** add a `mode=daily_news` graph configuration where every human-approval interrupt is replaced by `auto_approve.py` running machine validation (script parse OK, scene strict-valid against `backend/app/schemas/scene.py`, produce output complete) — **except** the Fact Check interrupt, which stays a real gate per the non-negotiable note above. `auto_approve.py` writes `actor=system` + which validation passed to the audit log, same shape as a human approval (BR-1). On Fact Check `FAIL`, transition to `NEED_REVIEW`, keep all completed step outputs intact, and emit a notify event for 7-4 (BR-2) — do not raise/cancel/rollback completed work.
- **Verify:** `cd backend && pytest backend/tests/integration/test_mode1_graph.py -k "auto_approve or factcheck_fail"` → auto-approve path writes correct audit rows (AC1 audit shape); FAIL fixture stops at `NEED_REVIEW` with prior steps' outputs retrievable and editable via Mode 2 UI (AC5).
- **On failure:** logic error touching the graph → `systematic-debugging` skill, treat as high-blast-radius per `CLAUDE.md` §4 (this graph is shared with Mode 2 — a bug here can break Mode 2 too); still failing after 3 → `blocked`, flag in `memory/project-memory.md` Open Questions before moving on.
- **Commit:** `git commit -m "feat(mode1): 7-2 non-interrupt graph mode with fact-check gate intact"` → `git push`

### Step 4: "Nothing worth making today" clean exit (BR-3)
- **Files:** `backend/app/pipeline/nodes/topic_scan.py` (extend), `backend/app/services/notifications.py` (call into 7-4's adapter, stub if 7-4 not yet merged — coordinate via `sprint-status.yaml` dependency state)
- **Do:** when no candidate clears the configured threshold, end the run cleanly with no project created and a low-key notify ("hôm nay không có gì đáng làm") — never force a low-quality project through just to produce output.
- **Verify:** `cd backend && pytest backend/tests/unit/pipeline/nodes/test_topic_scan.py -k poor_trending` → poor-trending fixture yields zero projects + one notify call, run marked complete (not failed). Covers AC2.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(mode1): 7-2 clean no-topic exit path"` → `git push`

### Step 5: 30-minute total timeout → cancel + FAILED(timeout)
- **Files:** `backend/app/pipeline/nodes/` (wire into existing run-control from 4-7, don't reimplement cancel/timeout)
- **Do:** reuse the run-control cancel mechanism built in task 4-7 (`dieu-khien-run-huy-ngam-resume`) to enforce a 30-minute wall-clock budget for the whole Mode 1 run; on breach, cancel, set status `FAILED(timeout)`, notify (BR-4). Do not build a second timeout mechanism — this is a config/wiring step onto the existing one.
- **Verify:** `cd backend && pytest backend/tests/integration/test_mode1_graph.py -k timeout` → simulated hung node → cancelled at 30' boundary (test uses a short override timeout, not a literal 30-minute wait), status `FAILED(timeout)`, notify fired. Covers AC4.
- **On failure:** same retry policy; if 4-7's cancel mechanism doesn't expose what's needed, that's a scope-ambiguity case — flag per `rules/autonomy-policy.md` and note the gap rather than duplicating cancel logic.
- **Commit:** `git commit -m "feat(mode1): 7-2 wire 30-minute run timeout via 4-7 cancel mechanism"` → `git push`

### Step 6: Scheduler wiring — `mode1_pipeline` job + fixed topic config
- **Files:** `backend/app/services/jobs/mode1_pipeline_job.py` (from 7-1, now implemented for real instead of stub)
- **Do:** the 7-1 `mode1_pipeline` job handler invokes this graph with `schedules.config` (topic source config, gate threshold, 1 video/day default per "Decisions already locked"); project created with `projects.mode = daily_news`.
- **Verify:** `cd backend && pytest backend/tests/integration/test_mode1_graph.py -k happy_path` → fixture trending set → project reaches `READY` within the simulated budget, all `step_version` rows present, project editable afterward exactly like a Mode 2 project. Covers AC1.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "feat(mode1): 7-2 wire mode1_pipeline scheduler job to graph"` → `git push`

### Step 7: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/integration/test_mode1_graph.py`, `backend/tests/unit/pipeline/nodes/`
- **Do:** one test per AC (happy/BR-3/BR-5/BR-4/BR-2, already built incrementally in Steps 1-6 above — this step is the consolidation + the full-run integration test with MockLLM across two trending fixtures (rich/poor) called out in Test Notes. Tag the full-run test `slow`.
- **Verify:** `cd backend && pytest tests/ -m "not slow" -k mode1 -v` (fast set) and `pytest tests/ -m slow -k mode1 -v` (full-run, only on PRs touching pipeline + nightly per Test Notes) → all pass.
- **On failure:** same retry policy.
- **Commit:** `git commit -m "test(mode1): 7-2 full AC coverage incl. slow full-run integration"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + full-run integration MockLLM là test dài nhất CI (slow tag, chạy PR đụng pipeline + nightly).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/7-2.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/7-2.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
