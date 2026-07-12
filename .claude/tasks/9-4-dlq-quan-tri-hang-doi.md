# Task 9-4: DLQ + Quản trị › Hàng đợi

**Points:** 3đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-1, 7-4 · **FR:** NFR-3

## User story
As an Admin, I want thấy message lỗi, hiểu lý do và replay sau khi sửa, so that sự cố hàng đợi xử lý trong phút thay vì mò log container.

## Why
DLQ không có UI = hố đen vận hành. `docs/runbook.md` §3.5 đã viết quy trình — task này cho nó công cụ.

## Scope
**In:** API queue stats (pending/redeliver/DLQ per stream), payload viewer (che secret), replay, xoá (audit); tab Quản trị › Hàng đợi (wireframe); alert DLQ>0 (7-4).
**Out:** replay hàng loạt có filter (v1.1); sửa payload trước replay (nguy hiểm — không cho).

## Business Rules
1. Replay message đã thành công → no-op (idempotency downstream).
2. Xoá message → audit (ai/lúc/payload hash).
3. Payload viewer che field nhạy cảm theo denylist (token/key pattern).
4. Alert DLQ gộp ("DLQ có 3 message") không bắn từng cái.

## Acceptance Criteria
1. **(happy)** Message vào DLQ → alert Telegram (gộp) → xem payload → sửa nguyên nhân → replay → xử lý OK, DLQ trống.
2. **(biên/BR-1)** Replay message đã ok trước đó → no-op không side-effect.
3. **(BR-3)** Payload chứa "api_key=..." → hiển thị che.
4. **(quyền)** Admin only; audit xoá query được.

## Data & API
Endpoints §9 queue/dlq. Contract change: không.

## Decisions already locked
- Không sửa payload trước replay (chống tạo dữ liệu tay ngoài luồng).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + seed DLQ bằng consumer cố tình fail; test denylist che secret giữ vĩnh viễn.
