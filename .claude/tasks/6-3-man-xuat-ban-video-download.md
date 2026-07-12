# Task 6-3: Màn Xuất bản — video + download + metadata

**Points:** 3đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 6-2 · **FR:** FR-12

## User story
As a Content Creator, I want xem video cuối, tải về và copy sẵn tiêu đề/mô tả/tags, so that đăng tay lên bất kỳ nền tảng nào trong 1 phút.

## Why
Đường publish "luôn hoạt động" (FR-12 tầng download) — giá trị dùng được ngay từ M4 khi chưa có nền tảng nào duyệt API.

## Scope
**In:** player video final theo format; Download presigned (per-format); metadata copy (từng cái + tất cả); publish record `download` → PUBLISHED; bảng nền tảng đúng trạng thái provider (✓/⚠ chờ duyệt/○ chưa key — hàng khác của 8-1/10-3 hiện đúng nhãn từ giờ).
**Out:** đăng tự động (8.x); hẹn giờ (8-4).

## Business Rules
1. Presigned URL 24h; hết → nút "Tạo link mới".
2. Lần tải đầu (format bất kỳ) → PUBLISHED (1 lần chuyển); tải tiếp không đổi trạng thái.
3. Màn truy cập được từ READY trở đi (kể cả PUBLISHED — xem lại/tải lại).
4. Metadata copy gồm cả attribution BGM nếu track yêu cầu (6-5 BR-2).

## Acceptance Criteria
1. **(happy)** Tải 9:16 → file đúng; PUBLISHED; quay lại tải 16:9 vẫn được, trạng thái không đổi.
2. **(biên/BR-1)** URL 24h+ → "Tạo link mới" hoạt động.
3. **(copy/BR-4)** "Copy tất cả" đủ 3 phần + attribution khi có.
4. **(states)** Chưa READY → trạm lock đúng; render lỗi → error state đúng.

## Data & API
Bảng: publishes. Endpoints: §7 video + §8 publish-preview/publish(download). Contract change: không.

## Decisions already locked
- ⏳ PUBLISHED khi tải (không cần xác nhận "đã đăng thật").

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + Playwright flow M4 end-to-end kết thúc tại đây — trở thành E2E chuẩn của test-plan.
