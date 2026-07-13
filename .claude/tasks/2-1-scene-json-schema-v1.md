# Task 2-1: Scene JSON schema v1 — Pydantic + export + Zod

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 1-1 (parallel with Track A) · **FR:** FR-08, AR-3
**State file:** [`state/2-1.json`](state/2-1.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/2-1-scene-json-schema-v1` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a developer, I want một nguồn schema duy nhất mà backend, frontend và Remotion cùng dùng, so that ba bên không bao giờ lệch contract trung tâm của hệ thống.

## Why
Scene JSON là contract quan trọng nhất ([decisions/0004-scene-json-contract.md](../decisions/0004-scene-json-contract.md)): preview, cache, render, versioning, editor đều đứng trên nó.

## Scope
**In:** Pydantic models đầy đủ theo `docs/specs/scene-json-schema.md` (SemanticStoryboard strict riêng; VideoProject/Scene resolved có format + platform_profile; 5 layout/các type §3); validator ngoài-schema §5 hai chế độ `auto_fix`/`strict`; `make gen-scene-schema` (JSON Schema → Zod — Zod là schema prop chính thức của `<Composition>` Remotion, xem `docs/specs/remotion-integration.md` §2.1); fixtures share pytest/vitest (hợp lệ mỗi layout + ≥3 lỗi); CI gate diff; hàm canonical hash.
**Out:** schema v2 elements (chart/video/karaoke); migration runner; UI form (5-1 tiêu thụ).

## Business Rules
1. Canonical hash: sort keys, UTF-8 NFC, bỏ `scene_number` — đổi thứ tự cảnh không phá cache.
2. `auto_fix` chỉ sửa vi phạm "cắt được" (thừa phần tử, duration lệch, thiếu default) + log warning; kiểu dữ liệu sai → lỗi kể cả auto_fix.
3. Mọi lỗi strict có `field_path` máy-đọc-được để FE map inline.
4. Fixtures là contract test hai chiều — thêm rule validator mới bắt buộc kèm fixture fail tương ứng.
5. `SemanticStoryboard` dùng `extra="forbid"`: payload LLM có `layout`, `position`, `font`, `animation`, `camera`, `transition` hoặc field không khai báo phải fail trước resolver; resolved Scene không được dùng làm model parse output LLM.

## Acceptance Criteria
1. **(happy)** Fixture hợp lệ pass pytest+vitest; fixture lỗi fail cả hai cùng field_path.
2. **(biên/BR-2)** 6 texts vào TextFocus (max 3): auto_fix cắt còn 3 + warning; strict → 422 `texts`.
3. **(biên/BR-1)** Đổi scene_number/thứ tự key → hash không đổi; đổi 1 ký tự content → hash đổi.
4. **(lỗi)** `duration_ms: "abc"` → lỗi kiểu cả 2 chế độ.
5. **(CI)** Sửa Pydantic không chạy gen → CI fail đúng thông điệp.

## Data & API
File sinh: `packages/remotion-templates/schema/scene-1.0.0.json` + `schema.ts` (Zod) commit vào repo. Contract change: khởi tạo contract trung tâm.

## Decisions already locked
- 11 layout class v1, PascalCase canonical (Hero/TextFocus/MediaFull/MediaText/Comparison/BigNumber/Chart/VersusTable/List/Quote/Code) — thêm class = minor version + preset json; class do Classifier chọn, không phải AI. See [rules/naming.md](../rules/naming.md), [anti-patterns/layout-name-drift.md](../anti-patterns/layout-name-drift.md).
- Số liệu motion chuyển thể từ taste-skill (`docs/specs/video-taste.md`), hiệu chỉnh nhịp web→video (chậm hơn ~1.5×).

## Execution Steps

Work these in order. Update `state/2-1.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Pydantic models — VideoProject/Scene/11 layout classes/element types
- **Files:** `backend/app/schemas/scene.py`
- **Do:** Implement Pydantic models per `docs/specs/scene-json-schema.md` §3: strict `SemanticStoryboard` (all models `extra="forbid"`), resolved `VideoProject` (including `platform_profile`) and `Scene`, the 5 base layout classes shipped in this story (`Hero`, `TextFocus`, `MediaFull`, `MediaText`, `Comparison` — the remaining 6 data/structure classes are 2-6's scope, but the 11-class enum/discriminator itself must exist now per `rules/naming.md` PascalCase list so 2-6 only adds variants, not renames), and the shared element types (`heading`, `body`, `media_intent`, etc., snake_case per `rules/naming.md`). Use a discriminated union keyed on layout class name. No `layout`/`position`/`animation` field anywhere in the AI-facing Semantic Storyboard — see `rules/type-safety.md` and `anti-patterns/ai-chooses-layout.md`.
- **Verify:** `python -c "from app.schemas.scene import VideoProject, Scene; print('ok')"` → prints `ok`, no import error.
- **On failure:** transient (missing dep) → `pip install`/`uv sync` and retry, up to 3×, log attempt in state file; logic/type error → stop retrying, invoke `systematic-debugging` skill; still failing after 3 → mark step + task `blocked` in state file with `blocked_reason`, note in `memory/project-memory.md` Open Questions, move to a different unblocked task.
- **Commit:** `git add backend/app/schemas/scene.py && git commit -m "feat(scene): 2-1 add Pydantic models for Scene JSON v1.0.0"` → `git push`

### Step 2: Canonical hash function (BR-1)
- **Files:** `backend/app/schemas/scene.py` or `backend/app/services/scene_hash.py`
- **Do:** Implement `canonical_hash(scene_or_project) -> str`: sort keys, normalize to UTF-8 NFC, drop `scene_number` before hashing (so reordering scenes doesn't invalidate render cache, per BR-1 and `rules/performance.md` cache-key note). Use sha256 as the underlying digest to stay consistent with the render `cache_key` convention already fixed in `rules/performance.md`.
- **Verify:** `python -c "from app.schemas.scene import canonical_hash; ..."` quick smoke script confirming two permutations of scene order hash identically and a 1-character content change changes the hash → both assertions pass, exit 0.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/schemas/scene.py && git commit -m "feat(scene): 2-1 add canonical hash (BR-1: order-independent, scene_number-independent)"` → `git push`

### Step 3: Validator — auto_fix / strict modes (BR-2, BR-3)
- **Files:** `backend/app/schemas/scene.py`, `backend/app/services/scene_validator.py`
- **Do:** Implement the out-of-schema validator per `docs/specs/scene-json-schema.md` §5, two modes: `auto_fix` (trims "cắt được" violations — e.g. excess elements beyond a layout's max, duration drift, missing defaults — and logs a warning; type mismatches still error even in `auto_fix`, per BR-2) and `strict` (rejects with HTTP 422 and a machine-readable `field_path` per BR-3, so the frontend can map the error inline). Raise a typed exception carrying `field_path`, not a bare `ValueError`.
- **Verify:** targeted smoke test: `TextFocus` with 6 `texts` (max 3) in `auto_fix` → resulting scene has 3 texts + a warning logged; same input in `strict` → raises with `field_path == "texts"`. Both pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/app/schemas/scene.py backend/app/services/scene_validator.py && git commit -m "feat(scene): 2-1 add auto_fix/strict validator (BR-2, BR-3)"` → `git push`

### Step 4: JSON Schema export + Zod codegen (`make gen-scene-schema`)
- **Files:** `Makefile` (or `backend/Makefile` per actual scaffold), `packages/remotion-templates/schema/scene-1.0.0.json`, `packages/remotion-templates/src/schema.ts`
- **Do:** Add/confirm the `make gen-scene-schema` target: exports Pydantic → JSON Schema → commits `packages/remotion-templates/schema/scene-1.0.0.json`, then regenerates `packages/remotion-templates/src/schema.ts` (Zod) from that JSON Schema. Per `rules/type-safety.md`, `schema.ts` is generated, never hand-edited. This Zod schema is the official `schema` prop for Remotion's `<Composition>` (`docs/specs/remotion-integration.md` §2.1) — 2-2 depends on it existing.
- **Verify:** `make gen-scene-schema` → exits 0, `git diff --stat` shows both generated files changed/created, no manual edits needed after running it twice in a row (idempotent).
- **On failure:** same policy as Step 1.
- **Commit:** `git add Makefile packages/remotion-templates/schema/scene-1.0.0.json packages/remotion-templates/src/schema.ts && git commit -m "feat(scene): 2-1 add make gen-scene-schema (Pydantic -> JSON Schema -> Zod)"` → `git push`

### Step 5: CI gate — fail if schema changed without regenerating
- **Files:** CI workflow config (per `context/build-process.md` conventions once scaffolded), `Makefile`
- **Do:** Add a CI check that runs `make gen-scene-schema` and fails the build with a clear message if it produces a diff (i.e., someone edited `backend/app/schemas/scene.py` without regenerating `schema-1.0.0.json`/`schema.ts`). This satisfies AC-5.
- **Verify:** simulate locally — hand-edit `backend/app/schemas/scene.py`, run the CI check script/command without regenerating → it fails with a message naming the stale files; run `make gen-scene-schema` then rerun the check → passes.
- **On failure:** same policy as Step 1.
- **Commit:** `git add .` (CI config + any Makefile changes) `&& git commit -m "feat(scene): 2-1 add CI gate for scene schema codegen drift"` → `git push`

### Step 6: Shared fixtures (pytest + vitest, valid + ≥3 invalid) (BR-4)
- **Files:** `packages/remotion-templates/schema/fixtures/*.json`, `backend/tests/unit/schemas/test_scene_fixtures.py` (or `backend/tests/unit/schemas/...` per actual scaffold path), `packages/remotion-templates/src/__tests__/schema.fixtures.test.ts`
- **Do:** Create one valid fixture per shipped layout class (the 5 in this story) plus at least 3 invalid fixtures (per BR-4, each new validator rule needs a matching fail fixture): wrong type (`duration_ms: "abc"`), TextFocus with 6 texts (strict mode), and a missing-required-field case. Both pytest and vitest load the same fixture files (per `rules/testing.md` — provider/schema tests share fixtures, not forked).
- **Verify:** `pytest backend/tests/unit/schemas/test_scene_fixtures.py -v` → all pass; `npx vitest run schema.fixtures.test.ts` → all pass; both report the same `field_path` for each invalid fixture.
- **On failure:** same policy as Step 1.
- **Commit:** `git add packages/remotion-templates/schema/fixtures backend/tests/unit/schemas packages/remotion-templates/src/__tests__ && git commit -m "test(scene): 2-1 add shared valid/invalid fixtures for pytest+vitest (BR-4)"` → `git push`

### Step 7: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `backend/tests/unit/schemas/test_scene_hash.py`, `backend/tests/unit/schemas/test_scene_validator.py` (mirror module under test, per `rules/folder-structure.md`)
- **Do:** One test per Acceptance Criterion: AC-1 (fixture pass/fail parity across pytest+vitest, already covered by Step 6 — assert here explicitly), AC-2 (auto_fix trims to 3 + warning; strict → 422 on `texts`), AC-3 (hash property test: hash a scene, shuffle scene order + change `scene_number`, assert hash unchanged; change one character of content, assert hash changes — use `hypothesis` or manual permutations for the property test per Test Notes), AC-4 (`duration_ms: "abc"` errors in both modes), AC-5 (covered by Step 5's CI gate test).
- **Verify:** `pytest backend/tests/unit/schemas/ -v` → all AC-mapped tests pass, exit 0.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests/unit/schemas && git commit -m "test(scene): 2-1 cover all acceptance criteria (AC-1..AC-5)"` → `git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + từng rule §5 một unit test; property test hash (random permutation không đổi hash).

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/2-1.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/2-1.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
