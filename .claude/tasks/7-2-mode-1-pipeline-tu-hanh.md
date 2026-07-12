# Task 7-2: Mode 1 pipeline tự hành + chọn topic

**Points:** 5đ · **Epic:** 7 — Automation · **Depends:** 7-1, 4-7 · **FR:** Mode 1 SRS §2

## User story
As a PO, I want hệ thống tự chọn chủ đề AI đáng nói nhất hôm nay và làm video hoàn chỉnh, so that sáng nào cũng có video chờ duyệt mà không ai phải động tay.

## Why
Mode 1 là nửa giá trị của SRS ("Daily AI News"). Quy tắc "không ép ra video rác" (BR-3) bảo vệ chất lượng kênh — thà không đăng còn hơn đăng nhạt.

## Scope
**In:** graph mode không-interrupt (trừ gate factcheck); topic selection: quét trending (HN top/arXiv mới/RSS 24h) → ranking → chọn top chưa làm (dedupe 7 ngày bằng embedding); auto-approve kèm validation máy (script parse ok, scene strict-valid, produce đủ); dừng READY theo gate; topic cố định qua schedules.config; timeout tổng 30'.
**Out:** auto-publish (7-3 + 8-3); nhiều video/ngày (config sẵn, default 1); chọn topic bằng vote cộng đồng.

## Business Rules
1. Mọi auto-approve ghi actor=system + validation pass nào (audit đầy đủ như người duyệt).
2. FAIL factcheck → NEED_REVIEW + notify; giữ mọi bước đã xong cho người xử lý tiếp bằng Mode 2 UI.
3. Không topic nào đạt ngưỡng điểm (config) → kết thúc "hôm nay không có gì đáng làm" + notify nhẹ — không ép.
4. Quá 30' → cancel (4-7) + FAILED(timeout) + notify.
5. Dedupe topic 7 ngày bằng embedding similarity (không chỉ string match).

## Acceptance Criteria
1. **(happy)** Run sáng (fixture trending) → project READY ≤30'; mọi step_version đủ; mở sửa được như Mode 2.
2. **(biên/BR-3)** Fixture trending nghèo → kết thúc sạch không project; notify "không có gì đáng làm".
3. **(biên/BR-5)** Topic cùng nghĩa khác chữ với video 3 ngày trước → bị dedupe, chọn topic kế.
4. **(lỗi/BR-4)** Node treo giả lập → 30' cancel + FAILED(timeout) + notify.
5. **(BR-2)** Fixture mâu thuẫn → dừng NEED_REVIEW; xử lý bằng UI 5-6 → chạy tiếp tới READY.

## Data & API
projects.mode=daily_news; schedules.config (topic/gate/ngưỡng). Contract change: không.

## Decisions already locked
- ⏳ Ngưỡng điểm topic khởi điểm 70/100 — tune theo dogfooding.
- 1 video/ngày mặc định.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + full-run integration MockLLM là test dài nhất CI (slow tag, chạy PR đụng pipeline + nightly).
