# Task 8-5: Analytics collector

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-3, 7-1 · **FR:** FR-13

## User story
As a Content Creator, I want số liệu video tự động cập nhật hàng ngày từ YouTube, so that biết nội dung nào hiệu quả mà không phải mở từng nền tảng chép tay.

## Why
FR-13 phần thu thập. Thiết kế "api + manual cùng schema" cho phép nền tảng chưa có API (TikTok chờ duyệt) vẫn có mặt trong dashboard từ ngày 1.

## Scope
**In:** job daily (7-1) YouTube Analytics API → metrics (views/likes/comments/watch_time/avg%); dedupe (unique index + upsert); backfill 28 ngày khi video mới connect; form nhập tay (§8 api-spec).
**Out:** dashboard (8-6); realtime metrics; nền tảng khác qua API (10-3+/v1.1).

## Business Rules
1. Chạy lại không nhân đôi (upsert theo publish/metric/ngày/source).
2. Video bị xoá trên YouTube → đánh dấu, ngừng thu, job vẫn xanh.
3. Nhập tay source=manual — job API không ghi đè manual (2 dòng song song, dashboard ưu tiên api khi cả hai).
4. Quota Analytics API riêng với upload quota — đếm riêng.

## Acceptance Criteria
1. **(happy)** Video đăng 3 ngày → 3 ngày metrics; re-run job → số dòng không đổi.
2. **(biên/BR-3)** Nhập tay TikTok views → lưu manual; job sau không đè.
3. **(lỗi/BR-2)** Video deleted (mock 404) → cờ + job xanh + các video khác thu bình thường.
4. **(backfill)** Video cũ 30 ngày mới connect → backfill 28 ngày.

## Data & API
Bảng: metrics partition. Endpoint manual entry §8. Contract change: không.

## Decisions already locked
- ⏳ Thu 06:00 hàng ngày (trước giờ PO xem 07:00+).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock Analytics API responses theo ngày; test upsert kỹ (chạy 3 lần cùng dữ liệu).
