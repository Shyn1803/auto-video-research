# Task 3-4: API Key management + mã hoá + xoay key

**Points:** 3đ · **Epic:** 3 — Provider framework · **Depends:** 3-2 · **FR:** FR-15

## User story
As an Admin, I want quản lý key an toàn với xoay vòng tự động, so that tận dụng nhiều free tier mà không lộ secret và không phải canh quota tay.

## Why
FR-15. Free tier là chiến lược chi phí của dự án — xoay key tự động biến "quota hết" từ sự cố thành non-event.

## Scope
**In:** bảng `api_keys` Fernet; CRUD 🅐 (masked response); validate key thật trước lưu (test call nhẹ); round-robin nhiều key/provider; 429 → `exhausted_until` → tự re-activate; tab Quản trị › API Keys.
**Out:** YouTube OAuth (8-2 — flow riêng cùng bảng); Fernet rotation script (10-4).

## Business Rules
1. Key plaintext không xuất hiện trong response/log sau lưu — chỉ masked `AIza…x4Kq`. See [rules/security.md](../rules/security.md).
2. Xoá key cuối của provider đang trong chain active → cảnh báo hệ quả trước khi xoá.
3. env key + DB key cùng provider → cả hai vào vòng xoay, env đứng trước.
4. `exhausted_until` mặc định = reset time provider (config/provider; không rõ → 00:00 UTC).

## Acceptance Criteria
1. **(happy)** 2 key gemini, key1 mock 429 → tự sang key2; key1 hiện "⚠ hết hạn mức → 00:00"; 00:00 tự active.
2. **(biên/BR-3)** Env + DB key → thứ tự đúng, cả hai được dùng.
3. **(lỗi)** POST key sai → 400 "key không hợp lệ", không lưu.
4. **(bảo mật/BR-1)** Test tự động grep log+response sau lưu → không plaintext.
5. **(biên/BR-2)** Xoá key cuối gemini khi gemini trong LLM_CHAIN → dialog nêu hệ quả.

## Data & API
Bảng: api_keys. Endpoints §9 CRUD. Contract change: không.

## UI/UX
Wireframe Quản trị › API Keys. States: default(bảng)/loading/empty(link CONFIGURATION)/error/disabled N/A.

## Decisions already locked
- Validate key bằng call nhẹ nhất của từng provider (models.list tương đương).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + Fernet roundtrip unit; test bảo mật BR-1 giữ vĩnh viễn (regression).
