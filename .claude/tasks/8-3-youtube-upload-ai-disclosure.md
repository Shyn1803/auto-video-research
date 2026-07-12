# Task 8-3: YouTube upload + AI disclosure + quota

**Points:** 5đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-2 · **FR:** FR-12

## User story
As a Content Creator, I want video tự đăng lên YouTube với đầy đủ metadata và khai báo AI, so that đúng chính sách nền tảng và không bao giờ bị gỡ vì thiếu khai báo.

## Why
FR-12 + rủi ro "AI content bị giảm reach/gỡ" — disclosure bắt buộc (BR-1 không có nút tắt) là quyết định tuân thủ, không phải tuỳ chọn.

## Scope
**In:** resumable upload; metadata (title/description/tags/category); altered-content (AI) disclosure + madeForKids=false; privacy config (default unlisted); quota guard (đếm units/ngày, chặn trước upload); map lỗi API → tiếng Việt; external_id/url về publishes; attribution BGM nối description (6-5 BR-2).
**Out:** thumbnail tuỳ chỉnh (v1.1); playlist/end-screen (v1.1); Shorts-specific metadata.

## Business Rules
1. Disclosure luôn bật — không config tắt (compliance).
2. Quota không đủ (~1600 units) → chặn trước upload + giờ reset (07:00 PT); không thử-rồi-fail.
3. Upload đứt → resume theo session (không tải lại từ đầu).
4. Video >15' hoặc >256GB → chặn capabilities (không xảy ra với v1 nhưng check rẻ).

## Acceptance Criteria
1. **(happy)** Đăng → video unlisted đúng metadata + disclosure (kiểm Studio 1 lần, screenshot vào PR); URL lưu + mở được.
2. **(biên/BR-3)** Ngắt mạng giữa upload (mock) → resume tiếp session, không upload lại phần đã gửi.
3. **(lỗi/BR-2)** Quota còn 500 → chặn + "reset 07:00 PT"; 403 lạ → failed message dịch + retry.
4. **(BGM)** Track cần ghi công → description chứa attribution.
5. **(BR-1)** Không tồn tại đường tắt disclosure (review code + không có config).

## Data & API
publishes.external_id/url; cột `quota_used_today` mới. Contract change: nhẹ (cột) — ghi migration.

## Decisions already locked
- ⏳ Category mặc định "Science & Technology".

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock YouTube API đủ nhánh (200/401/403quota/500/resume); upload thật 1 video test kiểm tay.
