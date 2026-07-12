# Task 4-3: Node Research — thu thập + dedupe + tóm tắt

**Points:** 5đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-1, 3-3 · **FR:** FR-02

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

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture HTML 5 provider khác nhau; connector test độc lập từng module.
