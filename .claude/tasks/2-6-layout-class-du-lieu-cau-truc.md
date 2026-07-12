# Task 2-6: 6 layout class dữ liệu & cấu trúc — constraint preset + motion preset

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-1, 2-2, 2-4 (timestamps) · **FR:** FR-08, FR-11

## User story
As a Content Creator, I want các bố cục chuyên cho số liệu, so sánh, danh sách, trích dẫn và code — với hiệu ứng chuyển động phù hợp từng loại nội dung, so that video tin công nghệ đa dạng và truyền tải đúng bản chất thông tin.

## Why
Feedback PO 2026-07-11 + [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md): mỗi layout class = constraint preset (flexbox) + motion preset theo loại component. Dựng 6 class nhóm Dữ liệu + Cấu trúc (`BigNumber`, `Chart`, `VersusTable`, `List`, `Quote`, `Code`) + bảng motion preset dùng chung cho cả 5 class cơ bản của 2-2.

## Scope
**In:** 6 composition = constraint preset flex (slots, gap, padding) + responsive rules 2 format; motion preset table + renderer cho MotionPlan: mỗi track = `<Sequence from>` + Animated, sync_points = interpolate mốc tuyệt đối — countUp kết thúc theo `end_by_ms`, list stagger theo `enter_at_ms` từng item; áp cả cho 5 class 2-2; Pydantic + Zod 6 element types (mở rộng 2-1); SceneForm control tương ứng; gallery override trong editor; render test matrix 11 class × 2 format.
**Out:** chart line/pie, Timeline/Gallery class, lower_third (v1.1); solver tổng quát (v1.1); classifier (4-6).

## Business Rules
1. Dữ liệu chart/table/number là inline trong Scene JSON, không fetch ngoài; constraints theo spec §3.6 (points 2-6, rows 2-4, items 3-5…).
2. `quote_block` bắt buộc `source_id` truy được fact-check; không nguồn → validator chặn (strict) / engine hạ class về TextFocus (auto_fix + warning).
3. List stagger khớp voice: item i xuất hiện khi từ đầu tiên của ý i được đọc; không có timestamps → fallback 90ms/item (dial 4-7) hoặc 60ms/item (dial 8-10) — `docs/specs/video-taste.md` §3.
4. Số trong number/chart/table phải khớp fact đã kiểm chứng — mapper 4-6 chỉ điền từ claims/key_facts, kèm `[source_id]`.
5. Mỗi class mới pass đủ render test 2 format + auto-shrink trước khi được bật trong rule table của Layout Classifier (4-6) — AI không biết đến danh sách layout.

## Acceptance Criteria
1. **(happy)** Fixture 6 layout render 2 format đúng spec; PO duyệt visual (12 ảnh); count-up/bar-grow/stagger đúng nhịp.
2. **(biên/BR-3)** List 4 items voice 8s → xuất hiện đúng lúc từng ý được đọc.
3. **(biên/BR-2)** quote không source_id: strict → 422; auto_fix → hạ TextFocus + warning.
4. **(lỗi)** chart 7 points → validator chặn đúng field_path; table label 25 ký tự → 422.
5. **(pipeline)** Bật 6 class trong rule table classifier → storyboard 3 topic thật (Ollama) chọn ≥3 class mới hợp lý.
6. **(editor)** Ghi đè sang Chart trong gallery → form đổi sang bảng nhập points; Player cập nhật ngay.

## Decisions already locked
- 6 layout thuộc v1 (PO 2026-07-11). Lịch: tuần 4-6, sau M1, không chặn critical path.
- ⏳ Màu chart: 1 màu primary + highlight — không palette nhiều màu.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixtures vào bộ share (2-1); render test matrix nightly 22 tổ hợp; unit stagger-mapping là pure function.
