# Task 4-6: Semantic Storyboard + Layout Engine core (Tree → Analysis → Classifier → Resolve)

**Points:** 6đ (PO 2026-07-11: +1đ theo kiến trúc engine) · **Epic:** 4 — Pipeline AI · **Depends:** 4-5, 2-1 · **FR:** FR-07, FR-08
**State file:** [`state/4-6.json`](state/4-6.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-6-semantic-storyboard-layout-engine-core` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.
>
> **This is the highest-scrutiny task in the backlog** ([tasks/README.md](README.md) task→agent ownership table): [architect](../agents/architect.md) reviews for Layout Engine boundary compliance before merge, not just Reviewer. Read [context/architecture.md](../context/architecture.md), `docs/specs/layout-engine.md`, [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md), and [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md) before writing any code here. **AI never chooses layout** — the LLM emits a Semantic Storyboard (content + intent only: component kinds, `beat`, `narration_anchor`); Classifier → Constraint Resolver → Theme → Motion Planner is 100% deterministic non-LLM code operating on that tree. Any prompt schema field named `layout`/`position`/`font`/`animation`/`camera`/`transition` is a violation, not a nitpick — see [rules/code-review.md](../rules/code-review.md).

## User story
As a Content Creator, I want AI chỉ mô tả nội dung và ý đồ từng cảnh còn hệ thống tự quyết bố cục tối ưu, so that phân cảnh luôn hợp lệ, đa dạng và nhất quán — không phụ thuộc "gu chọn layout" thất thường của LLM.

## Why
Kiến trúc Gamma-style ([decisions/0008-layout-engine-deterministic.md](../decisions/0008-layout-engine-deterministic.md), PO 2026-07-11): **AI không chọn layout**. Dựng phần lõi engine: Semantic Storyboard → Scene Tree → Semantic Analysis → Layout Classifier (rule table) → tích hợp Constraint/Theme/Motion resolver (preset từ 2-2/2-6) → Scene JSON resolved. This is the single most-enforced architectural rule in the project — see [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md) and [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md) before writing any code here.

## Scope
**In:** prompt `storyboard.generate` semantic (10 kinds + `beat` + `narration_anchor` — `docs/specs/prompts.md` §7); Pydantic Scene Tree + validate giới hạn (≤8 comp, bullet 3-6, group ≤2); Semantic Analysis (profile + dominant); Layout Classifier theo rule table **config** + `layout_override`; **Motion Planner pass-1** (choreography rules, timing ước lượng, anchor match + fallback thứ tự); pipeline resolve gọi preset (2-2); lưu tree + resolved JSON (kèm motion_plan) trong scene_set version; warnings machine-readable; integration MockLLM full-pipeline CI.
**Out:** constraint presets/motion table cụ thể (2-2, 2-6); solver tổng quát + Gallery/Timeline class (v1.1); editor semantic (5-1 dùng tree qua form).

## Business Rules
1. AI không sinh layout/vị trí/font/animation — schema đầu ra prompt không có các field đó; xuất hiện → parse fail. **Hard-enforced, this is the anti-pattern this project has already hit once — see the [rules/naming.md](../rules/naming.md) layout drift incident.**
2. Ghép `narration` các cảnh == voice_over script (normalize) — lệch là bug engine, không ship.
3. Classifier deterministic: cùng tree → cùng class (property test); rule table là config có version, sửa không deploy.
4. scene_set resolved pass strict 100% — fail là bug engine.
5. `layout_override` của user thắng classifier; regenerate: cấu trúc semantic cùng loại → giữ override, đổi loại → reset + thông báo.
6. Component kind dữ liệu (stat/chart/table/quote) thiếu source_id → strict chặn / auto_fix hạ về body + warning.
7. Cảnh >10s → tách tại ranh giới câu; class không khả dụng → hạ bậc theo bảng + warning.
8. **(Motion Planner)** deterministic theo rule §9.2; `narration_anchor` không match nguyên văn → bỏ anchor + fallback thứ tự (warning, không lỗi); attention budget (≤1 chuyển động lớn cùng lúc); mọi track khai `reason` (narration_sync|hierarchy|sequence).
9. **(chống lặp bố cục — video-taste.md §4.2)** post-pass sau classify: không quá 2 cảnh liên tiếp cùng class; 1 class không vượt 40% tổng cảnh (trừ Hero/TextFocus ≤2); video ≥8 cảnh phải ≥4 class khác nhau. **Luật engine, KHÔNG đưa vào prompt AI.**

## Acceptance Criteria
1. **(happy)** Script 60s → 8-12 cảnh: tree hợp lệ, class phân bổ đa dạng đúng rule, resolved strict-valid, đủ 2 format từ 1 tree (không gọi lại AI).
2. **(biên/BR-3)** Property test: 50 tree fixture → classifier ổn định.
3. **(biên/BR-5)** Override List→Quote, regenerate cùng cấu trúc → giữ Quote; đổi cảnh chart → reset + thông báo.
3b. **(biên/BR-9)** Fixture 10 cảnh mà classifier tự nhiên cho 4 cảnh MediaText liên tiếp → post-pass phân bổ lại.
4. **(biên/BR-1)** Mock LLM trả field "layout" → parse fail đúng BR.
5. **(BR-2)** Test ghép narration == voice_over pass 10 fixture.
6. **(CI)** Full pipeline MockLLM xanh; 3 topic thật Ollama nghiệm thu tay.

## Data & API
scenes lưu `semantic_tree` + resolved JSON + `layout_override`. Contract change: **có** — schema scene mở rộng; prompt schema mới.

## Decisions already locked
- Kiến trúc Layout Engine tầng, AI dừng ở semantic (PO 2026-07-11 — [decisions/0008](../decisions/0008-layout-engine-deterministic.md)).
- Rule table khởi điểm 12 rule; Gallery hạ về MediaText ở v1. ⏳ thứ tự rule do BA review khi implement.

## Execution Steps

Work these in order. Update `state/4-6.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

**Boundary reminder for every step below:** AI (LLM call) touches ONLY Step 1 (the Semantic Storyboard prompt + Scene Tree parse). Steps 2 onward — Semantic Analysis, Layout Classifier, Constraint Resolver, Theme, Motion Planner — are pure, deterministic, non-LLM Python. If any step past Step 1 needs an LLM call to "decide" something, that is a violation of this task's entire premise — stop and re-read [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md) before continuing.

### Step 1: Semantic Storyboard prompt + Scene Tree Pydantic schema (BR-1, BR-6)
- **Files:** `backend/app/pipeline/nodes/storyboard/generate.py`, `backend/app/schemas/scene_tree.py`
- **Do:** call `get_active_prompt("storyboard.generate")` per `docs/specs/prompts.md` §7 (do not re-invent — the prompt spec already defines the 10 component kinds + `beat` + `narration_anchor`, content/intent only). Define the Scene Tree Pydantic schema so it has **no** `layout`/`position`/`font`/`animation`/`camera`/`transition` field anywhere — if the LLM output contains one, parsing must fail loudly (BR-1, per `rules/type-safety.md`: "a stray layout/position/animation field is a parse failure by design, not something to `.get()` around"). Enforce structural limits: ≤8 components/scene, bullet 3-6 items, group ≤2 levels.
- **Verify:** unit test: Mock LLM response containing a `"layout"` field → schema parse raises (AC4). Unit test: valid semantic-only response → parses to Scene Tree.
- **On failure:** transient → retry 3x; logic/config → `systematic-debugging` skill; still failing → block task, log in `memory/project-memory.md`, flag to [architect](../agents/architect.md) per the task's elevated review requirement.
- **Commit:** `git add backend/app/pipeline/nodes/storyboard/generate.py backend/app/schemas/scene_tree.py && git commit -m "feat(storyboard): 4-6 semantic storyboard prompt + scene tree schema (AI content/intent only)" && git push`

### Step 2: narration == voice_over reconciliation check (BR-2)
- **Files:** `backend/app/pipeline/nodes/storyboard/validate.py`
- **Do:** deterministic check (no LLM) that concatenated per-scene `narration` (normalized) equals the script's `voice_over` text. A mismatch is a bug in the engine, not something to ship with a warning (BR-2 — stricter than 4-5's number-set check).
- **Verify:** `pytest backend/tests/unit/pipeline/nodes/storyboard/test_narration_match.py` with 10 fixtures → all pass (AC5).
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 narration==voice_over reconciliation check (10 fixtures)`.

### Step 3: Semantic Analysis pass (deterministic, no LLM)
- **Files:** `backend/app/pipeline/layout_engine/analysis.py`
- **Do:** pure-function analysis over the Scene Tree producing a content profile (dominant component kind, density, structure signals) that the Classifier consumes next. Follow [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md) for the analysis→classify pipeline shape.
- **Verify:** unit test: fixture tree → expected profile fields populated deterministically (same input → same output, run twice).
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 semantic analysis pass (profile + dominant kind)`.

