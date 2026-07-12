# Task 4-1: LangGraph skeleton + checkpoint + human gate

**Points:** 5đ · **Epic:** 4 — Pipeline AI · **Depends:** 1-4, 1-5, 1-6, 3-2 · **FR:** AR-2

## User story
As a system, I want pipeline có checkpoint bền và điểm dừng chờ người duyệt, so that crash không mất việc đã làm và user kiểm soát từng bước như SRS cam kết.

## Why
Bộ khung của toàn bộ giá trị sản phẩm (human-in-the-loop + resume). Mọi node sau chỉ là "điền thịt" vào khung này — see [patterns/langgraph-pipeline-node.md](../patterns/langgraph-pipeline-node.md).

## Scope
**In:** graph 6 node (produce/render stub); state Pydantic→JSONB; checkpoint `langgraph-checkpoint-postgres`; interrupt sau mỗi node (Mode 2); map node↔state machine (1-4); API `steps/{step}/run` + `approve` + `GET runs/{id}`; retry backoff/node (3 lần); correlation_id = run_id xuyên log/event.
**Out:** logic node thật (4-3–4-6); cancel (4-7); mode không-interrupt (7-2).

## Business Rules
1. Một project chỉ 1 run active — POST run khi đang chạy → 409.
2. Approve chỉ hợp lệ khi run interrupt đúng node đó (chống double-approve/race).
3. Node hoàn thành → checkpoint + step_version ghi **cùng transaction** (atomic — không bao giờ lệch nhau).
4. Retry hết 3 lần → project FAILED(reason=node lỗi cuối), giữ previous_status (1-4 BR-3).

## Acceptance Criteria
1. **(happy)** Run → interrupt sau research → project NEED_REVIEW → approve → node kế chạy; SSE đủ chuỗi sự kiện.
2. **(biên)** Kill process giữa node write → restart → resume đúng write; research không chạy lại.
3. **(lỗi/BR-1,2)** POST run khi đang chạy → 409; approve node đã qua → 409.
4. **(biên/BR-3)** Giả lập crash giữa "node xong, đang ghi" → sau restart: checkpoint và step_version nhất quán.
5. **(CI)** Integration skeleton node-stub xanh.

## Data & API
Bảng: `langgraph_checkpoints` (lib tự tạo qua migration); runs tracked qua checkpoint + status_history. Endpoints: api-spec §2. Contract change: không.

## Decisions already locked
- ⏳ Interrupt sau **mọi** node ở Mode 2 kể cả produce (user có thể muốn xem asset/audio trước render).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fault injection test cho BR-3 (raise sau ghi 1 trong 2); resume test chạy trong CI mỗi PR đụng pipeline (quan trọng nhất task này).
