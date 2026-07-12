# Task 5-10: ProjectDrawer — Thông tin & Cài đặt dự án

**Points:** 2đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1, 1-3, 3-5 (llm_usage) · **FR:** FR-01

## User story
As a Content Creator, I want mở nhanh thông tin tổng quan và cài đặt của dự án từ bất kỳ màn nào, so that quay lại project cũ vẫn nắm ngay tình trạng và chỉnh cấu hình không phải rời workspace.

## Why
Gap kép từ review luồng: (1) FR-01 cho sửa project nhưng không màn nào chứa PATCH; (2) vào project 2 tuần tuổi mất phương hướng. Một drawer giải cả hai, không thêm trạm/route.

## Scope
**In:** drawer trượt phải (design-system §3.7), mở từ tên project ⓘ topbar; tab **Thông tin**: tóm tắt 2 câu (AI sinh 1 lần sau research, cache), verdict tổng + link, thời lượng/số cảnh/format/giọng/theme, chi phí AI ước tính (sum llm_usage), nguồn count, hoạt động gần đây (5 dòng); tab **Cài đặt**: đổi tên/format/giọng mặc định/theme (PATCH), Nhân bản, Lưu trữ (chuyển từ dashboard card menu vào đây).
**Out:** ghi chú/comment (v1.1); chia sẻ project (ngoài scope); chỉnh sâu chi phí (màn Vận hành lo).

## Business Rules
1. Đổi giọng mặc định → cảnh chưa produce dùng giọng mới; cảnh đã produce giữ nguyên — nêu rõ trong UI khi đổi.
2. Đổi format/theme → cảnh báo hệ quả render lại (tái dùng pattern 10-2 BR-2).
3. Lưu trữ từ drawer confirm như dashboard; project archive mở drawer chỉ-đọc + nút Khôi phục.
4. Chi phí hiển thị nhãn "ước tính" (nhất quán 3-5 BR-4).

## Acceptance Criteria
1. **(happy)** Mở drawer từ màn Phân cảnh → đủ thông tin đúng dữ liệu; đóng ESC quay đúng focus.
2. **(biên/BR-1)** Đổi giọng khi 5/8 cảnh đã produce → thông báo rõ phạm vi ảnh hưởng; produce lại chỉ 3 cảnh mới dùng giọng mới.
3. **(biên/BR-3)** Project archive → drawer read-only + Khôi phục hoạt động.
4. **(lỗi)** Endpoint cost lỗi → khối chi phí hiện "không tải được" + thử lại, phần khác nguyên vẹn.
5. **(quyền)** 🅞 — creator khác 403.

## Data & API
Endpoint mới `GET /projects/{id}/summary` (gộp metadata+verdict+cost+activity) → cập nhật api-spec §2; PATCH sẵn có. Tóm tắt AI thêm output nhẹ vào node research (tier cheap, cache). Contract change: **có**.

## Decisions already locked
- ⏳ Tóm tắt 2 câu sinh 1 lần sau research (không realtime).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + vitest tab/focus-trap; integration summary endpoint (so khớp seed llm_usage).
