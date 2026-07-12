# Task 10-2: Bộ template 2-3

**Points:** 3đ · **Epic:** 10 — Release · **Depends:** 2-2 · **FR:** FR-11

**⚠ Buffer cắt đầu tiên nếu trễ (docs/plan.md §5) — không chặn luồng nào khác nếu deprioritized.**

## User story
As a Content Creator, I want chọn giữa vài phong cách hình ảnh, so that video của kênh không bị một màu khi đăng hàng ngày.

## Why
Rủi ro "mass-produced content" bị nền tảng giảm reach (SRS §12) — đa dạng theme bổ sung cho cơ chế chống lặp layout (4-6 BR-9) đã enforce sẵn ở mọi theme.

## Scope
**In:** 2 theme mới (sáng / gradient động) cùng contract Scene JSON + `supportedSchemaRange`; mỗi theme khai đủ dial `motion_intensity`/`visual_density`/`accent_saturation_max`/`radius_scale` (**bắt buộc, không theme "mặc định ngầm"** — see [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md)); ví dụ: Sáng-tối-giản `(4,3,0.6,soft-16px)`, Gradient-động `(8,4,0.8,pill)`; theme cấp project (chọn khi tạo + đổi trong Phân cảnh có preview); render test matrix mở rộng.
**Out:** theme marketplace/tuỳ chỉnh màu per-project (v1.1); font riêng (v1.1).

## Business Rules
1. Đổi theme không đổi Scene JSON — chỉ mapping visual.
2. Đổi theme → mọi cảnh dirty; cảnh báo "8 cảnh sẽ render lại" trước khi áp.
3. Theme mới phải pass toàn bộ render test matrix (11 layout × 2 format) trước khi vào danh sách chọn.
4. **(video-taste.md §4.3)** 1 accent color/theme (saturation ≤ `accent_saturation_max`), 1 `radius_scale` — áp cho highlight_color, chart highlight point, winner badge trong toàn bộ scene của video; validator cảnh báo nếu scene tự ý set màu ngoài accent theme.

## Acceptance Criteria
1. **(happy)** 3 video cùng nội dung 3 theme khác biệt rõ (PO duyệt).
2. **(biên/BR-2)** Đổi theme → confirm → toàn bộ dirty → render lại đủ.
3. **(BR-3)** CI matrix theme mới xanh trước khi merge.

## Data & API
projects.theme (cột mới → migration); scene render props nhận theme. Contract change: **có** — cột + trường tạo project → cập nhật api-spec §2 + DB schema.

## Decisions already locked
- Theme cấp project, không per-scene (nhất quán video).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + tái dùng khung render test 2-2; screenshot 3 theme vào PR.
