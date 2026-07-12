# Task 5-2: Edit controls — text/màu/animation/layout/giọng

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1 · **FR:** FR-09

## User story
As a Content Creator, I want chỉnh chữ, màu, hiệu ứng, bố cục và lời đọc bằng control trực quan, so that tuỳ biến cảnh mà không hiểu gì về JSON.

## Why
FR-09 phần "sửa mọi thứ". Dry-run đổi layout (BR-1) chuyển lỗi validate từ "bực mình sau khi lưu" thành "quyết định có thông tin trước khi đổi".

## Scope
**In:** controls text (content marker bold, role, position, màu + highlight picker), animation (type + delay slider); đổi layout với dry-run cảnh báo phần tử bị cắt; voice panel (textarea, giọng nam/nữ, tốc độ).
**Out:** đổi ảnh (5-3); font tuỳ chỉnh (v1.1).

## Business Rules
1. Đổi layout vi phạm ràng buộc → dialog liệt kê đích danh phần tử bị bỏ; huỷ = nguyên trạng.
2. Color picker preset theo theme + custom hex có cảnh báo contrast (không chặn).
3. Sửa voice text sau produce → audio cũ đánh dấu stale + badge "giọng đọc sẽ tạo lại".
4. Bold marker nhập bằng nút **B** trên selection (user không cần gõ `**`).

## Acceptance Criteria
1. **(happy)** Mỗi control đổi → Player phản ánh ngay; lưu đúng schema.
2. **(biên/BR-1)** Ghi đè MediaText (3 text) → MediaFull (max 2): dialog nêu "chữ 't3' sẽ bị bỏ"; huỷ giữ nguyên.
3. **(biên/BR-3)** Sửa lời đọc cảnh đã produce → badge cảnh báo hiện; produce lại chỉ cảnh này (nối 6-1 BR-4).
4. **(BR-4)** Bôi đen chữ bấm B → content có marker + Player highlight.
5. **(a11y)** Slider delay điều khiển bằng ←/→.

## Data & API
PUT scene (sẵn). Contract change: không.

## Decisions already locked
- Không WYSIWYG kéo vị trí tự do — position ngữ nghĩa (top/center/bottom) đúng spec schema v1 (chống scope creep).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + vitest control-level; Playwright cho dialog dry-run; contrast check dùng lib sẵn (không tự viết).
