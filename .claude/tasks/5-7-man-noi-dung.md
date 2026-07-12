# Task 5-7: Màn "Nội dung" (Dàn ý collapse + Kịch bản)

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 4-5, 5-8 · **FR:** FR-05, FR-06

## User story
As a Content Creator, I want biên tập dàn ý và kịch bản với nguồn tham chiếu bên cạnh, so that sửa nội dung nhanh mà không rời ngữ cảnh fact đã kiểm chứng.

## Why
FR-05/06 phía user. Banner warning từ node (lệch số, title cắt — 4-5) phải "đập vào mắt" tại đây — chốt chặn con người cuối trước khi nội dung thành hình.

## Scope
**In:** Dàn ý 7 card section editable; Kịch bản (title/description/tags + voice_over textarea); panel phải fact PASS ghim + [source] link; "Sinh lại bằng AI" → RunningState; autosave; render `warnings[]` từ version content thành banner + "xem chỗ lệch".
**Out:** rich-text đầy đủ (plain + marker đủ v1); đếm thời lượng đọc chính xác (ước tính từ ký tự).

## Business Rules
1. Warnings hiện banner vàng đầu màn; loại `number_mismatch` có nút highlight đúng con số lệch 2 phía.
2. `[source_id]` render link → mở panel nguồn tương ứng.
3. Ước tính thời lượng đọc hiện cạnh voice_over — lệch mục tiêu ±20% → nhắc nhẹ.

## Acceptance Criteria
1. **(happy)** Sửa → version mới autosave; approve → RunningState bước kế.
2. **(biên/BR-1)** Version có number_mismatch → banner + highlight đúng số 2 phía.
3. **(BR-3)** Voice_over dài gấp rưỡi mục tiêu → nhắc thời lượng.
4. **(a11y)** Screen reader đọc banner khi vào màn.

## Data & API
Endpoints: versions PUT/GET (§3). Contract: `warnings[]` đã chuẩn ở 4-5.

## Decisions already locked
- **Gộp thành 1 trạm "Nội dung"** (PO 2026-07-11): dàn ý panel trên cùng — mở rộng khi chờ duyệt, collapse sau duyệt; kịch bản bên dưới. Backend giữ nguyên 2 step/2 version/2 gate (4-5 không đổi). Sửa dàn ý sau khi kịch bản tồn tại → kịch bản stale (cascade 1-5).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture version có warnings mỗi loại; Playwright flow sửa → sinh lại → so version.
