# Task 5-3: AssetPicker — đổi ảnh 3 nguồn

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1, 3-2 · **FR:** FR-20

## User story
As a Content Creator, I want đổi ảnh minh hoạ từ kho dự án, máy tính, hoặc kho stock, so that cảnh có hình đúng ý mà mọi ảnh đều sạch bản quyền.

## Why
FR-20 phía user. "Mọi đường ra là asset_id có license" là hàng rào pháp lý — UI này là nơi duy nhất user đưa ảnh vào hệ thống. See [anti-patterns/render-worker-external-fetch.md](../anti-patterns/render-worker-external-fetch.md).

## Scope
**In:** modal 3 tab (Asset dự án / Tải lên / Tìm stock — query prefill từ `media_intent.query_vi`, sửa được, kết quả kèm license badge + nguồn); upload validate loại/kích thước, license=user_upload; dedupe hash; chặn URL trần UI+API; nút "Tạo bằng AI" hiện khi image_gen chain active.
**Out:** thư viện asset workspace-level (v1.1); crop/chỉnh ảnh (v1.1 — fit cover đủ).

## Business Rules
1. Kết quả stock hiện license + nguồn **trước** khi chọn.
2. Upload trùng hash → dùng lại asset cũ + thông báo nhẹ.
3. 0 key stock → tab Tìm disabled + giải thích; admin thấy link Quản trị, creator thấy "nhờ admin thêm key".
4. Ảnh chọn từ stock được Asset Worker tải về MinIO trước khi gán (render không fetch ngoài); trong lúc tải hiện "đang lấy ảnh…".

## Acceptance Criteria
1. **(happy)** Tìm "GPU datacenter" → chọn Pexels → asset có license record → Player hiện ảnh.
2. **(biên/BR-2)** Upload ảnh đã tồn tại → tái dùng, không bản ghi mới.
3. **(biên/BR-3)** 0 key → tab Tìm disabled đúng vai trò; 2 tab kia hoạt động.
4. **(bảo mật)** PUT scene chèn url trần qua API → 422.
5. **(BR-4)** Chọn ảnh stock → trạng thái "đang lấy ảnh" → gán asset_id nội bộ (render/preview không gọi pexels).

## Data & API
Endpoints: search stock (mới `GET /assets/search?q=`), upload asset (mới `POST /assets/upload`) → cập nhật api-spec §6. Contract change: **có**.

## Decisions already locked
- ⏳ Upload giới hạn 10MB, jpg/png/webp.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock asset chain; Playwright flow 3 tab; test bảo mật URL trần giữ vĩnh viễn.
