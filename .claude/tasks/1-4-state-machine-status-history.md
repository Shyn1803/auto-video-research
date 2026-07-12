# Task 1-4: State machine + status_history

**Points:** 5đ · **Epic:** 1 — Nền tảng · **Depends:** 1-3 · **FR:** FR-17

## User story
As a system, I want mọi chuyển trạng thái project đi qua một cổng duy nhất có kiểm tra và audit, so that pipeline resume chính xác sau lỗi và mọi thay đổi truy vết được.

## Why
FR-17 là xương sống độ tin cậy: LangGraph resume (4-1), hàng đợi duyệt (7-5), gate Mode 1 (7-3) đều đọc status. Một chỗ ghi status "chui" là một bug resume tương lai.

## Scope
**In:** ma trận cạnh FR-17 dạng data (một nguồn cho code+test+docs); service `ProjectStateMachine.transition()` (validate cạnh, ghi history actor/reason, phát event `project.status`); `previous_status` cho FAILED/CANCELLED; API `GET status-history`.
**Out:** UI timeline lịch sử (5-9); cạnh CANCELLED chi tiết (4-7 bổ sung, dùng cùng service).

## Business Rules
1. Mọi write `projects.status` ngoài service bị cấm — enforced bằng CI grep + code review.
2. Actor bắt buộc: user uuid | `system` | tên node; reason bắt buộc với cạnh bất thường (→FAILED, override).
3. FAILED/CANCELLED giữ `previous_status`; resume chỉ về đúng trạng thái đó.
4. ARCHIVED đến từ trạng thái kết thúc (PUBLISHED/FAILED/DRAFT/READY); không từ trạng thái đang chạy.
5. Transition idempotent-safe: chuyển tới trạng thái hiện tại → no-op trả 200 (chống double-click), trừ cạnh có side-effect.

## Acceptance Criteria
1. **(happy)** APPROVED→PRODUCING: status đổi + history đủ actor/reason + event phát.
2. **(biên/BR-3)** FAILED từ RENDERING → resume → RENDERING, không về DRAFT.
3. **(lỗi)** PUBLISHED→RESEARCHING → 409 STATE_CONFLICT body chuẩn.
4. **(biên/BR-5)** Gọi 2 lần cùng transition → lần 2 no-op 200, history 1 dòng.
5. **(test)** Parametrize 100% cạnh hợp lệ + đại diện cạnh cấm; CI grep pass.

## Data & API
Bảng: cột `status` + `status_history`. Event: `project.status`. Contract change: không.

## Decisions already locked
- PUBLISHING tách khỏi READY (giữ nguyên FR-17 v3 SRS).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + ma trận cạnh export ra bảng trong PR; property test (random walk chỉ đi cạnh hợp lệ không bao giờ raise).