### Step 4: Layout Classifier — versioned rule-table config (BR-3, BR-7)
- **Files:** `app/layout_engine/classifier_rules.yaml` (or json, per `docs/specs/layout-engine.md` §5 conventions), `app/layout_engine/classifier.py`
- **Do:** implement the classifier as a **config-driven rule table** (12 starter rules per "Decisions already locked") — editable without a deploy (per `rules/configuration-env.md` spirit: behavior driven by data, not code). Same tree → same class always (deterministic, BR-3). Scenes >10s split at sentence boundaries; unavailable classes (e.g. Gallery in v1) degrade per the fallback table with a warning (BR-7). Layout class names are PascalCase canonical per `rules/naming.md` (`Hero, TextFocus, MediaFull, MediaText, Comparison, BigNumber, Chart, VersusTable, List, Quote, Code`) — never the retired snake_case names.
- **Verify:** property test: 50 tree fixtures → classifier output stable across reordering of components that shouldn't affect class (AC2).
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 layout classifier (config rule table, PascalCase classes, BR-3/BR-7)`.

### Step 5: layout_override handling on regenerate (BR-5)
- **Files:** `app/layout_engine/classifier.py`, `backend/app/services/scene_service.py`
- **Do:** a user's `layout_override` always wins over the classifier's choice. On content regeneration: if the new semantic structure is the same kind, keep the override; if it changed kind, reset the override and surface a notification (BR-5).
- **Verify:** unit test: override List→Quote, regenerate same-structure content → Quote retained (AC3); regenerate to a chart-shaped scene → override reset + notification flag present.
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 layout_override precedence + regenerate reset logic`.

