# Task 5-4: Scene ops — thêm/xoá/nhân bản/sắp xếp

**Points:** 2đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1 · **FR:** FR-09

## User story
As a Content Creator, I want thêm, xoá, nhân bản, kéo-thả sắp xếp phân cảnh, so that cấu trúc video theo đúng nhịp tôi muốn.

## Why
FR-09 danh sách thao tác cảnh. Điểm kỹ thuật then chốt: scene_id bất biến (see [patterns/scene-versioning.md](../patterns/scene-versioning.md)) — mọi op chỉ đổi scene_number.

## Scope
**In:** kéo-thả (dnd-kit) + nút ↑↓; thêm cảnh (chọn layout, chèn sau cảnh hiện tại); xoá (confirm); nhân bản; mọi op tạo scene_set version.
**Out:** copy cảnh giữa project (v1.1); bulk ops.

## Business Rules
1. Reorder đổi scene_number giữ scene_id (cache/diff sống nhờ điều này).
2. Xoá confirm nêu ảnh hưởng ("video ngắn đi 6s").
3. Mọi op = version mới (undo = restore 5-9).
4. Nhân bản = scene_id **mới**, nội dung copy (cache key tự khác).

## Acceptance Criteria
1. **(happy)** Kéo #4 → vị trí 2: số cập nhật, id giữ (verify qua API), version mới.
2. **(biên)** Xoá cảnh đang mở → focus cảnh kế; xoá hết → empty state.
3. **(biên/BR-4)** Nhân bản → id mới; sửa bản sao không ảnh hưởng gốc; cache key khác.
4. **(a11y)** Toàn bộ ops làm được không chuột.

## Data & API
Reorder endpoint (§6 sẵn); thêm/xoá/duplicate (§6 sẵn). Contract change: không.

## Decisions already locked
- Không undo-stack riêng trong editor — version là undo.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + vitest reducer ops; Playwright kéo-thả + keyboard path.
