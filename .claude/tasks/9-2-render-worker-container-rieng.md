# Task 9-2: Render Worker container riêng

**Points:** 5đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-1 · **FR:** NFR-2

## User story
As an operator, I want render chạy ở worker riêng scale được bằng replicas, so that render nặng không nghẽn API và tăng máy là tăng throughput.

## Why
NFR-2 scale ngang. Đặt sau M4: tách khi logic đã đúng in-process — di chuyển code ổn định, không debug 2 thứ cùng lúc.

## Scope
**In:** `render-worker/` Node.js: consumer render.scene/video.request → `bundle()` **1 lần khi container khởi động** (cache serveUrl in-memory — mỗi replica bundle độc lập, không share qua network) → `selectComposition()`/`renderMedia()` mỗi job → MinIO → done event; orchestrator publish qua NATS khi bật; compose replicas; graceful shutdown (ack in-flight xong mới thoát); version handshake supportedSchemaRange → từ chối vào DLQ.
**Out:** autoscale theo queue depth (10-5 đánh giá); GPU render (không cần — Remotion CPU).

## Business Rules
1. Idempotent theo cache_key — check renders/MinIO trước render (kể cả redeliver).
2. `ack_wait` = thời gian render tối đa dự kiến × 1.5 (từ benchmark 6-4) — crash → redeliver worker khác không chờ quá lâu.
3. Worker version cũ gặp scene mới → DLQ + alert — không render sai lặng lẽ (nối 2-2 BR-3).
4. SIGTERM → dừng nhận job mới, hoàn thành job hiện tại, ack, thoát (deploy không mất job).

## Acceptance Criteria
1. **(happy)** 2 replicas, batch 8 cảnh → phân phối đều; throughput ≈2× benchmark 1 worker.
2. **(biên/BR-1)** Kill -9 worker giữa job → redeliver worker kia hoàn thành; tổng số lần render thực = số cảnh.
3. **(lỗi/BR-3)** Scene 1.1.0 vào worker ^1.0 → DLQ SCHEMA_RANGE + alert.
4. **(BR-4)** `docker compose restart render-worker` giữa batch → batch hoàn thành đủ, không job mất.
5. **(vận hành)** `--scale render-worker=4` chạy không cấu hình thêm.

## Data & API
Container mới + compose; payload theo event-catalog (đã spec). Contract change: không.

## Decisions already locked
- Worker image riêng (node + chromium Remotion cần) — không nhét vào image backend.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + chaos test kill -9 chạy lặp trong CI nightly; benchmark so sánh trước/sau tách (không regression 1-worker).
