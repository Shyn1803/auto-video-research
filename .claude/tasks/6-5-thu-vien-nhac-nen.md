# Task 6-5: Thư viện nhạc nền có giấy phép

**Points:** 2đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 5-5, FR-20 infra · **FR:** FR-10, FR-20
**State file:** [`state/6-5.json`](state/6-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/6-5-thu-vien-nhac-nen` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want chọn nhạc nền từ thư viện có sẵn giấy phép, so that video có nhạc hợp không khí mà không bao giờ lo gậy bản quyền.

## Why
Gap: Timeline có BGM picker nhưng không ai nạp nhạc. Bản quyền nhạc là rủi ro bị gỡ video/claim doanh thu cao nhất trên YouTube.

## Scope
**In:** seed ~10 track (Pixabay Music/YouTube Audio Library — tải thủ công, license đầy đủ) vào assets(audio); API list BGM; admin upload track (license chọn từ danh sách chuẩn, bắt buộc); preview nghe trong picker (5-5).
**Out:** tìm nhạc theo mood bằng AI (v1.1); creator upload nhạc (admin only — rủi ro license); fade tuỳ chỉnh per-track.

## Business Rules
1. Track không license record → không xuất hiện trong picker (query-level filter).
2. License yêu cầu attribution → dòng ghi công tự nối vào description khi tải/đăng (6-3 BR-4, 8-3).
3. Admin upload: license + source_url bắt buộc; loại file mp3/m4a ≤15MB.

## Acceptance Criteria
1. **(happy)** Picker hiện ≥10 track nghe thử được; chọn → render có nhạc đúng volume/fade.
2. **(biên/BR-2)** Track cần ghi công → description có attribution.
3. **(lỗi/BR-3)** Upload thiếu license → 400 đúng field.
4. **(quyền)** Creator không upload được track.

## Data & API
Bảng: assets (media_type=audio). Endpoints: `GET /assets/bgm` (mới) + admin upload (dùng chung 5-3 upload) → cập nhật api-spec §6. Contract change: **có**.

## Decisions already locked
- 10 track seed do BA chọn đa dạng mood (tech/calm/upbeat) — danh sách trong PR.

## Execution Steps

Work these in order. Update `state/6-5.json` after **every** step. Contract change flagged in Data & API — the `GET /assets/bgm` endpoint must land alongside an `docs/specs/api-spec.md` §6 update in the same PR (per [rules/documentation.md](../rules/documentation.md)).

### Step 1: Resolve seed-track storage + acquire the 10 tracks
- **Files:** `scripts/seed/bgm_tracks.py`, a checksum manifest (e.g. `scripts/seed/bgm_tracks.json`)
- **Do:** this closes the DoD's open `⏳ chọn cách lưu` decision — pick a download-script-plus-checksum-manifest approach (not Git LFS: avoids LFS bandwidth/setup dependency and keeps binaries out of the repo) and record the choice in `state/6-5.json` `decisions[]` per [rules/autonomy-policy.md](../rules/autonomy-policy.md) (reversible/locally-scoped). Curate ~10 Pixabay Music/YouTube Audio Library tracks spanning tech/calm/upbeat moods, each with full license info; write a script that downloads them into dev-fixture storage and records checksums in a committed manifest.
- **Verify:** `python scripts/seed/bgm_tracks.py --dry-run` → lists 10 tracks with checksums, no network write.
- **On failure:** transient (network) → retry 3×; logic/config → `systematic-debugging` skill; still failing → mark `blocked`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add scripts/seed/bgm_tracks.py scripts/seed/bgm_tracks.json && git commit -m "feat(bgm): 6-5 seed script for 10 licensed BGM tracks" && git push`

### Step 2: assets(audio) rows with mandatory license metadata (BR-1, BR-3 shape)
- **Files:** `backend/app/models/assets.py`, `backend/alembic/versions/` (migration only if the `media_type` enum needs an `audio` value added)
- **Do:** seed script inserts `assets` rows with `media_type=audio`, and the mandatory `license`, `source_url`, `attribution_required`, `provider` fields (per [rules/security.md](../rules/security.md) "every asset requires..."); reject/skip any track missing a required field rather than inserting a partial row.
- **Verify:** `cd backend && pytest backend/tests/unit/services/test_bgm_seed.py::test_seed_inserts_10_tracks_with_license -v` → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(bgm): 6-5 assets(audio) rows with mandatory license fields"`

### Step 3: `GET /assets/bgm` endpoint (contract change)
- **Files:** `backend/app/api/assets.py`, `docs/specs/api-spec.md` §6 (update in the **same PR** — contract change)
- **Do:** new endpoint lists only `media_type=audio` assets with a non-null license record — filtered at the query level (BR-1), not filtered in application code after fetch; response includes a preview URL for a 10s listen.
- **Verify:** `pytest backend/tests/integration/api/test_assets_bgm.py::test_list_excludes_no_license_tracks -v` → passes (BR-1).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(bgm): 6-5 GET /assets/bgm endpoint (contract change, api-spec updated)"`

### Step 4: Admin upload endpoint (BR-3)
- **Files:** `backend/app/api/assets.py` (extend the 5-3 upload path with an admin-scoped variant), RBAC check reusing 1-2's middleware
- **Do:** admin-only upload requires a license chosen from a fixed standard list + `source_url`; reject non-mp3/m4a file types or files >15MB with a 400 naming the specific invalid field; a Creator-role request gets 403.
- **Verify:** `pytest backend/tests/integration/api/test_assets_bgm.py::test_upload_missing_license_400 backend/tests/integration/api/test_assets_bgm.py::test_upload_creator_403 -v` → both pass (AC-3, AC-4/quyền).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(bgm): 6-5 admin-only track upload with license validation (BR-3)"`

### Step 5: Picker UI wiring + preview playback
- **Files:** `frontend/src/components/finishing/BgmPicker.tsx` (Màn Hoàn thiện, 5-5 integration)
- **Do:** list ≥10 tracks with a 10s preview button + license badge; empty state "chưa có nhạc — admin thêm tại Quản trị"; wire the selected track into the project/scene BGM field consumed by 6-2's ffmpeg merge step.
- **Verify:** exercise in a real running browser per [rules/testing.md](../rules/testing.md) — load the Hoàn thiện screen against seeded fixture data, preview and select a track.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(bgm): 6-5 picker UI with preview + empty state"`

### Step 6: Attribution auto-append (BR-2)
- **Files:** `backend/app/services/publish_metadata.py` (shared metadata-assembly service consumed by 6-3's copy panel and 8-3's publish)
- **Do:** when the selected track's license requires attribution, auto-append the attribution line to the video description string at the point 6-3/8-3 read it.
- **Verify:** `pytest backend/tests/unit/services/test_publish_metadata.py::test_attribution_appended_when_required -v` → passes (AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(bgm): 6-5 auto-append license attribution to description (BR-2)"`

### Step 7: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/...`, `backend/tests/integration/...`, real-browser check log for the picker
- **Do:** one test per Acceptance Criterion (1–4); mock HTTP with `respx` per [rules/testing.md](../rules/testing.md); confirm the seed-storage decision from Step 1 is recorded as resolved in this task's Retrospective, not left as an open `⏳`.
- **Verify:** `cd backend && pytest tests/unit tests/integration -k bgm -v` → all pass; frontend picker exercised in a real browser.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "test(bgm): 6-5 full AC coverage for BGM library"`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + seed track là tài sản repo (resolved in Step 1: download script + checksum manifest, not Git LFS).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/6-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/6-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
