# Epic 7 — Mode 1 Automation + Scheduler + hàng đợi duyệt (FR-16, Mode 1)

**Goal:** M5 — 07:00 hệ thống tự sản xuất video tin AI; PO duyệt 1 click từ dashboard hoặc điện thoại.
**Points:** 19 · **Tuần:** 11–12 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.

---

# Story 7.1 — Scheduler service (5đ)

**User story:** As an Admin, I want đặt lịch các việc chạy định kỳ và xem lịch sử từng lần chạy, so that hệ thống tự vận hành và tôi biết đêm qua nó đã làm gì, tốn bao nhiêu.
**Bối cảnh & giá trị:** FR-16 — hạ tầng của Mode 1, analytics collector, publish hẹn giờ, cleanup. Advisory lock chống double-run là điều kiện an toàn khi scale API instance sau này.

## Scope
**In:** APScheduler + advisory lock Postgres; bảng schedules/schedule_runs; 4 loại job (mode1_pipeline / analytics_collect / publish / cleanup); API CRUD + enable/disable + run-now + history; tab Quản trị › Lịch chạy; cleanup job (cache render TTL + partition mới + backup trigger).
**Out:** NATS-based scheduler (không cần v1); cron editor trực quan (nhập cron + preview mô tả chữ).

## Business Rules
- **BR-1:** 2 instance API → mỗi lần nổ lịch đúng 1 job chạy (advisory lock — test 2 process).
- **BR-2:** job trước chưa xong khi tới lịch kế → skip + cảnh báo (không chồng).
- **BR-3:** run-now độc lập lịch định kỳ (không reset next-run).
- **BR-4:** mỗi run ghi cost tổng (sum llm_usage theo correlation_id).
- **BR-5:** cron nhập sai → 400 kèm ví dụ đúng; preview "07:00 mỗi ngày" trước khi lưu.
- **BR-6 (mới, PO 2026-07-11):** cleanup job tự lưu trữ project Mode 1 đã PUBLISHED sau `AUTO_ARCHIVE_DAYS` (mặc định 30; 0 = tắt) — số liệu analytics không mất; ghi audit actor=system.

## UI/UX
- Màn: wireframe **Quản trị › Lịch chạy**. States: default · loading · empty (chưa có lịch → gợi ý tạo Mode 1) · error banner · disabled (job hệ thống cleanup không xoá được — chỉ tắt).
- A11y: toggle bật/tắt có label; bảng history caption.

## Data & API
- Bảng: schedules, schedule_runs (partition — schema §2.7). Endpoints §9. Contract change: không.

## Acceptance Criteria
1. **(happy)** Cron `0 7 * * *` enabled → đúng giờ tạo run; disable → im.
2. **(biên/BR-1)** 2 process API, 1 lịch nổ → 1 run duy nhất (test tự động).
3. **(biên/BR-2)** Job treo qua lịch kế → skip + notify; history ghi skip.
4. **(lỗi/BR-5)** Cron "99 * * * *" → 400 kèm ví dụ.
5. **(BR-4)** Run Mode 1 xong → cost hiện trong history khớp llm_usage.

## Test Notes
Test lock 2-process trong CI (spawn 2 worker); time-travel bằng freezegun cho lịch.

## Quyết định đã chốt
- Cleanup mặc định 03:00 hàng ngày, tạo sẵn khi migrate (enabled). ⏳

**Depends:** 6.2 · **Design:** wireframe **Quản trị › Lịch chạy** · **FR:** FR-16

---

# Story 7.2 — Mode 1 pipeline tự hành + chọn topic (5đ)

**User story:** As a PO, I want hệ thống tự chọn chủ đề AI đáng nói nhất hôm nay và làm video hoàn chỉnh, so that sáng nào cũng có video chờ duyệt mà không ai phải động tay.
**Bối cảnh & giá trị:** Mode 1 là nửa giá trị của SRS ("Daily AI News"). Quy tắc "không ép ra video rác" (BR-3) bảo vệ chất lượng kênh — thà không đăng còn hơn đăng nhạt.

