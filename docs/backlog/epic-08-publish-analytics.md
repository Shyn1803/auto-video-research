# Epic 8 — Publish & Analytics (FR-12 YouTube, FR-13)

**Goal:** Video lên YouTube tự động kèm khai báo AI; số liệu quay về thành **phân tích hành động được** (insight, chủ đề, giữ chân); publish adapter chuẩn cho mọi nền tảng sau.
**Points:** 24 · **Tuần:** 11–14 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.
**v3.2:** +8.7 Analytics Insights (3đ) theo feedback PO "analytics chưa thể hiện được sự phân tích".

---

# Story 8.1 — Publish adapter interface + luồng chung (3đ)

**User story:** As a developer, I want một interface publish chuẩn với capabilities từng nền tảng, so that thêm nền tảng mới là một adapter, và UI tự phản ánh nền tảng nào dùng được.
**Bối cảnh & giá trị:** FR-12 kiến trúc tầng. Capabilities check (BR-3) chặn cả lớp lỗi "đăng video ngang lên nền tảng dọc" trước khi chúng thành lỗi API khó hiểu.

## Scope
**In:** `PublishAdapter` base (upload/get_status/capabilities: max_duration, formats, disclosure_supported); chuẩn hoá adapter `download` (6.3); vòng đời publishes đầy đủ; API publish/preview §8; retry backoff upload; UI tab Xuất bản mở rộng: bảng nền tảng theo provider state, form metadata prefill, khối hẹn giờ (UI — job 8.4).
**Out:** adapter YouTube (8.3), TikTok/FB/LinkedIn (10.3); analytics (8.5).

## Business Rules
- **BR-1:** platform inactive không ẩn — hiện kèm lý do + hướng dẫn (wireframe: "chờ duyệt" / "chưa cấu hình").
- **BR-2:** metadata sửa tại màn publish chỉ áp cho lần đăng đó — không sửa script version.
- **BR-3:** capabilities check trước đăng (format/duration/disclosure) → chặn kèm giải thích + gợi ý (ví dụ "dùng bản 9:16").
- **BR-4:** retry upload tối đa 3 với backoff; hết → failed + notify; retry tay được.

## UI/UX
- Màn: wireframe **Xuất bản** bảng nền tảng. States: default · loading (đang đăng — progress/spinner per-row) · empty N/A · error (row-level: failed + lý do + retry) · disabled (BR-1 + BR-3 kèm lý do).
- A11y: mỗi row trạng thái badge màu+icon+text.

## Data & API
- Bảng: publishes (schema §2.6). Endpoints §8. Contract change: không.

## Acceptance Criteria
1. **(happy)** Chỉ download active → bảng đúng wireframe; vòng đời pending→published ghi đủ.
2. **(biên/BR-3)** Đăng 16:9 lên platform dọc-only (mock) → chặn + gợi ý bản 9:16.
3. **(lỗi/BR-4)** Upload fail 3 lần (mock) → failed + notify; nút retry chạy lại.
4. **(quyền)** 🅞 đúng; creator khác 403.
5. **(BR-2)** Sửa title lúc đăng → publishes.title khác script; script version nguyên vẹn.

## Test Notes
Mock adapter "fakeplatform" với capabilities cấu hình được — dùng test BR-3 đủ nhánh, tái dùng ở 10.3.

## Quyết định đã chốt
- Vòng đời publish: pending→scheduled→uploading→published/failed (schema sẵn) — không thêm trạng thái.

**Depends:** 6.3 · **Design:** wireframe **Xuất bản** · **FR:** FR-12

---

# Story 8.2 — YouTube OAuth flow (5đ)

**User story:** As an Admin, I want kết nối kênh YouTube qua OAuth ngay trong trang Quản trị, so that hệ thống đăng thay tôi mà tôi không phải đưa mật khẩu Google cho ai.
**Bối cảnh & giá trị:** YouTube là nền tảng auto-publish chính của v1 (dễ xin quyền nhất). Refresh token là secret nhạy cảm nhất hệ thống nắm giữ — BR bảo mật ở đây khắt khe tương ứng.

## Scope
**In:** Google OAuth (client id/secret env — FR-21): flow connect trong Quản trị › API Keys; refresh token mã hoá (api_keys provider `youtube_oauth`); auto refresh access; revoke/reconnect; đa kênh (default + chọn khi đăng).
**Out:** app verification với Google (việc PO — checklist runbook; unverified đủ dùng nội bộ); OAuth nền tảng khác (10.3 pattern này).

