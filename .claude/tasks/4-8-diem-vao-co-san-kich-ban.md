# Task 4-8: Điểm vào "Có sẵn kịch bản"

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-4, 4-6, 1-3 · **FR:** FR-06, Mode 2

## User story
As a Content Creator, I want dán kịch bản tôi đã viết sẵn và đi thẳng tới dựng cảnh, so that video từ script có sẵn mất vài phút thay vì đi qua 2 bước nghiên cứu–viết không cần thiết.

## Why
Use case thực tế phổ biến. Quyết định giữ nguyên hàng rào: **fact-check vẫn chạy trên script dán vào** — không có đường nào ra video mà bỏ qua kiểm chứng.

## Scope
**In:** nhánh "Có sẵn kịch bản" trong modal Tạo dự án (thay nhánh "tạo trống" — đã bỏ); graph entry thứ 2: script → extract claims → factcheck (evidence tìm qua search với claim làm query) → gate như thường → storyboard; script dán lưu thành script v1 (created_by=user); title/description/tags sinh bằng AI từ script; trạm Nghiên cứu + Nội dung trên stepper hiển thị trạng thái "bỏ qua có kiểm chứng".
**Out:** import file docx/URL (v1.1); dịch script ngôn ngữ khác; nhảy thẳng tới scene JSON (storyboard vẫn chạy).

## Business Rules
1. Fact-check bắt buộc — claim FAIL vẫn chặn như luồng thường; evidence tìm bằng search chain.
2. Script dán 100-3000 ký tự; ngoài khoảng → validate với hướng dẫn.
3. Stepper: Nghiên cứu hiển thị "— bỏ qua", Nội dung hiển thị "✓ từ kịch bản của bạn" — user vẫn click vào Nội dung để sửa script.
4. project đánh dấu `entry_point=script` (phân tích 8-7 tách nhóm này khi so hiệu quả).

## Acceptance Criteria
1. **(happy)** Dán script 800 ký tự → kiểm chứng chạy → Phân cảnh có scene_set; title/tags đã sinh; script v1 created_by=user.
2. **(biên/BR-1)** Script chứa claim sai (fixture) → FAIL → NEED_REVIEW, xử lý bằng UI 5-6 như luồng thường.
3. **(biên/BR-3)** Click trạm Nội dung sau khi vào từ script → sửa được, tạo v2, storyboard stale đúng cascade.
4. **(lỗi/BR-2)** Script 50 ký tự → chặn kèm hướng dẫn.
5. **(quyền)** Như luồng tạo project thường.

## Data & API
`projects.entry_point` (cột mới, migration); `POST /projects` nhận `script_text?` → cập nhật api-spec §2 + database-schema. Graph: conditional entry (LangGraph branch) — không node mới. Contract change: **có**.

## Decisions already locked
- Thay nhánh "tạo trống" bằng nhánh này (PO duyệt 2026-07-11).
- Fact-check không thể bỏ qua kể cả entry này.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture script có 2 claim (1 đúng 1 sai); integration entry-branch với MockLLM thêm vào bộ CI pipeline.
