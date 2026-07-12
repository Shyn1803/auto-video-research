# Task 1-3: Project CRUD + Dashboard nhóm vòng đời

**Points:** 5đ (PO 2026-07-11: +1đ thumbnail/nhóm) · **Epic:** 1 — Nền tảng · **Depends:** 1-2 · **FR:** FR-01

## User story
As a Content Creator, I want tạo/sửa/clone/lưu trữ dự án và thấy ngay việc cần làm tiếp trên mỗi dự án, so that quản lý nhiều video cùng lúc không sót việc.

## Why
Dashboard là màn vào ra nhiều nhất mỗi ngày. "Hành động tiếp theo click được" (BR-3) biến dashboard từ danh sách thành hàng đợi việc.

## Scope
**In:** CRUD projects (api-spec §2) + ownership 🅞; modal Tạo dự án (topic bắt buộc; format mặc định 9:16, chọn thêm 16:9; giọng mặc định nữ + nghe thử); Dashboard khối "Dự án của tôi" (card: tên + StatusBadge + hành động tiếp theo), filter/paging/search; clone; archive/unarchive; empty state first-run.
**Out:** khối "Chờ duyệt hôm nay" (7-5); mini-stepper trên card; xoá vĩnh viễn dữ liệu (chỉ archive trong v1).

## Business Rules
1. DELETE chỉ khi DRAFT chưa có step_version; ngược lại 409 + UI gợi ý Lưu trữ.
2. Clone copy version mới nhất mọi step + asset refs; không copy renders/publishes; tên mặc định "{tên} (bản sao)".
3. "Hành động tiếp theo" suy từ status: NEED_REVIEW→"Mở duyệt ▸", RUNNING→"● {bước} x%", READY→"Xem & đăng", FAILED→"Xem lỗi & chạy tiếp".
4. Archive ẩn khỏi list mặc định; "Xem tất cả" gồm lưu trữ + khôi phục; project archive read-only.
5. Nghe thử giọng trong modal tạo gọi tts-preview với câu mẫu cố định (cache).
6. **(PO 2026-07-11)** Dashboard nhóm theo vòng đời, thứ tự: Chờ duyệt (7-5) → Đang chạy → Đang làm dở → Đã đăng 7 ngày; nhóm rỗng ẩn; card có thumbnail (frame cảnh 1) + "bước x/5 · tên trạm", **không** mini-stepper.
7. Filter theo Mode (Tất cả / Của tôi / Tự động).

## Acceptance Criteria
1. **(happy)** Tạo topic "GPT-5.5" (9:16, giọng nữ) → card DRAFT; mở → workspace stepper chỉ Nghiên cứu mở.
2. **(biên/BR-2)** Clone project 8 cảnh → đủ version+scene, DRAFT, không renders; tên "(bản sao)".
3. **(lỗi/BR-1)** DELETE project có script → 409; toast gợi ý Lưu trữ.
4. **(quyền)** Creator A không thấy project B (403).
5. **(empty)** User mới → empty state đúng wireframe.
6. **(BR-3)** Seed 4 project 4 status → 4 nhãn hành động đúng, click đến đúng nơi.

## Data & API
Bảng: `projects`. Contract change: **có** — thêm `next_action {label, href}` vào response list → cập nhật api-spec §2.

## UI/UX
Wireframe Dashboard + Tạo dự án (modal). States: default/loading(skeleton)/empty(CTA)/error/disabled N/A. A11y: card link, modal focus-trap ESC, search label.

## Decisions already locked
- Giọng đọc là thuộc tính project (per-scene override vẫn có ở editor).
- ⏳ Giới hạn 50 project active/user.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + Playwright: tạo → thấy card → mở.