## Scope
**In:** graph mode không-interrupt (trừ gate factcheck); topic selection: quét trending (HN top/arXiv mới/RSS 24h) → ranking → chọn top chưa làm (dedupe 7 ngày bằng embedding); auto-approve kèm validation máy (script parse ok, scene strict-valid, produce đủ); dừng READY theo gate; topic cố định qua schedules.config; timeout tổng 30'.
**Out:** auto-publish (7.3 + 8.3); nhiều video/ngày (config sẵn, default 1); chọn topic bằng vote cộng đồng (ngoài scope).

## Business Rules
- **BR-1:** mọi auto-approve ghi actor=system + validation pass nào (audit đầy đủ như người duyệt).
- **BR-2:** FAIL factcheck → NEED_REVIEW + notify; giữ mọi bước đã xong cho người xử lý tiếp bằng Mode 2 UI.
- **BR-3:** không topic nào đạt ngưỡng điểm (config) → kết thúc "hôm nay không có gì đáng làm" + notify nhẹ — không ép.
- **BR-4:** quá 30' → cancel (4.7) + FAILED(timeout) + notify.
- **BR-5:** dedupe topic 7 ngày bằng embedding similarity (không chỉ string match — "GPT-5.5 ra mắt" vs "OpenAI phát hành GPT-5.5").

## UI/UX
Project Mode 1 hiện trên dashboard với badge "● Tự động" (wireframe); mở ra là workspace Mode 2 bình thường (sửa được mọi thứ).

## Data & API
- projects.mode=daily_news; schedules.config (topic/gate/ngưỡng). Contract change: không.

## Acceptance Criteria
1. **(happy)** Run sáng (fixture trending) → project READY ≤30'; mọi step_version đủ; mở sửa được như Mode 2.
2. **(biên/BR-3)** Fixture trending nghèo → kết thúc sạch không project; notify "không có gì đáng làm".
3. **(biên/BR-5)** Topic cùng nghĩa khác chữ với video 3 ngày trước → bị dedupe, chọn topic kế.
4. **(lỗi/BR-4)** Node treo giả lập → 30' cancel + FAILED(timeout) + notify.
5. **(BR-2)** Fixture mâu thuẫn → dừng NEED_REVIEW; xử lý bằng UI 5.6 → chạy tiếp tới READY.

## Test Notes
Fixture trending 2 bộ (giàu/nghèo); full-run integration với MockLLM là test dài nhất CI — đánh dấu slow, chạy trên PR đụng pipeline + nightly.

## Quyết định đã chốt
- Ngưỡng điểm topic khởi điểm 70/100 — tune theo dogfooding. ⏳
- 1 video/ngày mặc định. 

**Depends:** 7.1, 4.7 · **Design:** badge Tự động trên Dashboard · **FR:** Mode 1 SRS §2

---

# Story 7.3 — Gate config + thống kê chính xác (3đ)

**User story:** As an Admin, I want nâng mức tự động của Mode 1 dựa trên thống kê độ chính xác thực tế, so that quyết định "cho máy tự đăng" dựa trên dữ liệu chứ không cảm tính.
**Bối cảnh & giá trị:** Cơ chế "earn trust" của SRS §2: `off → pass_only → on` theo tỉ lệ PASS-đúng 30 ngày ≥95%. Đây là câu trả lời cho rủi ro lớn nhất của sản phẩm (auto-publish nội dung sai).

## Scope
**In:** enforcement `MODE1_AUTOPUBLISH` 3 mức tại bước publish; đo "PASS có đúng không": approve nguyên trạng = đúng, sửa fact = sai (định nghĩa BR-1); thống kê 30 ngày + banner khuyến nghị trên tab Providers; đổi gate = admin action có confirm + audit.
**Out:** auto-publish thực tế cần 8.3 (trước đó nghiệm thu logic với platform download); ML threshold tự điều chỉnh (không có).

