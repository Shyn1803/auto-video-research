# Task 8-3: YouTube upload + AI disclosure + quota

**Points:** 5đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-2 · **FR:** FR-12
**State file:** [`state/8-3.json`](state/8-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/8-3-youtube-upload-ai-disclosure` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want video tự đăng lên YouTube với đầy đủ metadata và khai báo AI, so that đúng chính sách nền tảng và không bao giờ bị gỡ vì thiếu khai báo.

## Why
FR-12 + rủi ro "AI content bị giảm reach/gỡ" — disclosure bắt buộc (BR-1 không có nút tắt) là quyết định tuân thủ, không phải tuỳ chọn.

## Scope
**In:** resumable upload; metadata (title/description/tags/category); altered-content (AI) disclosure + madeForKids=false; privacy config (default unlisted); quota guard (đếm units/ngày, chặn trước upload); map lỗi API → tiếng Việt; external_id/url về publishes; attribution BGM nối description (6-5 BR-2).
**Out:** thumbnail tuỳ chỉnh (v1.1); playlist/end-screen (v1.1); Shorts-specific metadata.

## Business Rules
1. Disclosure luôn bật — không config tắt (compliance).
2. Quota không đủ (~1600 units) → chặn trước upload + giờ reset (07:00 PT); không thử-rồi-fail.
3. Upload đứt → resume theo session (không tải lại từ đầu).
4. Video >15' hoặc >256GB → chặn capabilities (không xảy ra với v1 nhưng check rẻ).

## Acceptance Criteria
1. **(happy)** Đăng → video unlisted đúng metadata + disclosure (kiểm Studio 1 lần, screenshot vào PR); URL lưu + mở được.
2. **(biên/BR-3)** Ngắt mạng giữa upload (mock) → resume tiếp session, không upload lại phần đã gửi.
3. **(lỗi/BR-2)** Quota còn 500 → chặn + "reset 07:00 PT"; 403 lạ → failed message dịch + retry.
4. **(BGM)** Track cần ghi công → description chứa attribution.
5. **(BR-1)** Không tồn tại đường tắt disclosure (review code + không có config).

## Data & API
publishes.external_id/url; cột `quota_used_today` mới. Contract change: nhẹ (cột) — ghi migration.

## Decisions already locked
- ⏳ Category mặc định "Science & Technology".

## Execution Steps

Work these in order. Update `state/8-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: `quota_used_today` migration
- **Files:** `alembic/versions/{rev}_add_quota_used_today.py` (or project's migration tool equivalent), `docs/specs/database-schema.md` update
- **Do:** add `quota_used_today` column to the relevant table (per epic doc: counter in `api_keys` usage or a dedicated quota table — confirm against `docs/specs/database-schema.md`'s existing shape before adding a synonym column, per `rules/naming.md`); this is a "đổi contract" change — update `docs/specs/database-schema.md` in the same PR (per `rules/documentation.md`).
- **Verify:** run the migration against a scratch DB → applies cleanly; `alembic downgrade -1` → reverts cleanly.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add alembic/ docs/specs/database-schema.md && git commit -m "feat(publish): 8-3 add quota_used_today column"` → `git push`

### Step 2: YouTube publish adapter — resumable upload + metadata
- **Files:** `backend/app/adapters/publish/youtube.py`
- **Do:** implement `@register_publish("youtube") class YouTubeAdapter(PublishAdapter)` per [patterns/provider-adapter.md](../patterns/provider-adapter.md); resumable upload session (BR-3: on network interruption, resume from the session, don't re-upload sent bytes); metadata mapping (title/description/tags/category, default category "Science & Technology" per locked decision); privacy default `unlisted` (8-2 decision); `madeForKids=false` always set.
- **Verify:** `mypy backend/app/adapters/publish/youtube.py --strict` → 0 errors.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/publish/youtube.py && git commit -m "feat(publish): 8-3 add YouTube adapter resumable upload"` → `git push`

### Step 3: AI disclosure (BR-1, no bypass) + quota guard (BR-2)
- **Files:** `backend/app/adapters/publish/youtube.py`, `backend/app/services/youtube_quota_service.py`
- **Do:** altered-content (AI) disclosure flag always sent with the upload request — no config path exists to disable it (BR-1, review the diff yourself to confirm zero conditional path); quota guard checks `quota_used_today` against the ~1600-unit budget **before** calling the API (BR-2: block-before-attempt, not try-then-fail), surfacing the 07:00 PT reset time when blocked.
- **Verify:** `pytest backend/tests/unit/adapters/publish/test_youtube_disclosure.py -q` → passes, including a static-analysis-style test asserting no env var/config key can suppress disclosure.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/publish/youtube.py backend/app/services/youtube_quota_service.py && git commit -m "feat(publish): 8-3 add mandatory AI disclosure + quota guard"` → `git push`

### Step 4: Error mapping + BGM attribution + external_id/url
- **Files:** `backend/app/adapters/publish/youtube.py`, `backend/app/services/publish_service.py`
- **Do:** map YouTube API error codes (401/403 quota/403 other/500) to Vietnamese user-facing messages (per `docs/glossary.md` terms); write `external_id`/`url` back to `publishes` on success; when the video's BGM track requires attribution (6-5 BR-2), append the attribution text to the YouTube description before upload.
- **Verify:** `pytest backend/tests/unit/adapters/publish/test_youtube_errors.py -q` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/publish/youtube.py backend/app/services/publish_service.py && git commit -m "feat(publish): 8-3 add error mapping + BGM attribution"` → `git push`

### Step 5: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/adapters/publish/test_youtube.py`, `backend/tests/integration/api/test_publish_youtube.py`
- **Do:** mock YouTube API branches per Test Notes (200/401/403 quota/500/resume) with `respx`; one test per AC (AC1 happy metadata+disclosure — real Studio check done manually once with a screenshot attached to the PR, not automated; AC2 BR-3 resume-without-reupload; AC3 BR-2 quota-block-with-reset-time + 403-translated-retry; AC4 BGM attribution in description; AC5 BR-1 no-disclosure-bypass).
- **Verify:** `pytest backend/tests/unit/adapters/publish backend/tests/integration/api/test_publish_youtube.py -q` → all AC-mapped tests pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests/ && git commit -m "test(publish): 8-3 cover all acceptance criteria"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock YouTube API đủ nhánh (200/401/403quota/500/resume); upload thật 1 video test kiểm tay.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/8-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/8-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
