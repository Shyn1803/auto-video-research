# Task 4-3: Node Research — thu thập + dedupe + tóm tắt

**Points:** 5đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-1, 3-3 · **FR:** FR-02
**State file:** [`state/4-3.json`](state/4-3.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/4-3-node-research` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As a Content Creator, I want AI tự gom và tóm tắt nguồn từ nhiều kênh uy tín trong vài phút, so that tôi bắt đầu từ nguyên liệu đã sàng lọc thay vì tự Google cả buổi.

## Why
FR-02 — bước tạo ra "nguyên liệu tin cậy" cho mọi bước sau. Chiến lược API/RSS-first vừa là chất lượng vừa là pháp lý (robots/ToS).

## Scope
**In:** connectors arXiv/HN-Algolia/GitHub/RSS-list(config)/SearXNG(+Tavily/Brave qua chain) — mỗi connector 1 module + fixture; crawl trafilatura (respect robots); paywall → title+abstract + `partial_content`; dedupe url_hash + embedding similarity; summarize song song bounded (tier cheap, prompt `research.summarize`); trusted domains seed; API sources đầy đủ (§4); SSE progress ("đang đọc X 4/12").
**Out:** UI màn (5-6); Reddit RSS (connector sau); quản lý RSS list qua UI (v1.1).

## Business Rules
1. 1 connector lỗi → skip + ghi nhận trong kết quả; run fail chỉ khi **mọi** connector lỗi.
2. Similarity ≥ ngưỡng (config 0.92) → giữ bản trusted hơn, hoà thì mới hơn.
3. Cache chung theo content_hash (project_id NULL) — không re-crawl URL đã có trong TTL 30 ngày.
4. Giữ tối đa N source (config 20) theo ranking sơ bộ.
5. Summarize fail 1 bài → bài đó không summary + cờ, không chặn node (tối thiểu 5 bài thành công).

## Acceptance Criteria
1. **(happy)** Fixture 12 bài (2 trùng, 1 paywall) → 10 sources; partial đánh dấu; đủ summary_vi + key_facts.
2. **(biên/BR-1)** Mock HN timeout → run xong, kết quả ghi "HN không truy cập được".
3. **(biên/BR-3)** Re-run cùng topic → 0 re-crawl URL cũ.
4. **(lỗi)** Mọi connector fail → node fail retryable, message "không thu thập được nguồn".
5. **(BR-2)** 2 bài giống 0.95 (1 trusted 1 không) → giữ trusted.
6. **(SSE)** Progress hiện tên nguồn thật.

## Data & API
Bảng: sources, source_embeddings. Endpoints §4. Events: step.progress. Contract change: không.

## Decisions already locked
- ⏳ Ngưỡng similarity 0.92 khởi điểm — tune sau 2 tuần dogfooding.
- RSS list khởi điểm: OpenAI/Anthropic/Google/DeepMind/NVIDIA/HuggingFace blog.

## Execution Steps

Work these in order. Update `state/4-3.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: Sources/source_embeddings schema
- **Files:** `backend/app/models/source.py`, migration under `alembic/versions/`
- **Do:** create `sources` and `source_embeddings` tables per Data & API §4.
- **Verify:** `alembic upgrade head` → tables exist.
- **On failure:** transient → retry 3x; logic/config → `systematic-debugging` skill; still failing → block task, log in `memory/project-memory.md`.
- **Commit:** `git add backend/app/models/source.py alembic/ && git commit -m "feat(research): 4-3 sources/source_embeddings schema" && git push`

### Step 2: Connector adapters (arXiv, HN-Algolia, GitHub, RSS-list, SearXNG)
- **Files:** `backend/app/adapters/search/arxiv.py`, `backend/app/adapters/search/hn_algolia.py`, `backend/app/adapters/search/github.py`, `backend/app/adapters/search/rss.py`, `backend/app/adapters/search/searxng.py` (Tavily/Brave already covered by existing chain from 3-3)
- **Do:** one connector = one module, each going through the adapter pattern ([patterns/provider-adapter.md](../patterns/provider-adapter.md)) — no business logic calling provider APIs directly. Each connector gets its own fixture (per DoD, HTML fixtures for 5 different providers).
- **Verify:** `pytest backend/tests/unit/adapters/search/` with `respx`-mocked HTTP (no live network calls, per `rules/testing.md`) → each connector module's test passes independently.
- **On failure:** same policy as Step 1.
- **Commit:** `4-3 connector adapters: arxiv/hn/github/rss/searxng`.

### Step 3: Crawl (trafilatura, robots-respecting) + paywall handling
- **Files:** `backend/app/pipeline/nodes/research/crawl.py`
- **Do:** crawl article bodies with trafilatura, respecting `robots.txt`; on paywall, fall back to title+abstract only and mark `partial_content=true`.
- **Verify:** unit test with fixture HTML (paywalled vs normal) → `partial_content` flag set correctly.
- **On failure:** same policy as Step 1.
- **Commit:** `4-3 trafilatura crawl + paywall partial_content handling`.

### Step 4: Dedupe — url_hash + embedding similarity (BR-2)
- **Files:** `backend/app/pipeline/nodes/research/dedupe.py`
- **Do:** dedupe by exact `url_hash` first, then embedding similarity ≥ configured threshold (0.92 default per "Decisions already locked"); on a tie, keep the trusted-domain source, and if still tied, keep the newer one (BR-2).
- **Verify:** unit test: 2 sources at 0.95 similarity, one trusted one not → trusted one kept (AC5).
- **On failure:** same policy as Step 1.
- **Commit:** `4-3 dedupe url_hash + embedding similarity + BR-2 tie-break`.

### Step 5: Content-hash cache (BR-3) + max-N source cap (BR-4)
- **Files:** `backend/app/pipeline/nodes/research/cache.py`
- **Do:** cache crawled content globally by `content_hash` (project_id NULL — shared across projects), TTL 30 days, so a re-crawl of the same URL within TTL is skipped (BR-3). After ranking-sort, cap kept sources at configured N (default 20) (BR-4).
- **Verify:** integration test: re-run same topic twice → 0 re-crawls of previously-seen URLs on the 2nd run (assert via a crawl-call counter, AC3).
- **On failure:** same policy as Step 1.
- **Commit:** `4-3 content_hash cache + max-N source cap`.

### Step 6: Bounded-parallel summarize (research.summarize prompt, tier cheap)
- **Files:** `backend/app/pipeline/nodes/research/summarize.py`
- **Do:** summarize sources in parallel with a concurrency bound, calling `get_active_prompt("research.summarize")` (from 4-2 — never hardcode the prompt, per BR-4 of 4-2) at `cheap` tier per `rules/performance.md`. A single article's summarize failure flags that article (no summary + a flag) without failing the node, as long as ≥5 articles succeed (BR-5).
- **Verify:** unit test: 1 of 12 summarize calls raises → node completes, that source flagged, others fine (AC1 partial).
- **On failure:** same policy as Step 1.
- **Commit:** `4-3 bounded-parallel summarize + BR-5 partial-failure handling`.

### Step 7: Node orchestration — connector-failure tolerance (BR-1) + SSE progress
- **Files:** `backend/app/pipeline/nodes/research/node.py` (registered in `backend/app/pipeline/graph.py`)
- **Do:** wire the full research node: run all connectors, skip+record any that error individually (BR-1 — node only fails if **every** connector fails), emit `step.progress` SSE events naming the actual source being read (not "Processing...", per Test Notes/UI section and `rules/logging.md` structured-log preference).
- **Verify:** unit test: mock HN connector timeout → node completes with "HN không truy cập được" recorded, other sources present (AC2). Second test: all connectors fail → node fails retryable with correct message (AC4).
- **On failure:** same policy as Step 1.
- **Commit:** `4-3 research node orchestration + connector fault tolerance + SSE progress`.

### Step 8: Wire up remaining tests + verify all Acceptance Criteria
- **Files:** `tests/unit/pipeline/nodes/research/...`, `backend/tests/integration/pipeline/test_research_node.py`
- **Do:** one test per Acceptance Criterion (happy fixture of 12 articles incl. 2 duplicates + 1 paywall → 10 sources, AC1); SSE progress content assertion (AC6).
- **Verify:** `pytest backend/tests/unit/pipeline/nodes/research backend/tests/integration/pipeline/test_research_node.py` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** `4-3 complete AC test coverage`.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + fixture HTML 5 provider khác nhau; connector test độc lập từng module.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/4-3.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/4-3.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
