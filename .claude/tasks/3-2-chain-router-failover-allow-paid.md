# Task 3-2: Chain router + failover + ALLOW_PAID

**Points:** 5đ · **Epic:** 3 — Provider framework · **Depends:** 3-1 · **FR:** FR-18, FR-21

## User story
As a system, I want mọi call ra ngoài đi qua chuỗi ưu tiên có failover tự động, so that một provider chết hay hết quota không bao giờ dừng cả hệ thống.

## Why
Trái tim của chiến lược free-tier: xoay giữa Gemini/Groq/OpenRouter/local theo tình trạng thực. Cũng là nơi thực thi `ALLOW_PAID` — hàng rào chống phát sinh chi phí ngoài ý muốn.

## Scope
**In:** router đọc `*_CHAIN` theo capability/tier; available check mỗi call (cache 30s: key tồn tại/health/paid-policy); failover: QuotaError→xoay key→next; Timeout/5xx→next; event `provider.failover`; ghi usage tại router; health check định kỳ + on-demand; `AllProvidersFailed` giàu thông tin.
**Out:** UI ma trận (3-5); adapters thật (3-3); daily cap (3-5).

## Business Rules
1. `ALLOW_PAID=false` loại provider `is_paid` khỏi chain kể cả có key — kiểm tại router, không tin adapter.
2. Lỗi 4xx non-retryable (prompt sai, content policy) → **không** failover — fail ngay kèm nguyên nhân.
3. `AllProvidersFailed` chứa `[{provider, reason}]` — nguồn dữ liệu cho error state RunningState (5-8 BR-2).
4. Mỗi call đi qua chain tối đa 1 vòng — không loop.
5. Health check fail → provider tạm loại 60s (circuit breaker đơn giản), event phát 1 lần (không spam).

## Acceptance Criteria
1. **(happy)** gemini mock 500 → groq trả lời + event failover đúng payload.
2. **(biên/BR-2)** gemini 400 invalid → fail ngay không gọi groq.
3. **(biên/BR-1)** fpt có key + ALLOW_PAID=false → counter fpt = 0 vĩnh viễn.
4. **(lỗi/BR-3)** Cả chain chết → AllProvidersFailed đủ danh sách lý do; node retry backoff.
5. **(BR-5)** Provider fail health → 60s không được gọi → tự thử lại; event 1 lần.

## Data & API
Bảng: `llm_usage` ghi tại đây. Events: `provider.failover`, `provider.exhausted`. Contract change: không.

## Decisions already locked
- ⏳ Circuit breaker 60s cố định v1 (không exponential).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + toàn bộ test bằng mock adapter (không network) — code được test kỹ nhất hệ thống.
