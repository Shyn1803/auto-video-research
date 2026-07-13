# Task 8-7: Analytics Insights — giữ chân, chủ đề, gợi ý hành động

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-5 (retention mở rộng), 8-6 (khung màn), 7-1 (apply schedule) · **FR:** FR-13
**State file:** [`state/8-7.json`](state/8-7.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/8-7-analytics-insights` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want hệ thống tự rút ra insight từ số liệu và gợi ý hành động, so that tôi ra quyết định nội dung tiếp theo mà không phải tự làm phân tích trên bảng số thô.

## Why
Feedback PO trực tiếp: "analytics chưa thực sự thể hiện được sự phân tích" — 8-6 là *hiển thị*, task này là *phân tích*. Insight là **rule-based trên số liệu thật** (không LLM đoán mò) — mỗi insight phải trích được số + cỡ mẫu.

## Scope
**In:**
- **Giữ chân (Tổng quan):** đường giữ chân trung bình kênh (0/15/30/45s) từ YouTube retention; callout điểm rơi mạnh nhất.
- **Drill-down video:** giữ chân theo giây + map điểm rơi sang ranh giới cảnh (join timeline scene) — "rơi 15% tại cảnh #6"; nguồn view; so với TB kênh (badge ✓/✗ ±%).
- **Theo chủ đề:** gắn `topic_group` cho project (AI phân loại lúc tạo, sửa được); bảng nhóm; gợi ý tỉ trọng chủ đề + nút "Áp dụng vào cấu hình Mode 1".
- **Insight tự động (rule-based):** ~5 rule khởi điểm: so nhóm chủ đề (xem hết), so độ dài (≤50s vs >70s), giờ đăng vs view 48h, cảnh báo CTR giảm so TB, cỡ mẫu kèm mọi insight.
**Out:** insight bằng LLM (v1.1); A/B thumbnail/title (v1.1); demographics (v1.1); nền tảng ngoài YouTube.

## Business Rules
1. Insight chỉ hiện khi đủ cỡ mẫu (mặc định ≥5 video/nhóm) — thiếu → "chưa đủ dữ liệu (3/5 video)".
2. Mọi insight kèm số gốc + cỡ mẫu ("54% vs 41%, 7 vs 5 video").
3. `topic_group` do AI gán khi tạo project (tier cheap, danh sách config cố định); user sửa được; đổi nhóm → số liệu tính lại.
4. "Áp dụng vào Mode 1" chỉ điều chỉnh trọng số ưu tiên chủ đề trong schedules.config, có confirm + audit.
5. Map điểm-rơi→cảnh dùng retention buckets của YouTube (độ phân giải hạn chế) — hiển thị "≈ cảnh #N" (xấp xỉ), tooltip giải thích.

## Acceptance Criteria
1. **(happy)** Seed 14 video 3 nhóm chủ đề đủ mẫu → tab Chủ đề bảng đúng số; Insight ①② hiện đúng công thức kèm cỡ mẫu.
2. **(biên/BR-1)** Nhóm 3 video → insight thay bằng "chưa đủ dữ liệu (3/5)".
3. **(biên/BR-3)** Đổi topic_group 1 video → bảng nhóm tính lại ngay; audit ghi.
4. **(biên/BR-5)** Drill-down video → điểm rơi map "≈ cảnh #N" khớp timeline scene; tooltip xấp xỉ hiện.
5. **(BR-4)** "Áp dụng vào Mode 1" → confirm nêu trọng số cũ→mới → schedules.config đổi + audit.
6. **(quyền)** Creator xem insight; chỉ admin bấm Áp dụng (🅐).

## Data & API
Bảng: `projects.topic_group` (cột mới). Endpoints: `GET /analytics/insights?from&to`, `GET /analytics/topics`, `POST /analytics/apply-topic-weights` 🅐 (mới) → cập nhật api-spec §8 + database-schema. Contract change: **có**.

## Decisions already locked
- ⏳ Insight rule-based v1, không LLM (giải thích được, không bịa).
- ⏳ Danh sách topic_group: công-cụ/hướng-dẫn · tin-model · nghiên-cứu/paper · khác. Ngưỡng cỡ mẫu 5 video/nhóm.

## Execution Steps

Work these in order. Update `state/8-7.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit. This is a "đổi contract" task (3 new endpoints + 1 new column + new metric keys) — `docs/specs/api-spec.md` §8 and `docs/specs/database-schema.md` must be updated in the same PR as the code (`rules/documentation.md`), each with a **Contract changes** note per `rules/pull-requests.md`.

### Step 1: `projects.topic_group` migration + retention metric keys
- **Files:** `alembic/versions/{rev}_add_topic_group.py`, `docs/specs/database-schema.md` update
- **Do:** add `topic_group` column to `projects` (values from the fixed config list: công-cụ/hướng-dẫn · tin-model · nghiên-cứu/paper · khác, per locked decision); extend the 8-5 collector's metric vocabulary with `retention_15s`/`retention_30s`/`retention_45s`/`views_48h` keys stored in the existing `metrics` table (no new table — reuse the partitioned schema per `rules/performance.md`). Update `docs/specs/database-schema.md` in the same commit.
- **Verify:** run migration against scratch DB → applies cleanly; `alembic downgrade -1` → reverts cleanly.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add alembic/ docs/specs/database-schema.md && git commit -m "feat(analytics): 8-7 add topic_group column + retention metric keys"` → `git push`

### Step 2: AI topic_group classification at project creation (BR-3)
- **Files:** `backend/app/pipeline/nodes/classify_topic_group.py` (or hook into existing project-creation node)
- **Do:** classify `topic_group` via an LLM call at `cheap` tier (per `rules/performance.md` — this is a cheap/ranking-shaped task, not a strong-tier one) from the fixed config list; user can edit it afterward; changing it triggers a recompute of dependent aggregates (BR-3, AC3). This is a classification label, not a layout decision — does not touch the Layout Engine boundary.
- **Verify:** `pytest backend/tests/unit/pipeline/test_classify_topic_group.py -q` → passes with the LLM boundary mocked (per `rules/testing.md` — zero live LLM calls in the test suite).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/pipeline/nodes/classify_topic_group.py && git commit -m "feat(analytics): 8-7 add AI topic_group classification"` → `git push`

### Step 3: Retention collector extension (extends 8-5) + retention-to-scene mapping (BR-5)
- **Files:** `backend/app/pipeline/jobs/analytics_collector_job.py` (extend), `backend/app/services/retention_mapping_service.py`
- **Do:** extend the 8-5 daily job to also pull YouTube retention buckets (0/15/30/45s) and `views_48h` per video; map the steepest retention drop-off to an approximate scene boundary by joining against the video's timeline scene data, labeling it "≈ cảnh #N" with a tooltip explaining the approximation (BR-5 — YouTube's bucket resolution is coarse, never claim exact).
- **Verify:** `pytest backend/tests/unit/services/test_retention_mapping_service.py -q` → passes against a fixture timeline.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/pipeline/jobs/analytics_collector_job.py backend/app/services/retention_mapping_service.py && git commit -m "feat(analytics): 8-7 extend collector with retention + scene mapping"` → `git push`

### Step 4: Insight rule engine (rule-based, pure function — BR-1, BR-2)
- **Files:** `backend/app/services/insight_rules.py`
- **Do:** implement the ~5 starter rules as pure functions over a dataframe/dataset (per Test Notes — "pure function trên dataframe → test nhanh không DB"): topic-group completion comparison, length comparison (≤50s vs >70s), publish-hour vs 48h views, CTR-drop-vs-average alert, all gated by a minimum sample size (default 5 videos/group, BR-1) — below threshold, return a "chưa đủ dữ liệu (n/5 video)" result instead of a conclusion, never a weak/misleading one-liner (BR-2: every insight carries its raw numbers + sample size, e.g. "54% vs 41%, 7 vs 5 video"). No LLM in this engine per the locked decision — rule-based only.
- **Verify:** `pytest backend/tests/unit/services/test_insight_rules.py -q` → passes, one test per rule's formula plus one BR-1 insufficient-sample test per rule.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/insight_rules.py && git commit -m "feat(analytics): 8-7 add rule-based insight engine"` → `git push`

