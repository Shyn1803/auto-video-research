# Task 2-4: TTS adapter + edge-tts tiếng Việt

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 1-1 (parallel with 2-2/2-3) · **FR:** FR-19
**State file:** [`state/2-4.json`](state/2-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/2-4-tts-adapter-edge-tts` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want giọng đọc tiếng Việt tự nhiên kèm timestamp từng từ, so that video có lời thuyết minh và phụ đề khớp mà không cần thu âm.

## Why
Giọng đọc là 50% chất lượng cảm nhận của video tin tức. edge-tts là lựa chọn 0đ tốt nhất cho tiếng Việt nhưng là service không chính thức → adapter interface là bảo hiểm (xem [patterns/provider-adapter.md](../patterns/provider-adapter.md)).

## Scope
**In:** `TTSAdapter` base (available/synthesize/ProviderError); adapter `edge_tts` (2 giọng, speed); MP3 + duration + word timestamps; cache MinIO theo hash(text+voice+speed+engine); mock adapter test; endpoint `POST scenes/{id}/tts-preview`.
**Out:** viXTTS/F5/FPT adapters (chèn theo docs/plan.md §5 khi cần); chuẩn hoá số→chữ (trách nhiệm prompt script 4-5 BR-2).

## Business Rules
1. Text rỗng/toàn khoảng trắng → lỗi validate, không gọi engine.
2. Text >500 ký tự → chia theo câu, ghép audio + nối timestamps offset chính xác.
3. Cache hit không gọi engine (counter đo được).
4. Lỗi engine → `ProviderError(retryable)` — adapter không tự retry (việc của router/node).
5. `voice_id` logic (`female_default`) map engine voice qua config — đổi engine không đổi dữ liệu scene.

## Acceptance Criteria
1. **(happy)** "Xin chào các bạn" nữ 1.0 → MP3 + timestamps từng từ; PO nghe duyệt chất lượng 3 câu mẫu.
2. **(biên/BR-2)** Đoạn 800 ký tự → 1 audio liền mạch, timestamps liên tục đúng offset.
3. **(biên/BR-3)** Gọi lần 2 cùng input → cache hit, engine counter không tăng.
4. **(lỗi/BR-4)** Engine 403 → ProviderError(retryable=true); mock node retry hoạt động.
5. **(BR-5)** Đổi config map voice → cùng scene ra giọng khác, không sửa scene JSON.

## Data & API
Storage: `audio/{project}/{hash}.mp3`. Endpoint mới: tts-preview (api-spec §6). Contract change: không.

## Decisions already locked
- 2 giọng v1 (nữ mặc định) — thêm giọng = config, không task mới.

## Execution Steps

Work these in order. Update `state/2-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: `TTSAdapter` base class + `ProviderError`
- **Files:** `backend/app/adapters/tts/base.py`
- **Do:** Define the `TTSAdapter` abstract base per [patterns/provider-adapter.md](../patterns/provider-adapter.md): `available() -> bool` and `synthesize(text, voice_id, speed) -> TTSResult` (MP3 bytes/path + duration + word timestamps). Adapter methods raise `ProviderError(retryable: bool)` on any external failure per `rules/error-handling.md` — never let a raw HTTP/SDK exception escape the adapter, and the adapter itself never retries (that's the router/node's job per BR-4).
- **Verify:** `python -c "from app.adapters.tts.base import TTSAdapter, ProviderError; print('ok')"` → prints `ok`.
- **On failure:** transient (missing dep) → `uv sync`/`pip install` and retry, up to 3×, log attempt in state file; logic/config error → stop retrying, invoke `systematic-debugging` skill; still failing after 3 → mark step + task `blocked`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/adapters/tts/base.py && git commit -m "feat(tts): 2-4 add TTSAdapter base class + ProviderError contract"` → `git push`

### Step 2: `edge_tts` provider adapter — registration + config (BR-5)
- **Files:** `backend/app/adapters/tts/edge_tts.py`
- **Do:** Implement `EdgeTts(TTSAdapter)` registered via `@register_tts("edge_tts")` per the adapter skeleton in dev-guide.md §3. Support 2 voices (`female_default` → e.g. HoaiMy, plus one more) and a `speed` parameter. `voice_id` like `female_default` maps to the actual engine voice through config (`ProviderSettings`), never hardcoded and never read from `os.environ` directly (per `rules/code-style.md`) — swapping the engine must not require changing scene data (BR-5). Add the `TTS_CHAIN` entry to `.env.example` per `rules/configuration-env.md` (env var stays a complete superset).
- **Verify:** unit test with `respx`-mocked HTTP (per `rules/testing.md` — no live network calls in the suite) confirms `EdgeTts.synthesize(...)` returns MP3 bytes + duration + timestamps for a mocked response, and that changing the voice-map config changes the resolved engine voice without touching scene JSON (AC-5).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/tts/edge_tts.py .env.example && git commit -m "feat(tts): 2-4 add edge_tts adapter (BR-5 config-driven voice map)"` → `git push`

### Step 3: Input validation — reject empty/whitespace-only text (BR-1)
- **Files:** `backend/app/adapters/tts/edge_tts.py` or `backend/app/services/tts_validation.py`
- **Do:** Validate text is non-empty/non-whitespace-only before calling the engine; raise a validation error without making any network call (BR-1).
- **Verify:** unit test calling `synthesize("")` and `synthesize("   ")` → both raise validation error, HTTP mock shows zero calls made.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/adapters/tts/edge_tts.py && git commit -m "feat(tts): 2-4 reject empty/whitespace text before engine call (BR-1)"` → `git push`

### Step 4: Long-text chunking — split by sentence, stitch audio + timestamps (BR-2)
- **Files:** `backend/app/services/tts_chunking.py`
- **Do:** For text >500 characters, split by sentence boundary, synthesize each chunk, concatenate the audio (MP3 stitching) and merge word timestamps with correct cumulative offset per chunk (BR-2).
- **Verify:** unit test with an 800-character Vietnamese fixture (mixed numbers, proper names, loanwords like "GPT", "benchmark" per Test Notes) → single continuous audio output, timestamps monotonically increasing with correct offsets, total duration matches sum of chunk durations (covers AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/tts_chunking.py && git commit -m "feat(tts): 2-4 add >500-char sentence chunking + timestamp offset merge (BR-2)"` → `git push`

### Step 5: MinIO cache by hash(text+voice+speed+engine) (BR-3)
- **Files:** `backend/app/adapters/tts/edge_tts.py`, `backend/app/services/tts_cache.py`
- **Do:** Cache synthesized audio in MinIO keyed by `hash(text + voice_id + speed + engine)` per `docs/backlog/epic-02-scene-remotion.md` Data & API (`audio/{project}/{hash}.mp3`, ARCHITECTURE §6). A cache hit must not call the engine — expose an engine-call counter for testability (BR-3).
- **Verify:** unit test calling `synthesize` twice with identical input → engine-call counter increments only once, second call returns from cache (covers AC-3).
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/services/tts_cache.py backend/app/adapters/tts/edge_tts.py && git commit -m "feat(tts): 2-4 add MinIO cache by content hash (BR-3)"` → `git push`

### Step 6: `POST scenes/{id}/tts-preview` endpoint
- **Files:** `backend/app/api/scenes.py` (or matching router file per `context/folder-structure.md`), `backend/app/services/tts_preview.py`
- **Do:** Add the `tts-preview` endpoint per `docs/api-spec.md` §6 — router calls a service function, no business logic in the router (per `rules/code-style.md`). Endpoint returns a short-lived audio URL. This is not a contract change (Data & API states "Contract change: không") since the endpoint is already documented in api-spec.md.
- **Verify:** integration test posting sample text to the endpoint (with `EdgeTts` mocked) → 200 response with an audio URL and duration.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/api/scenes.py backend/app/services/tts_preview.py && git commit -m "feat(tts): 2-4 add POST scenes/{id}/tts-preview endpoint"` → `git push`

### Step 7: Wire up tests + mock adapter + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/adapters/tts/test_edge_tts.py`, `backend/tests/unit/adapters/tts/test_mock_adapter.py`, `backend/tests/integration/test_tts_preview_endpoint.py`
- **Do:** Add a `MockTts(TTSAdapter)` test double for use by other nodes/tests (per Scope "mock adapter test"). One test per Acceptance Criterion: AC-1 ("Xin chào các bạn" female voice, speed 1.0 → MP3 + word timestamps — flag for manual PO quality approval per 3 sample sentences, don't auto-pass that portion), AC-2 (covered by Step 4), AC-3 (covered by Step 5), AC-4 (mock a 403 from the engine → `ProviderError(retryable=True)`; a mock router-level retry test confirms retry behavior lives outside the adapter), AC-5 (covered by Step 2). Mark any test hitting the real edge-tts service `@external` and schedule it nightly per Test Notes — PRs use the mock only, per `rules/testing.md`.
- **Verify:** `pytest backend/tests/unit/adapters/tts/ backend/tests/integration/test_tts_preview_endpoint.py -v -m "not external"` → all AC-mapped tests pass with zero live network calls.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests/unit/adapters/tts backend/tests/integration/test_tts_preview_endpoint.py && git commit -m "test(tts): 2-4 cover all acceptance criteria (AC-1..AC-5) + mock adapter"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + test edge-tts thật đánh dấu `@external` chạy nightly; PR dùng mock.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/2-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/2-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
