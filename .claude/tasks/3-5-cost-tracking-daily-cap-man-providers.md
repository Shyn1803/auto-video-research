# Task 3-5: Cost tracking + daily cap + màn Providers

**Points:** 2đ · **Epic:** 3 — Provider framework · **Depends:** 3-3, 3-4 · **FR:** FR-18, FR-21

## User story
As an Admin, I want một màn nhìn thấy hệ thống đang chạy bằng provider nào và tốn bao nhiêu, so that tôi kiểm soát chi phí bằng số liệu thay vì phỏng đoán.

## Why
Màn "niềm tin" của FR-21 — startup validation hiện hình. Daily cap là hàng rào cuối chống hoá đơn bất ngờ.

## Scope
**In:** llm_usage partition tháng; check cap trước call; vượt → pause pipeline + event `cost.cap_reached` + notify; tab Quản trị › Providers (ma trận StatusBadge + lý do inactive 3 loại, nút health-check, cost hôm nay/cap); API `/admin/costs?group_by=`.
**Out:** Grafana chart sâu (9-5); thống kê gate Mode 1 (7-3 — cùng màn, khối riêng).

## Business Rules
1. cap=0 nghĩa "chỉ free" (tương đương ALLOW_PAID=false runtime).
2. Chạm cap giữa run → dừng ở ranh giới node kế (không giết giữa node); status FAILED(reason=cost_cap); resume thủ công sau xử lý.
3. Ma trận phân biệt 3 lý do inactive: "thiếu key" / "kiểm tra thất bại" / "bị chặn trả phí".
4. Cost hiển thị = ước tính từ bảng giá — ghi rõ "ước tính" trên UI.

## Acceptance Criteria
1. **(happy)** 3 kịch bản env (0 key / free keys / full) → ma trận đúng từng nhãn.
2. **(biên/BR-2)** Cap chạm giữa run → dừng sau node hiện tại; resume sau reset chạy tiếp.
3. **(lỗi/BR-3)** Provider health fail → nhãn "kiểm tra thất bại"; service sống lại + bấm kiểm tra → ✓ ngay.
4. **(số liệu)** `group_by=task` khớp tổng llm_usage seed.

## Data & API
Bảng: llm_usage (partition). Endpoints: `/admin/providers`, `/admin/providers/{n}/health-check`, `/admin/costs`. Contract change: không.

## Decisions already locked
- `DAILY_COST_CAP` mặc định 0 (chỉ free) — an toàn nhất cho giai đoạn test.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + seed llm_usage 3 ngày × 3 provider × 3 task cho test costs. Note: cap drill là mục Release Checklist (10-5), task này chỉ cần test tự động.