## Business Rules
- **BR-1:** refresh token chỉ trong DB mã hoá — không log/response/error message.
- **BR-2:** refresh fail (revoked phía Google) → trạng thái "mất kết nối" + notify + hướng dẫn; hàng YouTube ở màn publish tự chuyển ⚠.
- **BR-3:** state param chống CSRF trong OAuth flow; redirect URI cố định từ env.
- **BR-4:** ngắt kết nối → xoá token + revoke phía Google (best effort).

## UI/UX
- Khối YouTube trong **Quản trị › API Keys** (wireframe). States: chưa kết nối (nút Connect) · đang connect (chờ callback) · đã kết nối (kênh + avatar) · mất kết nối (⚠ + reconnect) · error (message dịch).
- A11y: flow mở popup/redirect có thông báo rõ; trạng thái badge chuẩn.

## Data & API
- Bảng: api_keys (provider youtube_oauth, key_encrypted = refresh token). Endpoints: `GET /admin/oauth/youtube/start`, `GET /admin/oauth/youtube/callback` (mới) → **cập nhật api-spec §9**.
- Contract change: **có** — 2 endpoint OAuth.

## Acceptance Criteria
1. **(happy)** Connect → consent → kênh hiện tên+avatar; token mã hoá trong DB.
2. **(biên/BR-2)** Giả lập 401 refresh → "mất kết nối" + notify; reconnect phục hồi; màn publish phản ánh ⚠.
3. **(bảo mật/BR-1,3)** Grep log/response không token; callback sai state → 403.
4. **(đa kênh)** 2 kênh → đăng chọn đúng kênh; default hoạt động.
5. **(BR-4)** Ngắt kết nối → token xoá; đăng YouTube → trạng thái "chưa cấu hình".

## Test Notes
Mock Google OAuth server trong integration test; flow thật kiểm tay 1 lần với tài khoản test (ghi vào PR).

## Quyết định đã chốt
- Privacy video mặc định **unlisted** (an toàn khi test đăng); đổi qua config. 

**Depends:** 8.1, 3.4 · **Design:** khối YouTube wireframe · **FR:** FR-12, FR-21

---

# Story 8.3 — YouTube upload + AI disclosure + quota (5đ)

**User story:** As a Content Creator, I want video tự đăng lên YouTube với đầy đủ metadata và khai báo AI, so that đúng chính sách nền tảng và không bao giờ bị gỡ vì thiếu khai báo.
**Bối cảnh & giá trị:** FR-12 + rủi ro "AI content bị giảm reach/gỡ" trong plan §5 — disclosure bắt buộc (BR-1 không có nút tắt) là quyết định tuân thủ, không phải tuỳ chọn.

## Scope
**In:** resumable upload; metadata (title/description/tags/category); **altered-content (AI) disclosure + madeForKids=false**; privacy config (default unlisted); quota guard (đếm units/ngày, chặn trước upload); map lỗi API → tiếng Việt; external_id/url về publishes; attribution BGM nối description (6.5 BR-2).
**Out:** thumbnail tuỳ chỉnh (v1.1); playlist/end-screen (v1.1); Shorts-specific metadata (YouTube tự nhận theo tỉ lệ).

## Business Rules
- **BR-1:** disclosure luôn bật — không config tắt (compliance).
- **BR-2:** quota không đủ (~1600 units) → chặn trước upload + giờ reset (07:00 PT); không thử-rồi-fail.
- **BR-3:** upload đứt → resume theo session (không tải lại từ đầu).
- **BR-4:** video >15' hoặc >256GB → chặn capabilities (không xảy ra với v1 nhưng check rẻ).

## UI/UX
Row YouTube màn Xuất bản: trạng thái uploading (progress %) → published (link mở). Error row-level tiếng Việt + retry.

## Data & API
- publishes.external_id/url; bảng đếm quota (hoặc counter trong api_keys usage) → **cập nhật DB schema nhẹ** (cột quota_used_today).
- Contract change: nhẹ (cột) — ghi migration.

## Acceptance Criteria
1. **(happy)** Đăng → video unlisted đúng metadata + disclosure (kiểm Studio 1 lần, screenshot vào PR); URL lưu + mở được.
2. **(biên/BR-3)** Ngắt mạng giữa upload (mock) → resume tiếp session, không upload lại phần đã gửi.
3. **(lỗi/BR-2)** Quota còn 500 → chặn + "reset 07:00 PT"; 403 lạ → failed message dịch + retry.
4. **(BGM)** Track cần ghi công → description chứa attribution.
5. **(BR-1)** Không tồn tại đường tắt disclosure (review code + không có config).

