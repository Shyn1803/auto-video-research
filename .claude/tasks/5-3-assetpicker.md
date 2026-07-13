# Task 5-3: AssetPicker — đổi ảnh 3 nguồn

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1, 3-2 · **FR:** FR-20
**State file:** [`state/5-3.json`](state/5-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/5-3-assetpicker` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want đổi ảnh minh hoạ từ kho dự án, máy tính, hoặc kho stock, so that cảnh có hình đúng ý mà mọi ảnh đều sạch bản quyền.

## Why
FR-20 phía user. "Mọi đường ra là asset_id có license" là hàng rào pháp lý — UI này là nơi duy nhất user đưa ảnh vào hệ thống. See [anti-patterns/render-worker-external-fetch.md](../anti-patterns/render-worker-external-fetch.md).

## Scope
**In:** modal 3 tab (Asset dự án / Tải lên / Tìm stock — query prefill từ `media_intent.query_vi`, sửa được, kết quả kèm license badge + nguồn); upload validate loại/kích thước, license=user_upload; dedupe hash; chặn URL trần UI+API; nút "Tạo bằng AI" hiện khi image_gen chain active.
**Out:** thư viện asset workspace-level (v1.1); crop/chỉnh ảnh (v1.1 — fit cover đủ).

## Business Rules
1. Kết quả stock hiện license + nguồn **trước** khi chọn.
2. Upload trùng hash → dùng lại asset cũ + thông báo nhẹ.
3. 0 key stock → tab Tìm disabled + giải thích; admin thấy link Quản trị, creator thấy "nhờ admin thêm key".
4. Ảnh chọn từ stock được Asset Worker tải về MinIO trước khi gán (render không fetch ngoài); trong lúc tải hiện "đang lấy ảnh…".

## Acceptance Criteria
1. **(happy)** Tìm "GPU datacenter" → chọn Pexels → asset có license record → Player hiện ảnh.
2. **(biên/BR-2)** Upload ảnh đã tồn tại → tái dùng, không bản ghi mới.
3. **(biên/BR-3)** 0 key → tab Tìm disabled đúng vai trò; 2 tab kia hoạt động.
4. **(bảo mật)** PUT scene chèn url trần qua API → 422.
5. **(BR-4)** Chọn ảnh stock → trạng thái "đang lấy ảnh" → gán asset_id nội bộ (render/preview không gọi pexels).

## Data & API
Endpoints: search stock (mới `GET /assets/search?q=`), upload asset (mới `POST /assets/upload`) → cập nhật api-spec §6. Contract change: **có**.

## Decisions already locked
- ⏳ Upload giới hạn 10MB, jpg/png/webp.

## Execution Steps

Work these in order. Update `state/5-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit.

### Step 1: Backend asset endpoints (contract change)
- **Files:** `backend/app/api/assets.py`, `backend/app/adapters/assetstock/` (existing provider adapters from 3-x), `backend/tests/unit/api/test_assets.py`, `docs/specs/api-spec.md` §6
- **Do:** Add `GET /assets/search?q=` (proxies the asset-stock chain via the adapter pattern — never call a stock provider SDK directly from the router, see `patterns/provider-adapter.md`) and `POST /assets/upload` (validates type/size — 10MB, jpg/png/webp per locked decision — license=`user_upload`, dedupe by hash per BR-2). This is a **đổi contract** change — update `docs/specs/api-spec.md` §6 in the same PR and note it in the **Contract changes** section per `rules/pull-requests.md`.
- **Verify:** `pytest backend/tests/unit/api/test_assets.py -q` (mock HTTP with `respx`, no live network per `rules/testing.md`) → all pass.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/api/assets.py backend/tests/unit/api/test_assets.py docs/specs/api-spec.md && git commit -m "feat(assets): 5-3 search + upload endpoints" && git push`

### Step 2: AssetPicker modal shell — 3 tabs
- **Files:** `frontend/src/components/workspace/AssetPicker.tsx`, `frontend/src/components/workspace/AssetPickerTabs/{ProjectAssetsTab,UploadTab,StockSearchTab}.tsx`
- **Do:** Modal with 3 tabs: Asset dự án (project asset library), Tải lên (upload with validate), Tìm stock (query prefilled from `media_intent.query_vi`, editable). Focus-trap + ESC to close (a11y). Follow `docs/design/wireframe.html` "modal Đổi ảnh".
- **Verify:** `pnpm --filter frontend typecheck` → exit 0.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/AssetPicker.tsx frontend/src/components/workspace/AssetPickerTabs && git commit -m "feat(workspace): 5-3 AssetPicker modal shell, 3 tabs" && git push`

### Step 3: Stock search tab — license badge, BR-1/BR-3
- **Files:** `frontend/src/components/workspace/AssetPickerTabs/StockSearchTab.tsx`, `frontend/tests/unit/components/StockSearchTab.test.tsx`
- **Do:** Results grid shows license + source badge **before** selection (BR-1). If no stock provider key is active (`GET /providers` or chain status), disable this tab with role-appropriate explanation: admin sees a link to Quản trị, creator sees "nhờ admin thêm key" (BR-3). Grid navigable by arrow keys; each image `alt` = description + license.
- **Verify:** `pnpm --filter frontend vitest run StockSearchTab` → covers license-badge-before-select and BR-3 disabled states for both roles.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/AssetPickerTabs/StockSearchTab.tsx frontend/tests/unit/components/StockSearchTab.test.tsx && git commit -m "feat(workspace): 5-3 stock search tab license badges + BR-3 gating" && git push`

### Step 4: Stock selection → Asset Worker fetch → assign (BR-4, security)
- **Files:** `frontend/src/components/workspace/AssetPickerTabs/StockSearchTab.tsx` (selection handler), `backend/app/workers/asset_worker.py` (or existing 3-x/9-x worker if already present), `backend/app/schemas/scene.py` (reject raw URLs)
- **Do:** Selecting a stock image shows "đang lấy ảnh…" while the Asset Worker downloads it to MinIO (render/preview never fetches an external URL — glossary rule 4, `rules/security.md`), then assigns the resulting internal `asset_id`. Add/verify server-side rejection (422) of any raw URL submitted through `PUT scene` (defense in depth, not just UI-side).
- **Verify:** `pytest backend/tests/unit/schemas/test_scene_rejects_raw_url.py -q` and a network-tab assertion in the Playwright test (Step 6) that render/preview never calls the stock provider directly.
- **On failure:** same policy as Step 1; a code path where a render job could reach an attacker-controlled URL is an SSRF bug per `rules/security.md` — treat as high-priority, do not silently skip.
- **Commit:** `git add frontend/src/components/workspace/AssetPickerTabs/StockSearchTab.tsx backend/app/workers backend/app/schemas/scene.py && git commit -m "feat(assets): 5-3 stock fetch via Asset Worker, reject raw URLs" && git push`

### Step 5: Upload tab (dedupe, validation)
- **Files:** `frontend/src/components/workspace/AssetPickerTabs/UploadTab.tsx`, `frontend/tests/unit/components/UploadTab.test.tsx`
- **Do:** File input validates type (jpg/png/webp) and size (≤10MB) client-side before upload; on hash match with an existing asset (BR-2), reuse it and show a light notice instead of creating a duplicate record.
- **Verify:** `pnpm --filter frontend vitest run UploadTab` → covers reject-wrong-type, reject-oversize, dedupe-reuse cases.
- **On failure:** same policy as Step 1.
- **Commit:** `git add frontend/src/components/workspace/AssetPickerTabs/UploadTab.tsx frontend/tests/unit/components/UploadTab.test.tsx && git commit -m "feat(workspace): 5-3 upload tab validation + dedupe" && git push`

### Step 6: Wire up tests + verify all Acceptance Criteria + real browser
- **Files:** `frontend/tests/unit/components/AssetPicker*.test.tsx`, `tests/e2e/asset-picker.spec.ts`
- **Do:** One test per AC above; Playwright flow covering all 3 tabs (Test Notes), plus a permanent URL-security regression test (raw URL through PUT scene → 422, kept as a standing test not a one-off). Then **exercise the feature in a real running browser (dev server)**: open a fixture scene's AssetPicker, search stock, select an image, watch "đang lấy ảnh…" resolve, upload a file, and confirm the Player shows the chosen image with no direct calls to the stock provider visible in the network tab.
- **Verify:** `pnpm --filter frontend test:e2e -- asset-picker` → all AC-mapped tests pass; manual dev-server walkthrough confirms network tab shows no direct pexels/stock calls from render/preview.
- **On failure:** same policy as Step 1.
- **Commit:** `git add tests && git commit -m "test(workspace): 5-3 AC coverage + real-browser verification" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + mock asset chain; Playwright flow 3 tab; test bảo mật URL trần giữ vĩnh viễn.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/5-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/5-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