### Step 5: Insights/topics API endpoints + apply-topic-weights (BR-4, admin-only)
- **Files:** `backend/app/api/routes/analytics_insights.py` (new endpoints per epic doc: `GET /analytics/insights`, `GET /analytics/topics`, `POST /analytics/apply-topic-weights`), `docs/specs/api-spec.md` §8 update
- **Do:** `GET /analytics/insights?from&to` returns the rule engine output; `GET /analytics/topics` returns the per-topic-group aggregate table; `POST /analytics/apply-topic-weights` is admin-only (🅐) and only adjusts topic priority weights inside `schedules.config` — requires an explicit confirm step showing old→new weights and writes an audit log entry (BR-4, no silent change); disabled with a tooltip when no Mode 1 schedule exists yet. Update `docs/specs/api-spec.md` §8 in the same commit — this is a contract change.
- **Verify:** `pytest backend/tests/integration/api/test_analytics_insights.py -q -k "apply_topic_weights_admin_only"` → passes (403 for non-admin).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/routes/analytics_insights.py docs/specs/api-spec.md && git commit -m "feat(analytics): 8-7 add insights/topics/apply-weights endpoints"` → `git push`

### Step 6: Analytics screen — Insight tab UI (3 tabs: Tổng quan, Theo video, Theo chủ đề)
- **Files:** frontend under `src/app/analytics/` extending 8-6's screen, matching wireframe **Analytics** all 3 tabs
- **Do:** Tổng quan tab: channel-average retention curve (0/15/30/45s) + steepest-drop callout + Insight 💡 list (real text, not chart-only, for screen readers); Theo video tab: drill-down retention-per-second, "≈ cảnh #N" mapping with tooltip, view-source breakdown, vs-channel-average badge (✓/✗ ±%); Theo chủ đề tab: topic-group table + weight suggestion + "Áp dụng vào cấu hình Mode 1" button (disabled+tooltip when no schedule, per UI/UX states); states: default/loading skeleton/empty-or-insufficient-sample (BR-1 progress shown)/error banner.
- **Verify:** exercise in a real running browser (per `rules/testing.md`) — screenshot all 3 tabs including an insufficient-sample state; `npm run typecheck` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add src/app/analytics/... && git commit -m "feat(analytics): 8-7 add Insights tab UI (3 tabs)"` → `git push`

### Step 7: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/services/test_insight_rules.py`, `backend/tests/integration/api/test_analytics_insights.py`, `tests/fixtures/analytics/seed_14x30_retention.py`
- **Do:** write the 14-video × 30-day × retention fixture generator (per Test Notes — generator, not hand-authored); one test per AC (AC1 happy topic table + insight ①② match hand-computed query, AC2 BR-1 insufficient-sample-3-of-5, AC3 BR-3 topic_group-edit-recomputes + audit entry, AC4 BR-5 drill-down "≈ cảnh #N" matches fixture timeline + tooltip, AC5 BR-4 apply-confirms-old-to-new-weights + audit, AC6 permission — creator can view, only admin can apply).
- **Verify:** `pytest backend/tests/unit/services/test_insight_rules.py backend/tests/integration/api/test_analytics_insights.py -q` → all AC-mapped tests pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests/ && git commit -m "test(analytics): 8-7 cover all acceptance criteria"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + seed analytics 14 video × 30 ngày × retention là fixture lớn (generator, không tay); mỗi rule 1 unit test công thức + 1 test BR-1 thiếu mẫu.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/8-7.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/8-7.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