## Test Notes
Mock YouTube API đủ nhánh (200/401/403quota/500/resume); upload thật 1 video test kiểm tay.

## Quyết định đã chốt
- Category mặc định "Science & Technology". ⏳

**Depends:** 8.2 · **Design:** wireframe **Xuất bản** · **FR:** FR-12

---

# Story 8.4 — Publish theo lịch (3đ)

**User story:** As a Content Creator, I want hẹn giờ đăng video vào khung giờ vàng, so that video ra đúng lúc khán giả online mà tôi không phải thức canh.
**Bối cảnh & giá trị:** FR-12 scheduler + đường auto-publish của Mode 1 (7.3) đi qua đây — một cơ chế duy nhất cho cả hẹn tay lẫn tự động.

## Scope
**In:** scheduled_at → job type publish (7.1); datetime picker timezone VN; huỷ trước giờ; trạng thái "đã lên lịch 20:00" trên card + tab; Mode 1 auto-publish dùng đường này.
**Out:** gợi ý giờ vàng bằng analytics (v1.1); đăng lặp lại (không có).

## Business Rules
- **BR-1:** giờ quá khứ → chặn nhập (client + server).
- **BR-2:** huỷ chỉ khi chưa bắt đầu uploading.
- **BR-3:** job đăng fail → notify + giữ record scheduled để đặt lại — không lặng lẽ bỏ.
- **BR-4:** timezone hiển thị/nhập là Asia/Ho_Chi_Minh; lưu UTC.

## UI/UX
Khối hẹn giờ màn Xuất bản (wireframe). States: chưa hẹn · đã hẹn (đếm ngược + nút huỷ) · đang đăng (không huỷ được — BR-2) · lỗi (BR-3 + đặt lại).

## Data & API
- publishes.scheduled_at; job scheduler 7.1. Contract change: không.

## Acceptance Criteria
1. **(happy)** Hẹn 20:00 → đăng ±2'; trạng thái chuyển đúng chuỗi.
2. **(biên/BR-2)** Huỷ 19:59 → không đăng; huỷ lúc uploading → 409 giải thích.
3. **(biên)** 2 nền tảng 2 giờ → 2 job độc lập chạy đúng.
4. **(lỗi/BR-3)** Fail lúc chạy → notify + nút đặt lại hoạt động.
5. **(BR-4)** Nhập 20:00 VN → DB UTC đúng; hiển thị lại đúng VN.

## Test Notes
freezegun cho giờ; test DST không cần (VN không DST) nhưng test UTC conversion.

## Quyết định đã chốt
- Không giới hạn số lịch chờ. ⏳

**Depends:** 8.3, 7.1 · **Design:** wireframe **Xuất bản** hẹn giờ · **FR:** FR-12

---

# Story 8.5 — Analytics collector (3đ)

**User story:** As a Content Creator, I want số liệu video tự động cập nhật hàng ngày từ YouTube, so that biết nội dung nào hiệu quả mà không phải mở từng nền tảng chép tay.
**Bối cảnh & giá trị:** FR-13 phần thu thập. Thiết kế "api + manual cùng schema" cho phép nền tảng chưa có API (TikTok chờ duyệt) vẫn có mặt trong dashboard từ ngày 1.

## Scope
**In:** job daily (7.1) YouTube Analytics API → metrics (views/likes/comments/watch_time/avg%); dedupe (unique index + upsert); backfill 28 ngày khi video mới connect; form nhập tay (§8 api-spec).
**Out:** dashboard (8.6); realtime metrics (daily đủ); nền tảng khác qua API (10.3+/v1.1).

## Business Rules
- **BR-1:** chạy lại không nhân đôi (upsert theo publish/metric/ngày/source).
- **BR-2:** video bị xoá trên YouTube → đánh dấu, ngừng thu, job vẫn xanh.
- **BR-3:** nhập tay source=manual — job API không ghi đè manual (2 dòng song song, dashboard ưu tiên api khi cả hai).
- **BR-4:** quota Analytics API riêng với upload quota — đếm riêng.

## UI/UX
Form nhập tay đơn giản (từ dashboard 8.6 nút ✎). N/A màn riêng.

## Data & API
- Bảng: metrics partition (schema §2.6). Endpoint manual entry §8. Contract change: không.

