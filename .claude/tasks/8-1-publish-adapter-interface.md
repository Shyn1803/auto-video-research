# Task 8-1: Publish adapter interface + luồng chung

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 6-3 · **FR:** FR-12

## User story
As a developer, I want một interface publish chuẩn với capabilities từng nền tảng, so that thêm nền tảng mới là một adapter, và UI tự phản ánh nền tảng nào dùng được.

## Why
FR-12 kiến trúc tầng. Capabilities check (BR-3) chặn cả lớp lỗi "đăng video ngang lên nền tảng dọc" trước khi chúng thành lỗi API khó hiểu.

## Scope
**In:** `PublishAdapter` base (upload/get_status/capabilities: max_duration, formats, disclosure_supported); chuẩn hoá adapter `download` (6-3); vòng đời publishes đầy đủ; API publish/preview §8; retry backoff upload; UI tab Xuất bản mở rộng: bảng nền tảng theo provider state, form metadata prefill, khối hẹn giờ (UI — job 8-4).
**Out:** adapter YouTube (8-2), TikTok/FB/LinkedIn (10-3); analytics (8-5).

## Business Rules
1. Platform inactive không ẩn — hiện kèm lý do + hướng dẫn.
2. Metadata sửa tại màn publish chỉ áp cho lần đăng đó — không sửa script version.
3. Capabilities check trước đăng (format/duration/disclosure) → chặn kèm giải thích + gợi ý.
4. Retry upload tối đa 3 với backoff; hết → failed + notify; retry tay được.

## Acceptance Criteria
1. **(happy)** Chỉ download active → bảng đúng wireframe; vòng đời pending→published ghi đủ.
2. **(biên/BR-3)** Đăng 16:9 lên platform dọc-only (mock) → chặn + gợi ý bản 9:16.
3. **(lỗi/BR-4)** Upload fail 3 lần (mock) → failed + notify; nút retry chạy lại.
4. **(quyền)** 🅞 đúng; creator khác 403.
5. **(BR-2)** Sửa title lúc đăng → publishes.title khác script; script version nguyên vẹn.

## Data & API
Bảng: publishes. Endpoints §8. Contract change: không.

## Decisions already locked
- Vòng đời publish: pending→scheduled→uploading→published/failed (schema sẵn) — không thêm trạng thái.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock adapter "fakeplatform" với capabilities cấu hình được (dùng test BR-3 đủ nhánh, tái dùng ở 10-3).
