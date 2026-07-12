# Task 10-3: TikTok / Facebook / LinkedIn adapters

**Points:** 5đ · **Epic:** 10 — Release · **Depends:** 8-1 · **FR:** FR-12

## User story
As a Content Creator, I want hệ thống sẵn sàng đăng TikTok/Facebook/LinkedIn ngay khi nền tảng duyệt app, so that ngày có key là ngày đăng được, không chờ thêm sprint code.

## Why
FR-12 tầng 3. "Chờ duyệt" nằm ngoài kiểm soát — chiến lược là code xong 100%, kích hoạt = env. Nộp đơn từ tuần 11 chạy song song (đây là công việc PO, ngoài phạm vi code task này).

## Scope
**In:** 3 adapter theo PublishAdapter (8-1): TikTok Content Posting (dọc, AIGC disclosure), Facebook Reels (≤90s), LinkedIn video (ngang ưu tiên); env-activated; UI trạng thái "chờ duyệt nền tảng" + ngày nộp đơn; unit test HTTP mock đủ nhánh; test sandbox tới mức nền tảng cho phép; checklist nộp app review cho PO vào runbook.
**Out:** kích hoạt production (sau release — chỉ env); analytics 3 nền tảng qua API (v1.1 — nhập tay 8-5 đủ).

## Business Rules
1. Adapter code hoàn chỉnh + test — "chờ duyệt" là trạng thái dữ liệu, không phải code dở.
2. Capabilities per-platform vào bảng adapter (TikTok dọc ≤10'; FB Reels ≤90s; LinkedIn ngang ưu tiên) — validate trước đăng (8-1 BR-3 tiêu thụ).
3. App bị từ chối → runbook có mục các bước nộp lại + yêu cầu thường gặp của từng nền tảng.
4. AIGC disclosure TikTok bật cứng như YouTube (8-3 BR-1 pattern).

## Acceptance Criteria
1. **(happy-sandbox)** Key sandbox TikTok → flow chạy tới mức API cho phép; lỗi map rõ.
2. **(biên/BR-2)** Video 16:9 → TikTok chặn + gợi ý bản 9:16; video 2' → FB Reels chặn ≤90s.
3. **(UI)** Chưa duyệt → ⚠ + ngày nộp; thêm key → ✓ không deploy.
4. **(unit/BR-1)** 3 adapter coverage nhánh chính (200/4xx/5xx/quota) bằng mock.
5. **(BR-4)** Không đường tắt AIGC disclosure TikTok.

## Data & API
3 adapter + capabilities config. Contract change: không (PublishAdapter sẵn).

## Decisions already locked
- ⏳ Nộp đơn TikTok + Facebook tuần 11 (việc PO); LinkedIn nộp sau (ưu tiên thấp).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock server 3 nền tảng theo tài liệu API công khai; đánh dấu rõ phần "chưa kiểm được vì cần app duyệt" trong PR.