## Acceptance Criteria
1. **(happy)** Video đăng 3 ngày → 3 ngày metrics; re-run job → số dòng không đổi.
2. **(biên/BR-3)** Nhập tay TikTok views → lưu manual; job sau không đè; dashboard hiện đúng nguồn.
3. **(lỗi/BR-2)** Video deleted (mock 404) → cờ + job xanh + các video khác thu bình thường.
4. **(backfill)** Video cũ 30 ngày mới connect → backfill 28 ngày.

## Test Notes
Mock Analytics API responses theo ngày; test upsert kỹ (chạy 3 lần cùng dữ liệu).

## Quyết định đã chốt
- Thu 06:00 hàng ngày (trước giờ PO xem 07:00+). ⏳

**Depends:** 8.3, 7.1 · **Design:** — · **FR:** FR-13

---

# Story 8.6 — Analytics dashboard (2đ)

**User story:** As a Content Creator, I want dashboard tổng quan hiệu quả video theo thời gian và nền tảng, so that quyết định chủ đề tiếp theo dựa trên con số.
**Bối cảnh & giá trị:** FR-13 phần hiển thị — vòng lặp học của cả sản phẩm (nội dung nào chạy → làm thêm loại đó).

## Scope
**In:** màn Analytics: 4 số tổng, chart theo ngày, bảng video (sort CTR/completion/views), filter platform + khoảng ngày; empty state; nút ✎ nhập tay per-row.
**Out:** so sánh A/B chủ đề (v1.1); export CSV (v1.1); per-video detail page (bảng đủ v1).

## Business Rules
- **BR-1:** metric nền tảng không cung cấp → "—" + tooltip lý do (không hiện 0 gây hiểu sai).
- **BR-2:** số dashboard khớp DB tuyệt đối (test so khớp seed).
- **BR-3:** nguồn số liệu (tự động/nhập tay) hiển thị per-row.

## UI/UX
- Màn: wireframe **Analytics**. States: default · loading skeleton · empty ("chưa có video đăng" + link tạo) · error banner · disabled N/A.
- A11y: chart có bảng dữ liệu ẩn tương đương (screen reader); "—" có aria-label lý do.

## Data & API
- Endpoints §8 dashboard/videos. Contract change: không.

## Acceptance Criteria
1. **(happy)** Khớp wireframe; filter platform/ngày đúng; sort bảng đúng.
2. **(biên/BR-1)** TikTok completion → "—" + tooltip "nền tảng không cung cấp qua API".
3. **(BR-2)** Seed biết trước → 4 số tổng khớp query tay.
4. **(empty)** 0 video đăng → empty state + CTA.

## Test Notes
Seed metrics 14 video × 30 ngày × 2 nền tảng; vitest cho aggregate hiển thị.

## Quyết định đã chốt
- 4 số tổng: Video/Views/Giờ xem/Xem hết + delta so kỳ trước (wireframe v2). 

**Depends:** 8.5 · **Design:** wireframe **Analytics › Tổng quan + Theo video** · **FR:** FR-13

---

# Story 8.7 — Analytics Insights: giữ chân, chủ đề, gợi ý hành động (3đ) 🆕

**User story:** As a Content Creator, I want hệ thống tự rút ra insight từ số liệu (chủ đề nào giữ chân tốt, độ dài nào hiệu quả, giờ đăng nào lợi) và gợi ý hành động, so that tôi ra quyết định nội dung tiếp theo mà không phải tự làm phân tích trên bảng số thô.
**Bối cảnh & giá trị:** Feedback PO trực tiếp: "analytics chưa thực sự thể hiện được sự phân tích" — 8.6 mới là *hiển thị*, story này là *phân tích*. Đây là vòng lặp học của sản phẩm: insight → điều chỉnh Mode 1/chủ đề → video tốt hơn. Insight là **rule-based trên số liệu thật** (không LLM đoán mò) — mỗi insight phải trích được số + cỡ mẫu.

## Scope
**In:**
- **Giữ chân (Tổng quan):** đường giữ chân trung bình kênh (0/15/30/45s) từ YouTube retention; callout điểm rơi mạnh nhất.
- **Drill-down video (Theo video):** giữ chân theo giây + map điểm rơi sang **ranh giới cảnh** (join với timeline scene) — "rơi 15% tại cảnh #6"; nguồn view (đề xuất/tìm kiếm); so với TB kênh (badge ✓/✗ ±%).
- **Theo chủ đề:** gắn `topic_group` cho project (AI phân loại lúc tạo, sửa được); bảng nhóm (video/xem TB/xem hết TB/CTR/xu hướng); gợi ý tỉ trọng chủ đề + nút "Áp dụng vào cấu hình Mode 1".
- **Insight tự động (rule-based):** bộ ~5 rule khởi điểm: so nhóm chủ đề (xem hết), so độ dài (≤50s vs >70s), giờ đăng vs view 48h, cảnh báo CTR giảm so TB, cỡ mẫu kèm mọi insight.
**Out:** insight bằng LLM (v1.1 — sau khi rule-based chứng minh dữ liệu đủ sạch); A/B thumbnail/title (v1.1); phân tích audience demographics (v1.1); dữ liệu nền tảng ngoài YouTube (nhập tay không đủ hạt cho retention).

