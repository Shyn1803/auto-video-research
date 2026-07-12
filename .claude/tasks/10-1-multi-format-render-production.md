# Task 10-1: Multi-format render production

**Points:** 3đ · **Epic:** 10 — Release · **Depends:** 6-2, 2-2 · **FR:** FR-11

## User story
As a Content Creator, I want một dự án xuất được cả bản dọc lẫn ngang, so that cùng một nội dung phủ TikTok/Shorts lẫn YouTube dài mà không làm lại.

## Why
FR-11 multi-format — nhân đôi giá trị mỗi video sản xuất. Template responsive đã dựng từ 2-2; task này đưa nó thành luồng sản phẩm hoàn chỉnh.

## Scope
**In:** nghiệm thu production template 16:9; projects.formats nhiều giá trị; render batch per-format (cache riêng — 6-2 engine sẵn); UI: chọn format khi tạo (1-3 có sẵn) + "＋ Tạo bản 16:9" tại tab Xuất bản; publish tự chọn format hợp nền tảng (8-1 BR-3).
**Out:** format vuông 1:1 (v1.1 nếu cần); layout khác nhau per-format (template responsive đủ).

## Business Rules
1. Thêm format sau không đụng cache format cũ.
2. Mỗi format trạng thái render/download độc lập trên UI.
3. Asset orientation: format ngang ưu tiên ảnh ngang — produce re-resolve asset thiếu orientation (cờ cảnh báo nếu phải dùng ảnh dọc crop).

## Acceptance Criteria
1. **(happy)** Cùng scene_set 2 format → PO duyệt chất lượng cả hai.
2. **(biên/BR-1)** Thêm 16:9 vào project 9:16 done → chỉ render 16:9; cache 9:16 nguyên.
3. **(BR-3)** Cảnh có ảnh dọc sang 16:9 → cờ cảnh báo crop; picker gợi ý tìm ảnh ngang.
4. **(publish)** YouTube chọn 16:9; platform dọc chọn 9:16 tự động.

## Data & API
projects.formats[] (schema sẵn); render §7 nhận formats. Contract change: không.

## Decisions already locked
- 2 format v1 (dọc + ngang) — vuông khi có nhu cầu thật.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + render test matrix layout×format từ 2-2 nâng thành nghiệm thu; kiểm tay 2 video.
