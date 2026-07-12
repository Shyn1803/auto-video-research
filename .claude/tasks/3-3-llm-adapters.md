# Task 3-3: LLM adapters — ollama, gemini, groq, openrouter + mock + embedding

**Points:** 5đ · **Epic:** 3 — Provider framework · **Depends:** 3-2 · **FR:** FR-18

## User story
As a pipeline, I want gọi LLM local lẫn cloud free-tier qua cùng một interface có structured output, so that đổi model chỉ là đổi config và output luôn parse được.

## Why
Hiện thực chiến lược "local-first, free-tier-second" của SRS §1.2. Structured output + retry parse là điều kiện để pipeline chạy ổn với model local.

## Scope
**In:** 4 adapter (ollama/gemini/groq/openrouter) + `mock` (fixture theo prompt name — deterministic CI); `call_structured(tier, prompt_name, schema)` (JSON mode ollama, responseSchema gemini; retry parse 2); token counting + cost estimate; embedding `bge_m3_local` + `gemini_embedding`.
**Out:** mistral (1 file sau, pattern sẵn); model routing per-task nâng cao.

## Business Rules
1. Parse fail lần 3 → non-retryable kèm raw output trong log debug.
2. Mock adapter chỉ chạy `APP_ENV` development/test — guard cứng.
3. Provider free ghi cost=0 nhưng vẫn ghi tokens (theo dõi quota).
4. openrouter lọc model `:free` cho `openrouter_free`; `openrouter_paid` cần cả key + ALLOW_PAID.

## Acceptance Criteria
1. **(happy)** Chỉ OLLAMA_URL → ma trận đúng; call_structured trả Pydantic hợp lệ trên ollama.
2. **(biên)** Thêm GEMINI key qua UI → health pass → chain nhận không restart.
3. **(biên/BR-1)** Model trả JSON hỏng 3 lần (mock) → fail kèm raw output.
4. **(embedding)** 2 đoạn Việt cùng chủ đề → cosine > ngưỡng; khác chủ đề < ngưỡng.
5. **(BR-2)** `APP_ENV=production` + chain chứa mock → app từ chối start.

## Data & API
Bảng giá: file config `pricing.yaml` (không hardcode); llm_usage ghi qua router.

## Decisions already locked
- ⏳ BGE-M3 chạy trong process backend v1 (không service riêng) — tách khi 9-3 nếu nghẽn.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + nightly `@external` smoke (1 call thật/provider có key).
