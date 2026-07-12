# Task 1-6: Event bus nội bộ + SSE

**Points:** 2đ · **Epic:** 1 — Nền tảng · **Depends:** 1-4 · **FR:** NFR-1, AR-5

## User story
As a frontend, I want nhận tiến độ pipeline realtime, so that user luôn thấy hệ thống đang sống và đang làm gì.

## Why
RunningState (5-8) sống bằng dữ liệu của task này. Interface bus phải giống NATS ngay từ đầu để 9-1 swap không đổi call-site.

## Scope
**In:** in-process async bus (publish/subscribe, interface = NATS publisher tương lai); `GET /events/stream` SSE (auth one-time-token qua query); hook FE `useEventStream(projectId)` + reconnect; fallback polling `GET runs/{run_id}`.
**Out:** NATS thật (9-1); notification ngoài (7-4); event persistence (fire-and-forget, FE tự sync bằng polling).

## Business Rules
1. Event format đúng api-spec §10 + envelope event-catalog từ ngày 1.
2. Stream filter theo quyền — creator chỉ nhận event project mình; admin nhận tất.
3. One-time-token TTL 60s, dùng 1 lần.
4. FE reconnect → gọi polling 1 lần để sync trạng thái bị lỡ.

## Acceptance Criteria
1. **(happy)** Run chạy → FE nhận step.progress ≤1s, đúng format.
2. **(biên/BR-4)** Ngắt mạng 10s giữa run → reconnect + sync → UI đúng trạng thái hiện tại.
3. **(quyền/BR-2)** 2 session creator khác nhau → không nhận chéo event.
4. **(lỗi/BR-3)** Token quá 60s / dùng lần 2 → 401.

## Data & API
Endpoint mới: `POST /events/token` + `GET /events/stream?token=` → cập nhật api-spec §10. Events: `project.status`, `step.progress`.

## Decisions already locked
- ⏳ Fire-and-forget chấp nhận được vì polling bù (ảnh hưởng UX mất mạng dài).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + integration 2-client test; contract test format event so với event-catalog schema.
