# Task 6-1: Node Produce — TTS batch + asset resolve

**Points:** 5đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 4-6, 2-4, 3-2 · **FR:** FR-19, FR-20
**State file:** [`state/6-1.json`](state/6-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/6-1-node-produce` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a system, I want chuẩn bị đủ giọng đọc và ảnh có giấy phép cho mọi cảnh trước khi render, so that render không bao giờ chờ media và video không bao giờ dính ảnh mờ bản quyền.

## Why
Node "hậu cần" của pipeline — chậm nhất và dễ lỗi nhất. Thiết kế "lỗi cục bộ không giết run" (BR-3) là điều kiện để Mode 1 chạy đêm không người trông.

## Scope
**In:** TTS mọi cảnh song song bounded (semaphore/engine); điền `audio` vào scene JSON + validator nâng duration; asset resolve: `media_intent.query_vi` → prompt `asset.query` → asset chain (stock → SD local nếu active) → MinIO + license; thiếu → placeholder theme + cờ `asset_missing`; idempotent theo hash (audio + asset).
**Out:** BGM ingest (6-5); render (6-2); sinh ảnh nâng cao (chain lo).

## Business Rules
1. Chạy lại chỉ xử lý cảnh thiếu/stale (audio hash đổi khi voice text/giọng đổi — 5-2 BR-3).
2. Asset không rõ license → từ chối → provider kế → cuối cùng placeholder. Không bao giờ dùng ảnh thiếu license (see [rules/security.md](../rules/security.md)).
3. Lỗi 1 cảnh → cờ lỗi cảnh đó, cảnh khác tiếp tục; node fail chỉ khi >50% cảnh lỗi.
4. Ảnh stock chọn theo orientation khớp format project (dọc cho 9:16).
5. Audio produce xong → duration cảnh tự nâng nếu thiếu — ghi vào scene JSON version mới.
6. **(Motion pass-2)** sau TTS, gọi Motion Planner re-resolve `motion_plan` bằng word-timestamps thật (stat count-up kết thúc đúng lúc đọc xong số); chỉ cập nhật motion_plan — layout không đổi; deterministic, không token.

## Acceptance Criteria
1. **(happy)** 10 cảnh, chain pexels → đủ audio+timestamps; ≥8 ảnh thật đúng orientation; thiếu → placeholder + cờ.
2. **(biên/BR-1)** Run lần 2 → 0 call TTS/stock; sửa voice 1 cảnh → chỉ cảnh đó re-TTS.
3. **(biên/BR-3)** Mock TTS fail cảnh 3 → 9 cảnh xong, cảnh 3 cờ lỗi + retry riêng OK.
4. **(lỗi)** Mọi asset provider chết → toàn placeholder + cờ; run hoàn thành; UI cảnh báo tổng.
5. **(BR-2)** Provider trả ảnh không license (mock) → bị loại, thử provider kế.

## Data & API
Bảng: assets (ghi mới), scenes (update scene_json + hash). Events: step.progress. Contract change: không (schema audio field đã spec §3.4).

## Decisions already locked
- ⏳ Placeholder = nền gradient theme + icon chủ đề — video vẫn dùng được khi thiếu stock.
- ⏳ Ngưỡng fail node 50%.

## Execution Steps

Work these in order. Update `state/6-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next.

### Step 1: Scaffold the node skeleton
- **Files:** `backend/app/pipeline/nodes/produce.py`, `backend/app/pipeline/graph.py`
- **Do:** implement `run(input: ProduceInput, ctx: RunContext) -> ProduceOutput` (both Pydantic models) per [patterns/langgraph-pipeline-node.md](../patterns/langgraph-pipeline-node.md); register the node in `graph.py` after the `storyboard` node produced by 4-6, before `render` (6-2). Node must not assume Mode 1 vs Mode 2 — gate behavior is orchestration, not node logic.
- **Verify:** `cd backend && python -c "from app.pipeline.graph import build_graph; build_graph()"` → exit 0, no import/registration errors.
- **On failure:** transient (import/env) → retry 3× with backoff; logic error → invoke `systematic-debugging` skill; still failing → mark `blocked` in state file, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/pipeline/nodes/produce.py backend/app/pipeline/graph.py && git commit -m "feat(pipeline): 6-1 scaffold produce node" && git push`

### Step 2: TTS batch, bounded concurrency
- **Files:** `backend/app/pipeline/nodes/produce.py`, uses `backend/app/adapters/tts/*` (2-4) via the chain router (3-2)
- **Do:** call every scene's TTS through the chain router concurrently, bounded by an `asyncio.Semaphore` sized from config (never read env directly in the node — config via `ProviderSettings` per [rules/code-style.md](../rules/code-style.md)); write the result (audio URL + word-timestamps) into the scene JSON `audio` field per the already-spec'd §3.4 shape — no new field, no contract change.
- **Verify:** `cd backend && pytest backend/tests/unit/pipeline/test_produce_node.py::test_tts_semaphore_bound -v` → passes, asserts concurrent in-flight calls never exceed the configured bound.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(pipeline): 6-1 TTS batch with bounded concurrency"`

### Step 3: Idempotency by hash (BR-1)
- **Files:** `backend/app/pipeline/nodes/produce.py`, reuse the scene-hash helper from 5-2 BR-3
- **Do:** compute an audio hash from voice text + voice params per scene; skip the TTS call entirely when the stored hash still matches; only scenes whose voice text/voice params changed get re-synthesized.
- **Verify:** `pytest backend/tests/unit/pipeline/test_produce_node.py::test_rerun_zero_tts_calls_when_unchanged backend/tests/unit/pipeline/test_produce_node.py::test_single_scene_retts_on_voice_change -v` → both pass (AC-2).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(pipeline): 6-1 idempotent TTS via audio hash (BR-1)"`

### Step 4: Asset resolve chain + license enforcement (BR-2, BR-4)
- **Files:** `backend/app/adapters/assetstock/*`, `backend/app/pipeline/nodes/produce.py`
- **Do:** for each scene, build `asset.query` from `media_intent.query_vi`; call the asset chain router (stock providers, then local Stable Diffusion if active per `ALLOW_PAID`/local-reachable rules) through the adapter pattern ([patterns/provider-adapter.md](../patterns/provider-adapter.md)) — never call a provider SDK directly from the node. Reject any candidate missing `license`/`source_url`/`attribution_required`/`provider` (see [rules/security.md](../rules/security.md)) and fall through to the next provider; select by orientation matching the project format (vertical for 9:16). Chain exhaustion → placeholder theme (gradient + topic icon, per Decisions already locked) + `asset_missing` flag, never an unlicensed image.
- **Verify:** `pytest backend/tests/unit/pipeline/test_produce_node.py::test_asset_license_rejection backend/tests/unit/pipeline/test_produce_node.py::test_asset_orientation_match backend/tests/unit/pipeline/test_produce_node.py::test_all_providers_dead_placeholder -v` → all pass (AC-1, AC-4, AC-5).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(pipeline): 6-1 asset resolve chain with license gate (BR-2/BR-4)"`

### Step 5: Duration auto-raise + Motion Planner pass-2 (BR-5, BR-6)
- **Files:** `backend/app/pipeline/nodes/produce.py`, versioning per [patterns/scene-versioning.md](../patterns/scene-versioning.md), Motion Planner module from 4-6
- **Do:** after audio is produced, run the scene validator so scene duration auto-raises if the real audio duration exceeds the current value; re-invoke the deterministic Motion Planner (no LLM) with real word-timestamps for pass-2 (`motion_plan` only — layout must not change, per [context/architecture.md](../context/architecture.md) Layout Engine boundary); persist as a new scene JSON version.
- **Verify:** `pytest backend/tests/unit/pipeline/test_produce_node.py::test_duration_autoraise backend/tests/unit/pipeline/test_produce_node.py::test_motion_plan_pass2_layout_unchanged -v` → both pass.
- **On failure:** logic error here is high-blast-radius (Layout Engine boundary) — do not blind-retry, invoke `systematic-debugging` skill immediately on first failure.
- **Commit:** `git commit -m "feat(pipeline): 6-1 duration auto-raise + motion_plan pass-2 (BR-5/BR-6)"`

### Step 6: Local-error containment, node-level fail threshold (BR-3)
- **Files:** `backend/app/pipeline/nodes/produce.py`
- **Do:** wrap each scene's TTS/asset work so a scene-level exception sets an error flag on that scene and processing continues for the rest; the node itself only raises/fails when >50% of scenes error (locked default per Decisions already locked, ⏳ still PO-pending — proceed with 50%, record the judgment call in `state/6-1.json` `decisions[]` per [rules/autonomy-policy.md](../rules/autonomy-policy.md)).
- **Verify:** `pytest backend/tests/unit/pipeline/test_produce_node.py::test_partial_scene_failure_continues -v` (mock TTS fail on scene 3 of 10; 9 scenes complete, scene 3 flagged + retryable) → passes (AC-3).
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "feat(pipeline): 6-1 local error containment + 50% fail threshold (BR-3)"`

### Step 7: Wire up tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/pipeline/test_produce_node.py`, `backend/tests/integration/pipeline/test_produce_node_integration.py`
- **Do:** one test per Acceptance Criterion (1–5); mock HTTP with `respx` for every adapter per [rules/testing.md](../rules/testing.md); diverse `media_intent` fixtures (concrete/abstract, varying `media_hint`) per the epic's Test Notes.
- **Verify:** `cd backend && pytest backend/tests/unit/pipeline/test_produce_node.py backend/tests/integration/pipeline/test_produce_node_integration.py -v` → all pass, zero live network calls, zero GPU/Ollama dependency.
- **On failure:** same policy as Step 1.
- **Commit:** `git commit -m "test(pipeline): 6-1 full AC coverage for produce node"`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + semaphore test (không vượt bound); idempotency test là trọng tâm.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/6-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/6-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