## Business Rules
- **BR-1:** "sửa fact" đo được = sau READY user sửa số liệu/tên/ngày trong script HOẶC override claim; sửa hình/chữ trang trí/timing không tính.
- **BR-2:** nâng gate chặn khi mẫu <20 video ("chưa đủ dữ liệu").
- **BR-3:** gate `on` → chỉ PASS auto-publish; WARN luôn dừng (đúng SRS).
- **BR-4:** hạ gate luôn được phép không điều kiện (chiều an toàn).

## UI/UX
Khối thống kê trên tab Providers (wireframe: "96.4% + nút Nâng chế độ"). States: default · empty (<20 mẫu → hiện tiến độ "12/20 video") · disabled (BR-2). A11y: banner khuyến nghị role=status.

## Data & API
- Bảng: thêm `accuracy_events(project_id, was_correct, detected_by, at)`; endpoint stats + đổi gate 🅐 → **cập nhật api-spec §9** (+DB schema).
- Contract change: **có** — bảng + endpoint mới.

## Acceptance Criteria
1. **(happy)** pass_only: video PASS → auto-publish; WARN → READY chờ.
2. **(biên/BR-1)** Sau READY sửa số trong script → ghi nhận "sai"; sửa màu chữ → không ghi nhận.
3. **(biên/BR-2)** 12 video → nút nâng disabled "cần ≥20"; đủ 20 + ≥95% → enabled.
4. **(audit)** Đổi gate ghi ai/lúc/từ→đến; confirm nêu hệ quả.
5. **(BR-4)** Hạ on→off luôn được, không điều kiện.

## Test Notes
Simulate 30 ngày dữ liệu bằng seed; định nghĩa BR-1 cần test kỹ từng nhánh (đây là chỗ dễ cãi nhau nhất).

## Quyết định đã chốt
- Ngưỡng 95% / 30 ngày / tối thiểu 20 mẫu (SRS §2 + bổ sung mẫu tối thiểu). 

**Depends:** 7.2, 8.3 · **Design:** wireframe **Quản trị › Providers** khối thống kê · **FR:** Mode 1 gate

---

# Story 7.4 — Notification: Telegram + email (3đ)

**User story:** As a PO/Admin, I want nhận thông báo qua Telegram khi có việc cần tôi hoặc có sự cố, so that không phải mở dashboard canh chừng hệ thống chạy đêm.
**Bối cảnh & giá trị:** Mode 1 chạy không người trông — notification là "giác quan" duy nhất. Deep-link mở đúng màn (BR-3) biến thông báo thành hành động 1 chạm (nối 7.5 duyệt từ điện thoại).

## Scope
**In:** notification adapter (telegram bot / SMTP) theo khung 3.1, env-activated; sự kiện: factcheck FAIL, pipeline FAILED/timeout, video READY (deep-link), cost cap, provider exhausted, DLQ>0 (nối 9.4); template tiếng Việt ngắn; chống spam gộp 5'.
**Out:** in-app notification center (v1.1); digest tuần; phân kênh theo loại (v1 mọi thứ 1 kênh).

## Business Rules
- **BR-1:** không token → skip lặng (log debug 1 lần), không lỗi.
- **BR-2:** cùng loại + cùng project trong 5' → gộp 1 tin.
- **BR-3:** deep-link mở đúng màn cần thao tác (project → tab chờ xử lý); link hoạt động trên mobile browser.
- **BR-4:** gửi fire-and-forget — Telegram/SMTP chết không ảnh hưởng pipeline.

## UI/UX
N/A app; nội dung tin nhắn là UX: ngắn, emoji trạng thái nhất quán bộ màu (✓⚠✗), 1 link.

## Data & API
- Env: TELEGRAM_*, SMTP_URL (CONFIGURATION §9). Contract change: không.

## Acceptance Criteria
1. **(happy)** Video READY → tin có tiêu đề video + link mở đúng tab Xuất bản (test mobile viewport).
2. **(biên/BR-2)** 3 lỗi liên tiếp 1 run → 1 tin gộp "3 lỗi".
3. **(lỗi/BR-4)** Telegram 500 → pipeline không ảnh hưởng; log warning.
4. **(BR-1)** Không token → không lỗi, không spam log.