### Step 6: Component-kind data validation — source_id requirement (BR-6)
- **Files:** `app/layout_engine/analysis.py` or a dedicated `app/layout_engine/component_validate.py`
- **Do:** `stat`/`chart`/`table`/`quote` component kinds missing `source_id` either hard-block in strict mode or auto-downgrade to `body` with a warning in lenient mode (BR-6, ties to 2-6 BR-2).
- **Verify:** unit test: `stat` component without `source_id` in strict mode → blocked; in auto_fix mode → downgraded to `body` + warning present.
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 component-kind source_id validation (strict/auto_fix)`.

### Step 7: Anti-repetition post-pass (BR-9 — "chống lặp bố cục", engine-only, never in the prompt)
- **Files:** `app/layout_engine/post_pass.py`
- **Do:** after every scene is classified, apply the post-pass rules from `video-taste.md` §4.2: no more than 2 consecutive scenes of the same class; no class exceeds 40% of total scenes (except Hero/TextFocus ≤2 scenes); videos ≥8 scenes must use ≥4 distinct classes. Non-compliant results get a warning, not an auto-fix loop (per BR-9 — "không tự sửa vòng lặp"). **This logic must never leak into the storyboard.generate prompt** — it's engine code, reinforcing the Step 1 boundary reminder.
- **Verify:** unit test with the 10-scene fixture where the classifier naturally produces 4 consecutive MediaText scenes → post-pass redistributes so no run exceeds 2 (AC3b); 8-scene video with only 2 classes → warning surfaced.
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 anti-repetition post-pass (BR-9)`.

