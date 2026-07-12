# Task 7-3: Gate config + thống kê chính xác

**Points:** 3đ · **Epic:** 7 — Automation · **Depends:** 7-2, 8-3 · **FR:** Mode 1 gate

## User story
As an Admin, I want nâng mức tự động của Mode 1 dựa trên thống kê độ chính xác thực tế, so that quyết định "cho máy tự đăng" dựa trên dữ liệu chứ không cảm tính.

## Why
Cơ chế "earn trust" của SRS §2: `off → pass_only → on` theo tỉ lệ PASS-đúng 30 ngày ≥95%. Câu trả lời cho rủi ro lớn nhất của sản phẩm (auto-publish nội dung sai).

## Scope
**In:** enforcement `MODE1_AUTOPUBLISH` 3 mức tại bước publish; đo "PASS có đúng không": approve nguyên trạng = đúng, sửa fact = sai (định nghĩa BR-1); thống kê 30 ngày + banner khuyến nghị trên tab Providers; đổi gate = admin action có confirm + audit.
**Out:** auto-publish thực tế cần 8-3 (trước đó nghiệm thu logic với platform download); ML threshold tự điều chỉnh.

## Business Rules
1. "sửa fact" đo được = sau READY user sửa số liệu/tên/ngày trong script HOẶC override claim; sửa hình/chữ trang trí/timing không tính.
2. Nâng gate chặn khi mẫu <20 video ("chưa đủ dữ liệu").
3. Gate `on` → chỉ PASS auto-publish; WARN luôn dừng (đúng SRS).
4. Hạ gate luôn được phép không điều kiện (chiều an toàn).

## Acceptance Criteria
1. **(happy)** pass_only: video PASS → auto-publish; WARN → READY chờ.
2. **(biên/BR-1)** Sau READY sửa số trong script → ghi nhận "sai"; sửa màu chữ → không ghi nhận.
3. **(biên/BR-2)** 12 video → nút nâng disabled "cần ≥20"; đủ 20 + ≥95% → enabled.
4. **(audit)** Đổi gate ghi ai/lúc/từ→đến; confirm nêu hệ quả.
5. **(BR-4)** Hạ on→off luôn được, không điều kiện.

## Data & API
Bảng: thêm `accuracy_events(project_id, was_correct, detected_by, at)`; endpoint stats + đổi gate 🅐 → cập nhật api-spec §9 (+DB schema). Contract change: **có**.

## Decisions already locked
- Ngưỡng 95% / 30 ngày / tối thiểu 20 mẫu (SRS §2 + bổ sung mẫu tối thiểu).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + simulate 30 ngày dữ liệu bằng seed; định nghĩa BR-1 cần test kỹ từng nhánh (chỗ dễ cãi nhau nhất).
