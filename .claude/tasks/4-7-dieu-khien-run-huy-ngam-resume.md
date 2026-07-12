# Task 4-7: Điều khiển run — huỷ / chạy ngầm / resume

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-1 · **FR:** NFR-3

## User story
As a Content Creator, I want huỷ một bước AI đang chạy hoặc để nó chạy ngầm, so that tôi không bị giam trong màn chờ khi đổi ý hoặc muốn làm việc khác.

## Why
Gap từ design-critique: RunningState có nút Huỷ nhưng không API nào đứng sau. Không có task này, cách duy nhất dừng một run sai là chờ nó chạy hết.

## Scope
**In:** `POST runs/{id}/cancel`; abort an toàn (kết thúc sau LLM call hiện tại — không giết giữa transaction 4-1 BR-3); cạnh state machine RUNNING→CANCELLED (+previous_status); resume sau cancel = run mới từ checkpoint; "chạy ngầm" = FE rời màn (SSE sẵn — không API mới).
**Out:** pause/resume giữa node (checkpoint đủ); huỷ hàng loạt.

## Business Rules
1. Cancel best-effort có xác nhận: trạng thái CANCELLED chỉ khi node dừng thật (event xác nhận); UI hiện "đang huỷ…" trong lúc chờ (tối đa ~30s = 1 LLM call).
2. Chi phí đã phát sinh vẫn ghi usage.
3. Cancel không xoá version đã tạo trước đó.
4. Cancel run đã kết thúc → 409.

## Acceptance Criteria
1. **(happy)** Cancel giữa research → "đang huỷ…" → CANCELLED ≤30s; resume → run mới tiếp từ checkpoint.
2. **(biên)** Cancel đúng lúc node vừa xong → run kết thúc bình thường tại interrupt (không race).
3. **(lỗi/BR-4)** Cancel run xong → 409.
4. **(UI)** Rời màn khi chạy → dashboard card ●%; quay lại đúng RunningState; sau cancel card hiện "Đã huỷ — chạy tiếp?".

## Data & API
Cạnh mới state machine (cập nhật ma trận 1-4 + test); endpoint mới → cập nhật api-spec §2. Event mới: `run.cancelled` → cập nhật event-catalog.

## Decisions already locked
- ⏳ Không hard-kill LLM call đang bay (chờ xong call hiện tại) — đơn giản, an toàn transaction.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + race test (cancel vs node-finish) chạy lặp 20 lần trong CI (flaky-hunter).
