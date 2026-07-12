# Task 9-6: Langfuse + Sentry self-host

**Points:** 2đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 3-2 · **FR:** NFR-5

## User story
As a developer, I want trace mọi LLM call và error tracking có release tag, so that debug "AI trả lời lạ" và "lỗi ở đâu" bằng dữ liệu thay vì đoán.

## Why
LLM observability là điều kiện tune prompt có căn cứ (nối 4-2 eval); Sentry rút ngắn vòng phát hiện lỗi production khi dogfooding.

## Scope
**In:** Langfuse self-host: trace mỗi LLM call từ router 3-2 (prompt name+version, tokens, latency, tier, correlation_id); Sentry/GlitchTip: backend+FE+workers, release tag theo git; compose profile monitoring.
**Out:** trace UI trong app (dùng Langfuse UI); alert từ Sentry (7-4 đủ kênh).

## Business Rules
1. Trace không chứa key/token (chỉ prompt/response nghiệp vụ). See [rules/logging.md](../rules/logging.md).
2. Langfuse/Sentry down → fire-and-forget, pipeline không ảnh hưởng, warning 1 lần.
3. Env không cấu hình → tắt sạch (không lỗi, không noise).

## Acceptance Criteria
1. **(happy)** Mở 1 run trong Langfuse → chuỗi call đủ node, đúng prompt version, lọc theo correlation_id.
2. **(biên/BR-2)** Tắt Langfuse giữa run → pipeline xong bình thường, 1 warning.
3. **(Sentry)** Lỗi ném thử FE+BE+worker → hiện đúng release tag.
4. **(BR-1)** Trace sample kiểm không có secret (test denylist như 9-4).

## Data & API
Env LANGFUSE_*/SENTRY_DSN. Contract change: không.

## Decisions already locked
- ⏳ GlitchTip thay Sentry nếu resource server hạn chế — quyết khi dựng.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + smoke trong compose monitoring; BR-1 test tự động cùng pattern 9-4.
