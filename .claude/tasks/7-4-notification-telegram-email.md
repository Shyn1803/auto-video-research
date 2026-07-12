# Task 7-4: Notification — Telegram + email

**Points:** 3đ · **Epic:** 7 — Automation · **Depends:** 7-2 · **FR:** Reliability

## User story
As a PO/Admin, I want nhận thông báo qua Telegram khi có việc cần tôi hoặc có sự cố, so that không phải mở dashboard canh chừng hệ thống chạy đêm.

## Why
Mode 1 chạy không người trông — notification là "giác quan" duy nhất. Deep-link mở đúng màn (BR-3) biến thông báo thành hành động 1 chạm (nối 7-5).

## Scope
**In:** notification adapter (telegram bot / SMTP) theo khung 3-1, env-activated; sự kiện: factcheck FAIL, pipeline FAILED/timeout, video READY (deep-link), cost cap, provider exhausted, DLQ>0 (nối 9-4); template tiếng Việt ngắn; chống spam gộp 5'.
**Out:** in-app notification center (v1.1); digest tuần; phân kênh theo loại (v1 mọi thứ 1 kênh).

## Business Rules
1. Không token → skip lặng (log debug 1 lần), không lỗi.
2. Cùng loại + cùng project trong 5' → gộp 1 tin.
3. Deep-link mở đúng màn cần thao tác; link hoạt động trên mobile browser.
4. Gửi fire-and-forget — Telegram/SMTP chết không ảnh hưởng pipeline.

## Acceptance Criteria
1. **(happy)** Video READY → tin có tiêu đề video + link mở đúng tab Xuất bản (test mobile viewport).
2. **(biên/BR-2)** 3 lỗi liên tiếp 1 run → 1 tin gộp "3 lỗi".
3. **(lỗi/BR-4)** Telegram 500 → pipeline không ảnh hưởng; log warning.
4. **(BR-1)** Không token → không lỗi, không spam log.

## Data & API
Env: TELEGRAM_*, SMTP_URL. Contract change: không.

## Decisions already locked
- ⏳ 1 kênh Telegram chung v1 (không phân admin/creator) — đội nhỏ.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock Telegram API; test template render đủ loại sự kiện (snapshot).
