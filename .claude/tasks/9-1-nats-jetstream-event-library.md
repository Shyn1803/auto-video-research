# Task 9-1: NATS JetStream + event library

**Points:** 5đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 1-6, 6-2 · **FR:** AR-5

## User story
As a system, I want event bus bền với dedupe và DLQ, so that job phân phối tin cậy giữa các service và message lỗi không bao giờ biến mất lặng lẽ.

## Why
[decisions/0003-nats-jetstream.md](../decisions/0003-nats-jetstream.md). Nhờ 1-6 giữ interface từ đầu, task này là "swap transport" chứ không phải viết lại — trả cổ tức của kỷ luật contract. **Do not start this epic before Epic 6 (M4) is done — contract stability before extraction is deliberate sequencing, see [tasks/README.md](README.md).**

## Scope
**In:** NATS vào compose prod; provision streams/subjects idempotent theo `docs/specs/event-catalog.md`; event lib (envelope, publisher/consumer helper: ack, max_deliver=5, DLQ publish, dedupe Msg-Id); swap in-process bus khi `NATS_URL` set; CI matrix 2 chế độ.
**Out:** NATS cluster 3 node (v1.1); tách worker (9-2/9-3); UI queue (9-4).

## Business Rules
1. Unset NATS_URL → in-process, toàn test xanh (dev không cần NATS).
2. Envelope schema_version — consumer gặp major lạ → DLQ kèm lý do, không đoán.
3. NATS mất kết nối → publisher buffer + reconnect; quá ngưỡng (config) → lỗi rõ ràng, không nuốt event.
4. Provision script chạy lại an toàn (idempotent) — là một phần migrate/deploy.

## Acceptance Criteria
1. **(happy)** NATS_URL set → events qua JetStream; SSE bridge FE không đổi hành vi.
2. **(biên)** Consumer không ack → redeliver; 5 lần → DLQ; Msg-Id trùng → xử lý 1 lần.
3. **(biên/BR-1)** CI matrix in-process + NATS đều xanh.
4. **(lỗi/BR-3)** NATS down 30s giữa run → reconnect, đếm event 2 đầu khớp.
5. **(BR-2)** Event schema 2.0.0 giả → DLQ lý do "schema không hỗ trợ".

## Data & API
Hạ tầng: streams RENDER/MEDIA/PUBLISH/EVENTS. Contract change: không (catalog là spec sẵn).

## Decisions already locked
- ⏳ Buffer reconnect 100 events / 10s — quá → lỗi.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + Testcontainers NATS trong integration; đo "đếm 2 đầu" bằng counter publisher/consumer.