## Business Rules
- **BR-1:** insight chỉ hiện khi đủ cỡ mẫu (mặc định ≥5 video/nhóm so sánh) — thiếu → "chưa đủ dữ liệu (3/5 video)" thay vì kết luận yếu.
- **BR-2:** mọi insight kèm số gốc + cỡ mẫu ("54% vs 41%, 7 vs 5 video") — không câu kết luận trần.
- **BR-3:** `topic_group` do AI gán khi tạo project (tier cheap, từ danh sách nhóm cố định config: công-cụ/tin-model/nghiên-cứu/khác) — user sửa được; đổi nhóm → số liệu tính lại.
- **BR-4:** "Áp dụng vào Mode 1" chỉ điều chỉnh **trọng số ưu tiên chủ đề** trong schedules.config, có confirm + audit — không tự đổi im lặng.
- **BR-5:** map điểm-rơi→cảnh dùng retention buckets của YouTube (độ phân giải hạn chế) — hiển thị "≈ cảnh #6" (xấp xỉ), tooltip giải thích.

## UI/UX
- Màn: wireframe **Analytics** 3 tab (Tổng quan khối Insight 💡 + giữ chân; Theo video drill-down; Theo chủ đề + gợi ý). States: default · loading skeleton · empty/thiếu mẫu (BR-1 hiển thị tiến độ mẫu) · error banner · disabled (nút Áp dụng disabled khi chưa có schedule Mode 1 + tooltip).
- A11y: insight list là text thật (screen reader đọc trọn); chart giữ chân có bảng ẩn tương đương; badge xu hướng ▲▼→ kèm chữ.

## Data & API
- Bảng: `projects.topic_group` (cột mới + migration); retention lưu vào `metrics` (metric=`retention_15s/30s/45s` + `views_48h`) — mở rộng collector 8.5.
- Endpoints: `GET /analytics/insights?from&to` (mới), `GET /analytics/topics` (mới), `POST /analytics/apply-topic-weights` 🅐 (mới) → **cập nhật api-spec §8 + database-schema** trong PR.
- Contract change: **có** — 3 endpoint + 1 cột + metric keys mới.

## Acceptance Criteria
1. **(happy)** Seed 14 video 3 nhóm chủ đề đủ mẫu → tab Chủ đề bảng đúng số; Insight ①② hiện đúng công thức kèm cỡ mẫu (so khớp query tay).
2. **(biên/BR-1)** Nhóm 3 video → insight nhóm đó thay bằng "chưa đủ dữ liệu (3/5)"; không kết luận.
3. **(biên/BR-3)** Đổi topic_group 1 video → bảng nhóm tính lại ngay; audit ghi.
4. **(biên/BR-5)** Drill-down video → điểm rơi map "≈ cảnh #N" khớp timeline scene (fixture dựng sẵn); tooltip xấp xỉ hiện.
5. **(BR-4)** "Áp dụng vào Mode 1" → confirm nêu trọng số cũ→mới → schedules.config đổi + audit; chưa có schedule → disabled + tooltip.
6. **(quyền)** Creator xem insight; chỉ admin bấm Áp dụng (🅐).

## Test Notes
Seed analytics 14 video × 30 ngày × retention là fixture lớn — viết generator (không tay); mỗi rule insight 1 unit test công thức + 1 test BR-1 thiếu mẫu. Rule engine là pure function trên dataframe → test nhanh không DB.

## Quyết định đã chốt
- Insight rule-based v1, không LLM (giải thích được, không bịa) — LLM narrative để v1.1. ⏳
- Danh sách topic_group khởi điểm: công-cụ/hướng-dẫn · tin-model · nghiên-cứu/paper · khác. ⏳
- Ngưỡng cỡ mẫu 5 video/nhóm. ⏳

**Depends:** 8.5 (retention collector mở rộng), 8.6 (khung màn), 7.1 (apply vào schedule) · **Design:** wireframe **Analytics** cả 3 tab · **FR:** FR-13