### Step 8: Motion Planner pass-1 (BR-8, deterministic per layout-engine.md §9.2)
- **Files:** `app/layout_engine/motion_planner.py`
- **Do:** choreography rules producing timing estimates and motion tracks; match `narration_anchor` to the narration verbatim — on no match, drop that anchor and fall back to sequence order (warning, not an error). Enforce an attention budget of ≤1 large simultaneous motion. Every track must declare a `reason` (`narration_sync`/`hierarchy`/`sequence`) — a missing reason is an engine bug, not a warning (BR-8).
- **Verify:** unit test: anchor text not present in narration → anchor dropped, fallback order applied, warning present, no exception. Unit test: every generated track has a non-null `reason`.
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 motion planner pass-1 (anchor match + fallback + attention budget)`.

### Step 9: Resolve integration — Constraint Resolver + Theme (calls 2-2/2-6 presets)
- **Files:** `app/layout_engine/resolve.py`, wired into `backend/app/pipeline/nodes/storyboard/node.py`
- **Do:** wire classifier output + motion plan into the Constraint Resolver and Theme layer (presets already built in 2-2/2-6 — this task integrates, does not redefine, those presets per Scope Out). Resolve must pass strict validation 100% of the time on the classifier's own output (BR-4 — a strict-validation failure here is an engine bug, never shipped).
- **Verify:** unit test: resolve output from 5 golden semantic trees always strict-passes (feeds Step 11's golden snapshot test).
- **On failure:** non-transient by nature (a strict-fail here IS an engine bug) → `systematic-debugging` skill immediately.
- **Commit:** `4-6 resolve integration with constraint/theme presets (BR-4)`.

### Step 10: Persist tree + resolved JSON + motion_plan in scene_set version; two formats from one tree
- **Files:** `backend/app/services/scene_service.py`, `backend/app/models/scene_set.py`
- **Do:** store `semantic_tree`, resolved JSON, `layout_override`, and `motion_plan` on the scene_set version (contract change — update `docs/specs/scene-json-schema.md` and `docs/specs/database-schema.md` in the same PR per `rules/documentation.md`). Verify producing a 2nd output format from the same stored tree requires zero additional LLM calls (this is the entire point of the layered architecture).
- **Verify:** integration test asserting an LLM call counter stays at its Step-1 value when resolving the same tree into a 2nd format (part of AC1).
- **On failure:** same policy as Step 1.
- **Commit:** `4-6 persist semantic_tree/resolved/motion_plan + scene-json-schema contract update`.

### Step 11: Golden fixtures + property tests + full-pipeline MockLLM CI integration
- **Files:** `tests/fixtures/layout_engine/profile_to_class/*.json` (≥2 fixtures per rule — match + non-match), `tests/fixtures/layout_engine/golden_trees/*.json` (5 golden trees), `backend/tests/integration/pipeline/test_storyboard_full_pipeline.py`
- **Do:** the profile→class fixture set is this task's central, long-lived test asset per DoD — build ≥2 fixtures per classifier rule. Add the 5-golden-tree → snapshot-resolved-JSON test. Wire a full-pipeline MockLLM CI integration test (research→...→storyboard resolved).
- **Verify:** `pytest backend/tests/unit/layout_engine backend/tests/integration/pipeline/test_storyboard_full_pipeline.py` → all AC-mapped tests pass, including AC1 (8-12 scene script → diverse valid classes, strict-valid resolve, 2-format reuse without re-calling AI), AC2 (classifier stability), AC3/AC3b (override + anti-repetition), AC4 (parse-fail on stray layout field), AC5 (narration match), AC6 (full pipeline green).
- **On failure:** same policy as Step 1; a golden-snapshot mismatch needs `systematic-debugging`, never a snapshot-update-to-make-it-pass without understanding why it changed.
- **Commit:** `4-6 golden fixtures + property tests + full-pipeline CI (complete AC coverage)`.

### Step 12: Manual acceptance — 3 real topics via Ollama (AC6 second half)
- **Files:** none (manual run + notes appended to PR description / `memory/project-memory.md` if a gap is found)
- **Do:** run the full pipeline end-to-end with Ollama on 3 real topics; compare chosen classes against BA expectations table (per DoD). This step is a human-in-the-loop acceptance check, not automatable — flag findings rather than silently adjusting the rule table without recording why.
- **Verify:** 3 topics produce sensible, rule-compliant class distributions; any surprising result is noted (not silently "fixed" by tweaking rules without a recorded rationale).
- **On failure:** if a topic reveals a genuine classifier bug, treat as non-transient — root-cause via `systematic-debugging`, fix in Step 4/7, re-run this step.
- **Commit:** `4-6 manual acceptance notes for 3 Ollama topics` (docs-only commit, e.g. append to PR description file or task's Retrospective draft).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture profile→class là tài sản test trung tâm (mỗi rule ≥2 fixture); golden test: 5 semantic tree chuẩn → snapshot resolved JSON. Additionally: [architect](../agents/architect.md) review for Layout Engine boundary compliance is required before merge (not just Reviewer) per [tasks/README.md](README.md) task→agent ownership table.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-6.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-6.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
