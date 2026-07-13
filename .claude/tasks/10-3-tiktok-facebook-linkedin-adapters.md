# Task 10-3: TikTok / Facebook / LinkedIn adapters

**Points:** 5đ · **Epic:** 10 — Release · **Depends:** 8-1 · **FR:** FR-12
**State file:** [`state/10-3.json`](state/10-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/10-3-tiktok-facebook-linkedin-adapters` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want hệ thống sẵn sàng đăng TikTok/Facebook/LinkedIn ngay khi nền tảng duyệt app, so that ngày có key là ngày đăng được, không chờ thêm sprint code.

## Why
FR-12 tầng 3. "Chờ duyệt" nằm ngoài kiểm soát — chiến lược là code xong 100%, kích hoạt = env. Nộp đơn từ tuần 11 chạy song song (đây là công việc PO, ngoài phạm vi code task này).

## Scope
**In:** 3 adapter theo PublishAdapter (8-1): TikTok Content Posting (dọc, AIGC disclosure), Facebook Reels (≤90s), LinkedIn video (ngang ưu tiên); env-activated; UI trạng thái "chờ duyệt nền tảng" + ngày nộp đơn; unit test HTTP mock đủ nhánh; test sandbox tới mức nền tảng cho phép; checklist nộp app review cho PO vào runbook.
**Out:** kích hoạt production (sau release — chỉ env); analytics 3 nền tảng qua API (v1.1 — nhập tay 8-5 đủ).

## Business Rules
1. Adapter code hoàn chỉnh + test — "chờ duyệt" là trạng thái dữ liệu, không phải code dở.
2. Capabilities per-platform vào bảng adapter (TikTok dọc ≤10'; FB Reels ≤90s; LinkedIn ngang ưu tiên) — validate trước đăng (8-1 BR-3 tiêu thụ).
3. App bị từ chối → runbook có mục các bước nộp lại + yêu cầu thường gặp của từng nền tảng.
4. AIGC disclosure TikTok bật cứng như YouTube (8-3 BR-1 pattern).

## Acceptance Criteria
1. **(happy-sandbox)** Key sandbox TikTok → flow chạy tới mức API cho phép; lỗi map rõ.
2. **(biên/BR-2)** Video 16:9 → TikTok chặn + gợi ý bản 9:16; video 2' → FB Reels chặn ≤90s.
3. **(UI)** Chưa duyệt → ⚠ + ngày nộp; thêm key → ✓ không deploy.
4. **(unit/BR-1)** 3 adapter coverage nhánh chính (200/4xx/5xx/quota) bằng mock.
5. **(BR-4)** Không đường tắt AIGC disclosure TikTok.

## Data & API
3 adapter + capabilities config. Contract change: không (PublishAdapter sẵn).

## Decisions already locked
- ⏳ Nộp đơn TikTok + Facebook tuần 11 (việc PO); LinkedIn nộp sau (ưu tiên thấp).

## Execution Steps

Work these in order. Update `state/10-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

Every adapter in this task follows [patterns/provider-adapter.md](../patterns/provider-adapter.md) exactly: implements the `PublishAdapter` base from 8-1, reads config only via `ProviderSettings` (never `os.environ` directly, per `rules/code-style.md`), wraps every external exception into `ProviderError(retryable: bool)`, and ships with a respx-mocked unit test — no exceptions for "adapter code is done but not activatable yet" (BR-1: waiting on platform review is a data state, not unfinished code).

### Step 1: TikTok Content Posting adapter (dolc, AIGC disclosure)
- **Files:** `backend/app/adapters/publish/tiktok.py`, `backend/app/adapters/publish/base.py` (extend only if a genuinely new capability method is needed — reuse existing `PublishAdapter` interface from 8-1 otherwise).
- **Do:** Implement `TikTokPublish(PublishAdapter)` per the adapter skeleton in `dev-guide.md` §3 / `patterns/provider-adapter.md` — `@register_publish("tiktok")`, `available()` checks env-driven sandbox/prod key presence, `publish()` calls TikTok Content Posting API. AIGC disclosure flag hard-enabled with no opt-out, mirroring the 8-3 BR-1 YouTube pattern (BR-4) — do not add a config toggle to disable it.
- **Verify:** unit test with `respx` mocking TikTok API — `available()` false with no key, true with sandbox key; `publish()` happy path 200; AIGC disclosure field asserted present on every request payload with no code path that omits it.
- **On failure:** transient (mock/test infra flake) → retry 3×; logic error → `systematic-debugging`; still failing after 3 → block, log reason (e.g. "TikTok API sandbox docs ambiguous on field X") in `memory/project-memory.md` Open Questions.
- **Commit:** `git add backend/app/adapters/publish/tiktok.py tests/unit && git commit -m "feat(publish): 10-3 TikTok Content Posting adapter with hardcoded AIGC disclosure (BR-4)" && git push`

### Step 2: TikTok capability validation (BR-2: vertical only, ≤10')
- **Files:** `backend/app/adapters/publish/tiktok.py` (capabilities table entry), publish pre-flight validation service (wherever 8-1 BR-3 consumes capability tables).
- **Do:** Add TikTok's capability entry (dọc/vertical only, ≤10 min) to the shared adapter capability table consumed by 8-1 BR-3's pre-publish validation. A 16:9 video attempting to publish to TikTok must be blocked before the API call, with a clear Vietnamese-mapped error suggesting the 9:16 render (ties into 10-1's per-format renders).
- **Verify:** unit test — publish attempt with a 16:9-only project → validation blocks with suggestion message; 9:16 project → passes validation and proceeds to adapter call.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add backend/app/adapters/publish tests/unit && git commit -m "feat(publish): 10-3 TikTok capability validation (vertical-only, ≤10min)" && git push`

### Step 3: Facebook Reels adapter (≤90s cap, BR-2)
- **Files:** `backend/app/adapters/publish/facebook.py`.
- **Do:** Implement `FacebookReelsPublish(PublishAdapter)` following the same skeleton as Step 1. Add its capability entry (≤90s) to the shared table; pre-flight validation blocks any video exceeding 90s with a clear error before the API call.
- **Verify:** unit test with `respx` — happy path 200; a >90s video project → validation blocks with correct error before any HTTP call is made (assert the mock was never hit).
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add backend/app/adapters/publish/facebook.py tests/unit && git commit -m "feat(publish): 10-3 Facebook Reels adapter + ≤90s capability validation (BR-2)" && git push`

### Step 4: LinkedIn video adapter (horizontal-preferred)
- **Files:** `backend/app/adapters/publish/linkedin.py`.
- **Do:** Implement `LinkedInVideoPublish(PublishAdapter)` following the same skeleton, horizontal-preferred capability entry (not a hard block like TikTok/FB — a preference flag consumed by 10-1's auto-format-selection logic).
- **Verify:** unit test with `respx` — happy path 200; format-preference metadata correctly exposed for 10-1's publish auto-select to read.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add backend/app/adapters/publish/linkedin.py tests/unit && git commit -m "feat(publish): 10-3 LinkedIn video adapter (horizontal-preferred)" && git push`

### Step 5: 4xx/5xx/quota branch coverage for all 3 adapters (AC4)
- **Files:** `backend/tests/unit/adapters/publish/tiktok_test.py`, `facebook_test.py`, `linkedin_test.py` (mirror module under test per `rules/folder-structure.md`).
- **Do:** Extend each adapter's test suite to cover the full branch matrix required by AC4: 200 success, 4xx client error (mapped to a clear Vietnamese-language error), 5xx server error (`ProviderError(retryable=True)`), and quota-exceeded response (`QuotaError` per `rules/error-handling.md` routing). No live network calls — `respx` only, per `rules/testing.md`.
- **Verify:** `pytest backend/tests/unit/adapters/publish/ -k "tiktok or facebook or linkedin"` → all branch tests pass for all 3 adapters.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add backend/tests/unit/adapters/publish && git commit -m "test(publish): 10-3 200/4xx/5xx/quota branch coverage for 3 adapters (AC4)" && git push`

### Step 6: "Chờ duyệt nền tảng" UI state + submission date tracking
- **Files:** `src/app/projects/[id]/` publish platform table component (wireframe: bảng nền tảng).
- **Do:** Publish platform table shows ⚠ chờ duyệt + ngày nộp đơn per platform when no key is configured; auto-flips to ✓ once a sandbox/production key is present — this transition must not trigger any deploy action, purely a status read. Errors from the adapters map to Vietnamese-language messages in this UI.
- **Verify:** manual/E2E — platform table with no TikTok key shows ⚠ + date; adding `TIKTOK_API_KEY` env (test env) flips it to ✓ with no side effect on deploy state.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add "src/app/projects/[id]" && git commit -m "feat(ui): 10-3 platform approval-pending state + submission date tracking" && git push`

### Step 7: Runbook — app review submission + rejection retry checklist (BR-3)
- **Files:** `docs/runbook.md` (or wherever the operational runbook lives per `docs/README.md` reading-order table).
- **Do:** Add a runbook section: checklist for submitting each platform's app review (what PO needs, incl. demo video from M4 milestone), plus a "if rejected" subsection per platform with common rejection reasons and resubmission steps (per BR-3). This is documentation the PO acts on, not code — but it's part of this task's DoD.
- **Verify:** manual review — runbook section covers all 3 platforms' submission + rejection-retry steps; linked from `docs/README.md` reading-order table if this is a newly added doc section (per `rules/documentation.md`).
- **On failure:** N/A (documentation step) — if blocked on missing platform-specific info, note the gap explicitly rather than guessing at platform policy.
- **Commit:** `git add docs/runbook.md docs/README.md && git commit -m "docs: 10-3 app review submission + rejection retry checklist (BR-3)" && git push`

### Step 8: Sandbox-level integration check + PR "not verifiable" callout (DoD)
- **Files:** PR description, `backend/tests/integration/publish/` if sandbox credentials are available in CI/dev env.
- **Do:** Run each adapter against sandbox credentials to the extent the platform allows without app approval (AC1 "happy-sandbox"). Explicitly document in the PR which parts could NOT be verified because they require app review approval (per this task's DoD) — do not claim full verification where only mocked coverage exists.
- **Verify:** sandbox run reaches the documented API boundary without unexpected errors; PR description contains an explicit "not verified — pending platform approval" section.
- **On failure:** sandbox unavailable/expired → not a task blocker, document as a known gap; genuine adapter bug found via sandbox → fix and add regression test.
- **Commit:** `git add backend/tests/integration/publish && git commit -m "test(publish): 10-3 sandbox-level integration check, document approval-gated gaps" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock server 3 nền tảng theo tài liệu API công khai; đánh dấu rõ phần "chưa kiểm được vì cần app duyệt" trong PR.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/10-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/10-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
