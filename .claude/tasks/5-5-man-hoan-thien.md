# Task 5-5: Màn Hoàn thiện — timeline + BGM + render trigger

**Points:** 5đ · **Epic:** 5 — Workspace UI · **Depends:** 5-1, 2-4, 6-2 (tiến độ thật) · **FR:** FR-10, FR-11

## User story
As a Content Creator, I want tinh chỉnh nhịp, chuyển cảnh, nhạc nền rồi bấm tạo video trên một màn, so that bước cuối gọn trong một chỗ và chỉ render phần thay đổi.

## Why
FR-10 + cửa vào FR-11. Gộp Timeline+Render thành trạm "Hoàn thiện" là quyết định IA từ critique (stepper 5 trạm khớp state machine).

## Scope
**In:** TimelineBar (resize chặn dưới audio+300ms + tooltip; transition tại khớp nối); BGM picker (nguồn 6-5) + volume/fade; tổng thời lượng realtime; nghe thử giọng/cảnh; Play toàn bộ (Player nối cảnh — "bản xem thử", see [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)); khối Tạo video per-format + tiến độ inline (consume 6-2 — mock trước khi 6-2 xong).
**Out:** render logic (6-2); download/publish (6-3); BGM ingest (6-5).

## Business Rules
1. Vào màn chỉ khi mọi cảnh approve (trạm lock + guard API).
2. Resize hiện tooltip lý do chặn dưới ("giọng đọc 5.2s + đệm").
3. Mọi thay đổi ở màn này → cảnh liên quan dirty → nút "Tạo video" đổi nhãn "Tạo lại (2 cảnh thay đổi)".
4. Render đang chạy → điều khiển timeline disabled + giải thích (khớp 6-2 BR-4).

## Acceptance Criteria
1. **(happy)** Kéo 6s→5.5s (audio 5.2) OK; 4s → chặn 5.5 + tooltip; transition đổi nghe/nhìn được khi Play.
2. **(biên/BR-3)** Đổi transition cảnh 3 → chỉ cảnh 3 dirty; nhãn nút "Tạo lại (1 cảnh)".
3. **(lỗi/BR-4)** Đang render → timeline khoá + giải thích; xong → mở lại.
4. **(a11y)** Resize bằng phím hoạt động.
5. **(BGM)** Chọn track + volume → Play nghe được; render có nhạc đúng mức.

## Data & API
Endpoints: GET/PATCH timeline (§6), POST render (§7). Contract change: không.

## Decisions already locked
- "Bản xem thử" Player nối cảnh chấp nhận transition xấp xỉ. Nhãn UI ghi rõ.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock render progress qua SSE fixture khi 6-2 chưa xong (interface đã chốt event-catalog).
