# Task 7-5: Dashboard "Chờ duyệt hôm nay" + duyệt nhanh

**Points:** 3đ · **Epic:** 7 — Automation · **Depends:** 7-2, 8-3, 6-3 · **FR:** Mode 1, FR-01

## User story
As a PO, I want hàng đợi video chờ duyệt ngay đầu dashboard với nút duyệt-và-đăng 1 click, so that 2 phút mỗi sáng — kể cả từ điện thoại — xử lý xong tin hàng ngày.

## Why
Gap từ wireframe v2. Màn ROI cao nhất của Mode 1: toàn bộ giá trị "tự động 95%" quy về 1 cú click cuối cùng của con người. Yêu cầu mobile là ngoại lệ cố ý của chiến lược desktop-first.

## Scope
**In:** khối queue card (READY mode daily_news + mọi NEED_REVIEW): xem video inline (modal player), "✓ Duyệt & đăng" (READY+PASS+platform active → publish theo config), "Mở duyệt" (deep-link đúng tab); sort cũ nhất trước; badge đếm trên sidebar; **responsive <1024px cho riêng màn này**.
**Out:** duyệt hàng loạt; push notification (7-4 lo).

## Business Rules
1. "Duyệt & đăng" chỉ hiện khi PASS + platform active; ngược lại chỉ "Mở duyệt".
2. Duyệt nhanh ghi audit như duyệt thường (actor, thời điểm) + tính vào thống kê 7-3.
3. Queue rỗng → khối ẩn hẳn (không chiếm chỗ).
4. Card hiện verdict + tiêu đề + thời lượng + thumbnail — đủ ra quyết định không cần mở.

## Acceptance Criteria
1. **(happy)** Sáng 2 video → khối 2 card đủ thông tin BR-4; "Duyệt & đăng" → publish chạy → card biến mất + toast.
2. **(biên/BR-1)** Video WARN → chỉ "Mở duyệt"; deep-link tới claim đang chờ.
3. **(mobile)** 390px: xem video + duyệt được (Playwright viewport); từ link Telegram (7-4) → màn này mở đúng.
4. **(quyền)** Creator thấy queue project mình; admin thấy tất.
5. **(BR-2)** Duyệt nhanh → audit + accuracy_event ghi đúng.

## Data & API
Endpoint: `GET /projects/review-queue` (mới — tổng hợp 2 nguồn + verdict + next_action) → cập nhật api-spec §2; publish dùng §8. Contract change: **có**.

## Decisions already locked
- ⏳ Duyệt nhanh không cho sửa metadata (muốn sửa → "Mở duyệt").

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + Playwright mobile viewport là AC cứng; fixture queue 3 trạng thái (PASS/WARN/FAILED).
