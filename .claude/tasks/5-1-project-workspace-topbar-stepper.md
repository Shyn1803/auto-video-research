# Task 5-1: Project workspace — topbar + stepper + khung Phân cảnh

**Points:** 5đ · **Epic:** 5 — Workspace UI · **Depends:** 2-1, 2-3, 1-5 · **FR:** FR-09

## User story
As a Content Creator, I want một khung làm việc nhất quán với stepper luôn cho biết tôi đang ở đâu và cần làm gì, so that không bao giờ lạc trong quy trình 5 bước.

## Why
"Pipeline là xương sống UI" — nguyên tắc #1 của `docs/design/ux-design.md`. Khung mọi story UI khác lắp vào.

## Scope
**In:** layout `/projects/{id}`: topbar (← Dự án, tên, StatusBadge, slot VersionSwitcher); PipelineStepper 5 trạm đủ trạng thái (design-system §3.2); màn Phân cảnh 3 cột (sidebar thumbnail + SceneForm schema-driven + ScenePlayer); header "Đã duyệt x/y"; ApproveBar chuẩn §3.3; autosave 1s; 422→inline theo field_path; chế độ xem-lại readonly + "Sửa lại từ đây".
**Out:** controls chi tiết (5-2); AssetPicker (5-3); scene ops (5-4); RunningState (5-8); VersionSwitcher nội dung (5-9).

## Business Rules
1. Trạm done click → readonly + nút "Sửa lại từ đây" → confirm liệt kê bước sẽ stale → mở chế độ sửa.
2. Trạm locked click → tooltip điều kiện mở.
3. Autosave lỗi mạng → badge "⚠ chưa lưu" + retry tự động + giữ nội dung local — không mất chữ đang gõ.
4. SceneForm sinh từ JSON Schema — field mới trong schema tự có control mặc định theo type.
5. Duyệt từng cảnh ghi trạng thái; header đếm x/y realtime.
6. **(PO 2026-07-11)** Stepper **5 trạm** (Nghiên cứu → Nội dung → Phân cảnh → Hoàn thiện → Xuất bản); trạm done còn cảnh báo hiển thị **✓⚠** + tooltip liệt kê.
7. Topbar có nút **▶ Xem bản mới nhất**; tên project ⓘ mở ProjectDrawer (5-10).

## Acceptance Criteria
1. **(happy)** Sửa field → Player <100ms + autosave version mới + badge đúng chu trình.
2. **(biên/BR-1)** Click trạm ✓ Kịch bản → readonly; "Sửa lại từ đây" → confirm nêu bước sẽ lỗi thời → vào sửa được.
3. **(lỗi/BR-3)** Ngắt mạng khi gõ → ⚠ chưa lưu; nối lại → tự lưu; chữ không mất (Playwright offline test).
4. **(biên/BR-4)** Thêm field optional vào schema fixture → form tự render control.
5. **(a11y)** Điều hướng stepper bằng phím đủ; NVDA đọc trạng thái trạm.
6. **(states)** Đủ 5 states có test/screenshot trong PR.

## Data & API
Endpoints: GET/PUT scenes (§6), approve scene (mới — `POST scenes/{id}/approve` → cập nhật api-spec §6); GET project tổng hợp trạng thái stepper. Contract change: **có**.

## Decisions already locked
- Duyệt theo từng cảnh (không duyệt cả bước một nút).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + Playwright chính (khung + offline + keyboard); vitest cho form generator.
