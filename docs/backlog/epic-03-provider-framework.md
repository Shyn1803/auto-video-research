# Epic 3 — Provider framework: adapter, chain, failover, cost (FR-15/18/21)

**Goal:** M2 — thêm key qua UI provider tham gia chain không restart; 0 key vẫn chạy local đầy đủ (NFR-6).
**Points:** 18 · **Tuần:** 3–5 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.

---

# Story 3.1 — Adapter base + registry + config layer (3đ)

**User story:** As a developer, I want khung adapter chuẩn cho mọi năng lực bên ngoài, so that thêm provider mới là 1 file + 1 decorator, không đụng business logic.
**Bối cảnh & giá trị:** FR-21 là yêu cầu trung tâm của SRS ("local-first, kích hoạt bằng key"). Pattern adapter là việc lặp lại nhiều nhất toàn dự án (≥15 adapter đến release) — chuẩn sai ở đây nhân lỗi lên 15 lần.

## Scope
**In:** base class 7 capability (LLM/TTS/Search/ImageGen/AssetStock/Storage/Publish) + `@register_{cap}(name)`; hợp nhất TTSAdapter 2.4 vào khung; `ProviderSettings` (env override DB); `ProviderError(retryable)`; adapter mẫu + test mẫu làm chuẩn copy (dev-guide §3).
**Out:** router chain (3.2); adapter cụ thể (3.3+); notification adapter (7.4 — dùng cùng khung).

## Business Rules
- **BR-1:** adapter không đọc env/DB trực tiếp — nhận `ProviderSettings`.
- **BR-2:** adapter không ghi usage/log nghiệp vụ — chỉ raise/return (việc của router).
- **BR-3:** registry trùng tên → fail startup (không ghi đè lặng lẽ).
- **BR-4:** mỗi adapter khai báo `is_paid` tĩnh — quên khai = mặc định True (an toàn chi phí).

## UI/UX
N/A.

## Data & API
N/A trực tiếp; `ProviderSettings` đọc từ env + bảng api_keys (3.4 hoàn thiện phần DB).

## Acceptance Criteria
1. **(happy)** Provider demo mới: 1 file + decorator → có trong registry, gọi được qua router mock.
2. **(lỗi/BR-3)** 2 adapter trùng tên → app không start, message chỉ rõ 2 file.
3. **(BR-4)** Adapter không khai is_paid → được coi paid (test).
4. **(chuẩn)** mypy strict pass; test mẫu chạy không network.

## Test Notes
Test mẫu là tài liệu sống — dev copy khi viết adapter mới; review PR đầu tiên khắt khe vì là khuôn.

## Quyết định đã chốt
- 7 capability cố định v1 — thêm capability mới cần ADR nhỏ (giữ khung gọn).

**Depends:** 1.1 · **Design:** — · **FR:** FR-21

---

# Story 3.2 — Chain router + failover + ALLOW_PAID (5đ)

**User story:** As a system, I want mọi call ra ngoài đi qua chuỗi ưu tiên có failover tự động, so that một provider chết hay hết quota không bao giờ dừng cả hệ thống.
**Bối cảnh & giá trị:** Trái tim của chiến lược free-tier: xoay giữa Gemini/Groq/OpenRouter/local theo tình trạng thực. Cũng là nơi thực thi `ALLOW_PAID` — hàng rào chống phát sinh chi phí ngoài ý muốn mà user yêu cầu từ đầu dự án.

## Scope
**In:** router đọc `*_CHAIN` theo capability/tier; available check mỗi call (cache 30s: key tồn tại / health / paid-policy); failover: QuotaError→xoay key→next; Timeout/5xx→next; event `provider.failover`; ghi usage tại router; health check định kỳ + on-demand; `AllProvidersFailed` giàu thông tin.
**Out:** UI ma trận (3.5); adapters thật (3.3); daily cap (3.5).

## Business Rules
- **BR-1:** `ALLOW_PAID=false` loại provider `is_paid` khỏi chain kể cả có key — kiểm tại router, không tin adapter.
- **BR-2:** lỗi 4xx non-retryable (prompt sai, content policy) → **không** failover — fail ngay kèm nguyên nhân. Failover chỉ dành cho lỗi hạ tầng.
- **BR-3:** `AllProvidersFailed` chứa `[{provider, reason}]` — nguồn dữ liệu cho error state RunningState (5.8 BR-2).
- **BR-4:** mỗi call đi qua chain tối đa 1 vòng — không loop.
- **BR-5:** health check fail → provider tạm loại 60s (circuit breaker đơn giản), event phát 1 lần (không spam).

## UI/UX
N/A trực tiếp; toast failover (design-system §4.3) tiêu thụ event.

## Data & API
- Bảng: `llm_usage` ghi tại đây (schema §2.7). Events: `provider.failover`, `provider.exhausted`.
- Contract change: không (event-catalog sẵn).

