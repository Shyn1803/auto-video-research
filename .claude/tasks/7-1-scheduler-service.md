# Task 7-1: Scheduler service

**Points:** 5đ · **Epic:** 7 — Automation · **Depends:** 6-2 · **FR:** FR-16

## User story
As an Admin, I want đặt lịch các việc chạy định kỳ và xem lịch sử từng lần chạy, so that hệ thống tự vận hành và tôi biết đêm qua nó đã làm gì, tốn bao nhiêu.

## Why
FR-16 — hạ tầng của Mode 1, analytics collector, publish hẹn giờ, cleanup. Advisory lock chống double-run là điều kiện an toàn khi scale API instance sau này.

## Scope
**In:** APScheduler + advisory lock Postgres; bảng schedules/schedule_runs; 4 loại job (mode1_pipeline / analytics_collect / publish / cleanup); API CRUD + enable/disable + run-now + history; tab Quản trị › Lịch chạy; cleanup job (cache render TTL + partition mới + backup trigger).
**Out:** NATS-based scheduler; cron editor trực quan (nhập cron + preview mô tả chữ).

## Business Rules
1. 2 instance API → mỗi lần nổ lịch đúng 1 job chạy (advisory lock — test 2 process).
2. Job trước chưa xong khi tới lịch kế → skip + cảnh báo (không chồng).
3. run-now độc lập lịch định kỳ (không reset next-run).
4. Mỗi run ghi cost tổng (sum llm_usage theo correlation_id).
5. Cron nhập sai → 400 kèm ví dụ đúng; preview "07:00 mỗi ngày" trước khi lưu.
6. **(PO 2026-07-11)** cleanup job tự lưu trữ project Mode 1 đã PUBLISHED sau `AUTO_ARCHIVE_DAYS` (mặc định 30; 0 = tắt); ghi audit actor=system.

## Acceptance Criteria
1. **(happy)** Cron `0 7 * * *` enabled → đúng giờ tạo run; disable → im.
2. **(biên/BR-1)** 2 process API, 1 lịch nổ → 1 run duy nhất (test tự động).
3. **(biên/BR-2)** Job treo qua lịch kế → skip + notify; history ghi skip.
4. **(lỗi/BR-5)** Cron "99 * * * *" → 400 kèm ví dụ.
5. **(BR-4)** Run Mode 1 xong → cost hiện trong history khớp llm_usage.

## Data & API
Bảng: schedules, schedule_runs (partition). Endpoints §9. Contract change: không.

## Decisions already locked
- ⏳ Cleanup mặc định 03:00 hàng ngày, tạo sẵn khi migrate (enabled).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + test lock 2-process trong CI (spawn 2 worker); time-travel bằng freezegun cho lịch.
