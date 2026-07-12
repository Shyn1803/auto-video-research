# Task 9-5: Prometheus + Grafana + alerts

**Points:** 3đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-2, 7-4 · **FR:** NFR-5

## User story
As an operator, I want metrics và alert cho API, queue, worker, tài nguyên, so that biết hệ thống ốm trước khi user biết.

## Why
NFR-5. Nguyên tắc "alert phải actionable" (BR-2): mỗi alert trỏ mục runbook — chống alert fatigue từ ngày đầu.

## Scope
**In:** FastAPI instrumentator; exporters NATS/postgres/node; Grafana provisioned-as-code (API latency/error, queue depth, worker throughput, GPU/disk); alert rules (FAILED rate, DLQ>0, disk>80%, worker down, cost cap) → notification 7-4; compose profile monitoring.
**Out:** Langfuse/Sentry (9-6); SLO chính thức (v1.1); log aggregation tập trung (docker logs đủ v1).

## Business Rules
1. Dashboards là code trong repo — dựng lại container về nguyên trạng.
2. Mỗi alert rule kèm annotation link mục runbook xử lý.
3. Alert có cooldown — không lặp <15' cùng rule.

## Acceptance Criteria
1. **(happy)** `--profile monitoring up` → dashboards có data thật từ hệ đang chạy.
2. **(diễn tập)** Giết worker / đổ FAIL / vượt cap → 3 alert đến kèm link runbook đúng mục.
3. **(BR-1)** Xoá container Grafana dựng lại → dashboards nguyên vẹn.
4. **(BR-3)** Rule nổ liên tục → tin cách nhau ≥15'.

## Data & API
Hạ tầng thuần. Contract change: không.

## Decisions already locked
- ⏳ Retention Prometheus 30 ngày.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + diễn tập 3 alert ghi thành script (`make drill-alerts`) — tái dùng ở Release Checklist (10-6).