## Test Notes
Mock Telegram API; test template render đủ loại sự kiện (snapshot).

## Quyết định đã chốt
- 1 kênh Telegram chung v1 (không phân admin/creator) — đội nhỏ. ⏳

**Depends:** 7.2 · **Design:** — · **FR:** Reliability

---

# Story 7.5 — Dashboard "Chờ duyệt hôm nay" + duyệt nhanh (3đ) 🆕

**User story:** As a PO, I want hàng đợi video chờ duyệt ngay đầu dashboard với nút duyệt-và-đăng 1 click, so that 2 phút mỗi sáng — kể cả từ điện thoại — xử lý xong tin hàng ngày.
**Bối cảnh & giá trị:** Gap từ wireframe v2. Đây là màn ROI cao nhất của Mode 1: toàn bộ giá trị "tự động 95%" quy về 1 cú click cuối cùng của con người. Yêu cầu mobile là ngoại lệ cố ý của chiến lược desktop-first.

## Scope
**In:** khối queue card (READY mode daily_news + mọi NEED_REVIEW): xem video inline (modal player), "✓ Duyệt & đăng" (READY+PASS+platform active → publish theo config), "Mở duyệt" (deep-link đúng tab); sort cũ nhất trước; badge đếm trên sidebar; **responsive <1024px cho riêng màn này**.
**Out:** duyệt hàng loạt (không — từng video); push notification (7.4 lo).

## Business Rules
- **BR-1:** "Duyệt & đăng" chỉ hiện khi PASS + platform active; ngược lại chỉ "Mở duyệt".
- **BR-2:** duyệt nhanh ghi audit như duyệt thường (actor, thời điểm) + tính vào thống kê 7.3 (approve nguyên trạng = PASS đúng).
- **BR-3:** queue rỗng → khối ẩn hẳn (không chiếm chỗ).
- **BR-4:** card hiện verdict + tiêu đề + thời lượng + thumbnail — đủ ra quyết định không cần mở.

## UI/UX
- Màn: wireframe **Dashboard** khối 📥. States: default · loading skeleton · empty (BR-3 ẩn) · error banner · disabled (nút đăng disabled kèm lý do khi WARN/platform hỏng).
- A11y + mobile: 390px dùng được (nút ≥44px trên touch); player modal full-width mobile.

## Data & API
- Endpoint: `GET /projects/review-queue` (mới — tổng hợp 2 nguồn + verdict + next_action) → **cập nhật api-spec §2**; publish dùng §8.
- Contract change: **có** — endpoint queue.

## Acceptance Criteria
1. **(happy)** Sáng 2 video → khối 2 card đủ thông tin BR-4; "Duyệt & đăng" → publish chạy → card biến mất + toast.
2. **(biên/BR-1)** Video WARN → chỉ "Mở duyệt"; deep-link tới claim đang chờ.
3. **(mobile)** 390px: xem video + duyệt được (Playwright viewport); từ link Telegram (7.4) → màn này mở đúng.
4. **(quyền)** Creator thấy queue project mình; admin thấy tất.
5. **(BR-2)** Duyệt nhanh → audit + accuracy_event ghi đúng.

## Test Notes
Playwright mobile viewport là AC cứng; fixture queue 3 trạng thái (PASS/WARN/FAILED).

## Quyết định đã chốt
- Duyệt nhanh không cho sửa metadata (muốn sửa → "Mở duyệt") — giữ 1-click đúng nghĩa. ⏳

**Depends:** 7.2, 8.3, 6.3 · **Design:** wireframe **Dashboard** khối 📥 · **FR:** Mode 1, FR-01

---

## 🏁 M5 (cuối tuần 13)
5 sáng liên tiếp tự động thành công; PO duyệt từ điện thoại qua link Telegram.