## Acceptance Criteria
1. **(happy)** gemini mock 500 → groq trả lời + event failover đúng payload.
2. **(biên/BR-2)** gemini 400 invalid → fail ngay không gọi groq, lỗi nêu nguyên nhân.
3. **(biên/BR-1)** fpt có key + ALLOW_PAID=false → counter fpt = 0 vĩnh viễn.
4. **(lỗi/BR-3)** Cả chain chết → AllProvidersFailed đủ danh sách lý do; node retry backoff.
5. **(BR-5)** Provider fail health → 60s không được gọi → tự thử lại; event 1 lần.
6. **(unit)** Đủ bảng nhánh test-plan §1.1.

## Test Notes
Toàn bộ bằng mock adapter — không network. Đây là code được test kỹ nhất hệ thống (mọi thứ đi qua nó).

## Quyết định đã chốt
- Circuit breaker 60s cố định v1 (không exponential) — đơn giản đủ dùng. ⏳

**Depends:** 3.1 · **Design:** toast §4.3 · **FR:** FR-18, FR-21

---

# Story 3.3 — LLM adapters: ollama, gemini, groq, openrouter + mock + embedding (5đ)

**User story:** As a pipeline, I want gọi LLM local lẫn cloud free-tier qua cùng một interface có structured output, so that đổi model chỉ là đổi config và output luôn parse được.
**Bối cảnh & giá trị:** Hiện thực chiến lược "local-first, free-tier-second" của SRS §1.2. Structured output + retry parse là điều kiện để pipeline chạy ổn với model local (Qwen JSON mode kém ổn định hơn cloud).

## Scope
**In:** 4 adapter (ollama/gemini/groq/openrouter) + `mock` (fixture theo prompt name — deterministic CI); `call_structured(tier, prompt_name, schema)` (JSON mode ollama, responseSchema gemini; retry parse 2); token counting + cost estimate (bảng giá config); embedding `bge_m3_local` + `gemini_embedding`.
**Out:** mistral (1 file sau, pattern sẵn); model routing per-task nâng cao (tier đủ v1).

## Business Rules
- **BR-1:** parse fail lần 3 → non-retryable kèm raw output trong log debug.
- **BR-2:** mock adapter chỉ chạy APP_ENV development/test — guard cứng.
- **BR-3:** provider free ghi cost=0 nhưng vẫn ghi tokens (theo dõi quota).
- **BR-4:** openrouter lọc model `:free` cho `openrouter_free`; `openrouter_paid` cần cả key + ALLOW_PAID.

## UI/UX
N/A.

## Data & API
- Bảng giá: file config `pricing.yaml` (không hardcode); llm_usage ghi qua router.
- Contract change: không.

## Acceptance Criteria
1. **(happy)** Chỉ OLLAMA_URL → ma trận: ollama ✓, còn lại "thiếu key"; call_structured trả Pydantic hợp lệ trên ollama.
2. **(biên)** Thêm GEMINI key qua UI → health pass → chain nhận không restart; call sang gemini đúng thứ tự.
3. **(biên/BR-1)** Model trả JSON hỏng 3 lần (mock) → fail kèm raw output; không retry thêm.
4. **(embedding)** 2 đoạn Việt cùng chủ đề → cosine > ngưỡng; khác chủ đề < ngưỡng (fixture chuẩn).
5. **(BR-2)** APP_ENV=production + chain chứa mock → app từ chối start.

## Test Notes
Nightly `@external`: 1 call thật mỗi provider có key (smoke quota). Fixture embedding: 6 cặp câu Việt gán nhãn.

## Quyết định đã chốt
- BGE-M3 chạy trong process backend v1 (không service riêng) — tách khi 9.3 nếu nghẽn. ⏳

**Depends:** 3.2 · **Design:** — · **FR:** FR-18

---

# Story 3.4 — API Key management + mã hoá + xoay key (3đ)

**User story:** As an Admin, I want quản lý key an toàn với xoay vòng tự động, so that tận dụng nhiều free tier mà không lộ secret và không phải canh quota tay.
**Bối cảnh & giá trị:** FR-15. Free tier là chiến lược chi phí của dự án — xoay key tự động biến "quota hết" từ sự cố thành non-event.

## Scope
**In:** bảng api_keys Fernet; CRUD 🅐 (masked response); validate key thật trước lưu (test call nhẹ); round-robin nhiều key/provider; 429 → `exhausted_until` → tự re-activate; tab Quản trị › API Keys.
**Out:** YouTube OAuth (8.2 — flow riêng cùng bảng); Fernet rotation script (10.4).

## Business Rules
- **BR-1:** key plaintext không xuất hiện trong response/log sau lưu — chỉ masked `AIza…x4Kq`.
- **BR-2:** xoá key cuối của provider đang trong chain active → cảnh báo hệ quả (capability sẽ mất provider) trước khi xoá.
- **BR-3:** env key + DB key cùng provider → cả hai vào vòng xoay, env đứng trước.
- **BR-4:** `exhausted_until` mặc định = reset time provider (config/provider; không rõ → 00:00 UTC).

## UI/UX
- Màn: wireframe **Quản trị › API Keys**. States: default (bảng) · loading skeleton · empty ("chưa có key — hệ thống đang chạy local" + link CONFIGURATION) · error banner · disabled N/A.
- A11y: nút Thu hồi confirm; bảng caption.

## Data & API
- Bảng: api_keys (schema §2.7). Endpoints §9 CRUD.
- Contract change: không.

## Acceptance Criteria
1. **(happy)** 2 key gemini, key1 mock 429 → tự sang key2; key1 hiện "⚠ hết hạn mức → 00:00"; 00:00 tự active.
2. **(biên/BR-3)** Env + DB key → thứ tự đúng, cả hai được dùng (counter cả hai tăng).
3. **(lỗi)** POST key sai → 400 "key không hợp lệ", không lưu.
4. **(bảo mật/BR-1)** Test tự động grep log+response sau lưu → không plaintext.
5. **(biên/BR-2)** Xoá key cuối gemini khi gemini trong LLM_CHAIN → dialog nêu hệ quả.

## Test Notes
Fernet roundtrip unit; validate-call mock theo provider. Test bảo mật BR-1 là test giữ vĩnh viễn (regression).

## Quyết định đã chốt
- Validate key bằng call nhẹ nhất của từng provider (models.list tương đương) — ghi trong bảng provider config.

**Depends:** 3.2 · **Design:** wireframe **Quản trị › API Keys** · **FR:** FR-15

---

# Story 3.5 — Cost tracking + daily cap + màn Providers (2đ)

**User story:** As an Admin, I want một màn nhìn thấy hệ thống đang chạy bằng provider nào và tốn bao nhiêu, so that tôi kiểm soát chi phí bằng số liệu thay vì phỏng đoán.
**Bối cảnh & giá trị:** Đây là màn "niềm tin" của FR-21 — startup validation hiện hình. Daily cap là hàng rào cuối chống hoá đơn bất ngờ (yêu cầu gốc của user: test free trước, đầu tư sau).

## Scope
**In:** llm_usage partition tháng; check cap trước call; vượt → pause pipeline + event `cost.cap_reached` + notify; tab Quản trị › Providers (ma trận StatusBadge + lý do inactive 3 loại, nút health-check, cost hôm nay/cap); API `/admin/costs?group_by=`.
**Out:** Grafana chart sâu (9.5); thống kê gate Mode 1 (7.3 — cùng màn, khối riêng).

## Business Rules
- **BR-1:** cap=0 nghĩa "chỉ free" (tương đương ALLOW_PAID=false runtime).
- **BR-2:** chạm cap giữa run → dừng ở ranh giới node kế (không giết giữa node); status FAILED(reason=cost_cap); resume thủ công sau xử lý.
- **BR-3:** ma trận phân biệt 3 lý do inactive: "thiếu key" / "kiểm tra thất bại" / "bị chặn trả phí" — 3 nhãn khác nhau (critique v1).
- **BR-4:** cost hiển thị = ước tính từ bảng giá — ghi rõ "ước tính" trên UI.

## UI/UX
- Màn: wireframe **Quản trị › Providers**. States: default · loading · empty N/A (luôn có capability) · error (health-check API lỗi → giữ dữ liệu cũ + nhãn "chưa cập nhật") · disabled N/A.
- A11y: badge có text không chỉ màu (BR ma trận từ design-system §2.1).

## Data & API
- Bảng: llm_usage (partition — schema §2.7). Endpoints: `/admin/providers`, `/admin/providers/{n}/health-check`, `/admin/costs` (§9).
- Contract change: không.

## Acceptance Criteria
1. **(happy)** 3 kịch bản env (0 key / free keys / full) → ma trận đúng từng nhãn.
2. **(biên/BR-2)** Cap chạm giữa run → dừng sau node hiện tại; resume sau reset chạy tiếp.
3. **(lỗi/BR-3)** Provider health fail → nhãn "kiểm tra thất bại"; service sống lại + bấm kiểm tra → ✓ ngay.
4. **(số liệu)** `group_by=task` khớp tổng llm_usage seed (test so khớp).

## Test Notes
Seed llm_usage 3 ngày × 3 provider × 3 task cho test costs. Diễn tập cap là một mục Release Checklist (10.5) — story này chỉ cần test tự động.

## Quyết định đã chốt
- `DAILY_COST_CAP` mặc định 0 (chỉ free) — an toàn nhất cho giai đoạn test (theo yêu cầu gốc user).

**Depends:** 3.3, 3.4 · **Design:** wireframe **Quản trị › Providers** · **FR:** FR-18, FR-21

---

## 🏁 M2 (cuối tuần 5)
Demo tháo/lắp key trực tiếp: 0 key → chạy local; thêm key → chain nhận ngay; rút key giữa run → failover mượt + toast đúng.
