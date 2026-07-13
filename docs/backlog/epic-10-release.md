# Epic 10 — Multi-platform, Hardening & Release (FR-12 đa nền tảng, NFR-4, Release)

**Goal:** Đóng gói release v1.0 production — vượt Release Checklist [plan.md](../plan.md) §6.
**Points:** 18 · **Tuần:** 14–17 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.

---

# Story 10.1 — Multi-format render production (3đ)

**User story:** As a Content Creator, I want một dự án xuất được cả bản dọc lẫn ngang, so that cùng một nội dung phủ TikTok/Shorts lẫn YouTube dài mà không làm lại.
**Bối cảnh & giá trị:** FR-11 multi-format — nhân đôi giá trị mỗi video sản xuất. Template responsive đã dựng từ 2.2; story này đưa nó thành luồng sản phẩm hoàn chỉnh.

## Scope
**In:** nghiệm thu production template 16:9; projects.formats nhiều giá trị; render batch per-format/**platform profile** (cache riêng — 6.2 engine sẵn); UI: chọn format khi tạo (1.3 có sẵn) + "＋ Tạo bản 16:9" tại tab Xuất bản; publish tự chọn profile hợp nền tảng (8.1 BR-3).
**Out:** format vuông 1:1 (v1.1 nếu cần); layout khác nhau per-format (template responsive đủ).

## Business Rules
- **BR-1:** thêm format sau không đụng cache format cũ.
- **BR-2:** mỗi format trạng thái render/download độc lập trên UI.
- **BR-3:** asset orientation: format ngang ưu tiên ảnh ngang — produce re-resolve asset thiếu orientation (cờ cảnh báo nếu phải dùng ảnh dọc crop).
- **BR-4:** profile và format phải tương thích: TikTok/Facebook Reels/YouTube Shorts → 9:16; YouTube video → 16:9. Profile áp safe-area, subtitle và watermark nhưng không gọi lại AI hay đổi layout class.

## UI/UX
Tab Xuất bản: badge per-format (wireframe ✓9:16 ✓16:9); nút thêm format kèm ước lượng "sẽ render 8 cảnh". States: từng format có trạng thái riêng (○ chưa tạo · ● đang · ✓ · ✗ retry).

## Data & API
- projects.formats[] (schema sẵn); render §7 nhận formats. Contract change: không.

## Acceptance Criteria
1. **(happy)** Cùng scene_set 2 format → PO duyệt chất lượng cả hai.
2. **(biên/BR-1)** Thêm 16:9 vào project 9:16 done → chỉ render 16:9; cache 9:16 nguyên.
3. **(BR-3)** Cảnh có ảnh dọc sang 16:9 → cờ cảnh báo crop; picker gợi ý tìm ảnh ngang.
4. **(publish)** YouTube video chọn `youtube_video` + 16:9; TikTok/FB Reels/Shorts chọn profile dọc + 9:16 tự động; safe-area đúng profile.

## Test Notes
Render test matrix layout×format từ 2.2 nâng thành nghiệm thu; kiểm tay 2 video.

## Quyết định đã chốt
- 2 format v1 (dọc + ngang) — vuông khi có nhu cầu thật. 

**Depends:** 6.2, 2.2 · **Design:** wireframe **Xuất bản** badge format · **FR:** FR-11

---

# Story 10.2 — Bộ template 2–3 (3đ) *(buffer cắt đầu tiên nếu trễ — plan §5)*

**User story:** As a Content Creator, I want chọn giữa vài phong cách hình ảnh, so that video của kênh không bị một màu khi đăng hàng ngày.
**Bối cảnh & giá trị:** Rủi ro "mass-produced content" bị nền tảng giảm reach (SRS §12) — đa dạng theme bổ sung cho cơ chế chống lặp layout (4.6 BR-9) đã enforce sẵn ở mọi theme. Cắt được nếu trễ vì không chặn luồng nào.

## Scope
**In:** 2 theme mới (sáng / gradient động) cùng contract Scene JSON + `supportedSchemaRange`; mỗi theme khai đủ dial `motion_intensity`/`visual_density`/`accent_saturation_max`/`radius_scale` (layout-engine §8 — bắt buộc, không theme "mặc định ngầm"); ví dụ: Sáng-tối-giản `(4,3,0.6,soft-16px)`, Gradient-động `(8,4,0.8,pill)`; theme cấp project (chọn khi tạo + đổi trong Phân cảnh có preview); render test matrix mở rộng.
**Out:** theme marketplace/tuỳ chỉnh màu per-project (v1.1); font riêng (v1.1).

## Business Rules
- **BR-1:** đổi theme không đổi Scene JSON — chỉ mapping visual.
- **BR-2:** đổi theme → mọi cảnh dirty; cảnh báo "8 cảnh sẽ render lại" trước khi áp.
- **BR-3:** theme mới phải pass toàn bộ render test matrix (11 layout × 2 format) trước khi vào danh sách chọn.
- **BR-4 (video-taste.md §4.3):** 1 accent color/theme (saturation ≤ `accent_saturation_max`), 1 `radius_scale` — áp cho highlight_color, chart highlight point, winner badge trong toàn bộ scene của video; validator cảnh báo nếu scene tự ý set màu ngoài accent theme.

## UI/UX
Chọn theme = 3 thumbnail preview cùng 1 cảnh mẫu (so sánh trực quan). States: preview loading · áp dụng (confirm BR-2).

## Data & API
- projects.theme (cột mới → migration); scene render props nhận theme. Contract change: **có** — cột + trường tạo project → cập nhật api-spec §2 + DB schema.

## Acceptance Criteria
1. **(happy)** 3 video cùng nội dung 3 theme khác biệt rõ (PO duyệt).
2. **(biên/BR-2)** Đổi theme → confirm → toàn bộ dirty → render lại đủ.
3. **(BR-3)** CI matrix theme mới xanh trước khi merge.

## Test Notes
Tái dùng khung render test 2.2; screenshot 3 theme vào PR.

## Quyết định đã chốt
- Theme cấp project, không per-scene (nhất quán video). 

**Depends:** 2.2 · **Design:** design-system tokens mở rộng theme · **FR:** FR-11

---

# Story 10.3 — TikTok / Facebook / LinkedIn adapters (5đ)

**User story:** As a Content Creator, I want hệ thống sẵn sàng đăng TikTok/Facebook/LinkedIn ngay khi nền tảng duyệt app, so that ngày có key là ngày đăng được, không chờ thêm sprint code.
**Bối cảnh & giá trị:** FR-12 tầng 3. "Chờ duyệt" nằm ngoài kiểm soát (plan §1 điểm 3) — chiến lược là code xong 100%, kích hoạt = env. Nộp đơn từ tuần 11 chạy song song.

## Scope
**In:** 3 adapter theo PublishAdapter (8.1): TikTok Content Posting (dọc, AIGC disclosure), Facebook Reels (≤90s), LinkedIn video (ngang ưu tiên); env-activated; UI trạng thái "chờ duyệt nền tảng" + ngày nộp đơn; unit test HTTP mock đủ nhánh; test sandbox tới mức nền tảng cho phép; checklist nộp app review cho PO (kèm video demo M4) vào runbook.
**Out:** kích hoạt production (sau release — chỉ env); analytics 3 nền tảng qua API (v1.1 — nhập tay 8.5 đủ).

## Business Rules
- **BR-1:** adapter code hoàn chỉnh + test — "chờ duyệt" là trạng thái dữ liệu, không phải code dở.
- **BR-2:** capabilities per-platform vào bảng adapter (TikTok dọc ≤10'; FB Reels ≤90s; LinkedIn ngang ưu tiên) — validate trước đăng (8.1 BR-3 tiêu thụ).
- **BR-3:** app bị từ chối → runbook có mục các bước nộp lại + yêu cầu thường gặp của từng nền tảng.
- **BR-4:** AIGC disclosure TikTok bật cứng như YouTube (8.3 BR-1 pattern).

## UI/UX
Bảng nền tảng (wireframe): ⚠ chờ duyệt + ngày nộp; có key sandbox/thật → tự chuyển trạng thái không deploy. Lỗi API map tiếng Việt.

## Data & API
- 3 adapter + capabilities config. Contract change: không (PublishAdapter sẵn).

## Acceptance Criteria
1. **(happy-sandbox)** Key sandbox TikTok → flow chạy tới mức API cho phép; lỗi map rõ.
2. **(biên/BR-2)** Video 16:9 → TikTok chặn + gợi ý bản 9:16; video 2' → FB Reels chặn ≤90s.
3. **(UI)** Chưa duyệt → ⚠ + ngày nộp; thêm key → ✓ không deploy.
4. **(unit/BR-1)** 3 adapter coverage nhánh chính (200/4xx/5xx/quota) bằng mock.
5. **(BR-4)** Không đường tắt AIGC disclosure TikTok.

## Test Notes
Mock server 3 nền tảng theo tài liệu API công khai; đánh dấu rõ phần "chưa kiểm được vì cần app duyệt" trong PR.

## Quyết định đã chốt
- Nộp đơn TikTok + Facebook tuần 11 (việc PO — plan đã ghi); LinkedIn nộp sau (ưu tiên thấp). ⏳

**Depends:** 8.1 · **Design:** wireframe **Xuất bản** bảng nền tảng · **FR:** FR-12

---

# Story 10.4 — Security hardening (4đ)

**User story:** As an operator, I want hệ thống khoá chặt trước khi ra production, so that key người dùng, nội dung và hạ tầng không thành điểm yếu khi hệ chạy công khai 24/7.
**Bối cảnh & giá trị:** NFR-4 tổng nghiệm thu. Nguyên tắc: kiểm soát bằng **test tự động** (RBAC từ OpenAPI, secret-in-log, dependency scan) — không bằng trí nhớ reviewer.

## Scope
**In:** rate limit toàn API (user+IP, config); security headers (CSP Next, HSTS); CORS prod allowlist; test tự động "log không chứa secret" (mở rộng pattern 3.4/9.4 toàn hệ); `make rotate-fernet` + drill staging; pip-audit/npm-audit CI fail-on-critical; images non-root + pin digest; RBAC test sinh từ OpenAPI (route thiếu khai báo quyền → CI fail).
**Out:** pentest ngoài (v1.1 nếu thương mại hoá); WAF (chưa cần scale này); SSO (ngoài scope).

## Business Rules
- **BR-1:** route mới bắt buộc khai báo quyền — enforced bằng test sinh từ OpenAPI.
- **BR-2:** rotation Fernet không downtime — 2-key giai đoạn chuyển, re-encrypt batch.
- **BR-3:** rate limit trả 429 chuẩn error format + Retry-After.
- **BR-4:** CSP không unsafe-inline cho script (Next config phù hợp).

## UI/UX
N/A (trừ 429 hiển thị lịch sự qua error format chuẩn).

## Data & API
Middleware + CI jobs. Contract change: không (429 đã trong spec).

## Acceptance Criteria
1. **(happy)** Checklist Bảo mật plan §6 tick đủ kèm bằng chứng (screenshot/log/CI link).
2. **(biên/BR-2)** Rotation trên staging: hệ hoạt động xuyên suốt; key cũ hết hiệu lực sau hoàn tất.
3. **(CI/BR-1)** Route demo không khai quyền → CI fail; dependency critical giả → fail.
4. **(BR-3)** Vượt rate limit → 429 + Retry-After; UI toast lịch sự.
5. **(secret-log)** Test toàn hệ grep secret pass (chạy trên log integration test đầy đủ).

## Test Notes
RBAC test generator là deliverable tái dùng vĩnh viễn; drill rotation ghi thời gian vào runbook.

## Quyết định đã chốt
- Rate limit mặc định 100 req/phút/user, 20 req/phút cho auth endpoints. ⏳

**Depends:** toàn hệ · **Design:** — · **FR:** NFR-4

---

# Story 10.5 — Load test + backup drill + nghiệm thu local-first (3đ)

**User story:** As a team, I want bằng chứng hệ chịu tải mục tiêu, khôi phục được từ backup, và chạy đủ với 0 API key, so that release dựa trên kiểm chứng chứ không hy vọng.
**Bối cảnh & giá trị:** 3 mục "Vận hành" của Release Checklist. BR-1 (người không viết code làm drill) kiểm luôn chất lượng runbook — tài liệu chưa ai làm theo là tài liệu chưa xong.

## Scope
**In:** k6/locust: 5 render đồng thời + 20 user UI trên staging → số liệu vào ARCHITECTURE.md; đánh giá autoscale cần/chưa (quyết định cho v1.1); restore drill máy sạch theo runbook (đo thời gian, do người không viết code thực hiện); CI job E2E `.env` 0 key (nightly với Ollama thật).
**Out:** stress đến gãy (không cần — biết headroom đủ); multi-region (ngoài scope).

## Business Rules
- **BR-1:** drill do người không viết code làm theo runbook — mọi chỗ tắc = bug tài liệu → sửa runbook trong story này.
- **BR-2:** load test chạy trên staging cấu hình = production (không test trên dev).
- **BR-3:** nightly 0-key phải xanh 3 đêm liên tiếp mới tick (chống may mắn).

## UI/UX
N/A.

## Data & API
N/A. Output: số liệu ARCHITECTURE.md; thời gian restore vào runbook; CI job mới.

## Acceptance Criteria
1. **(load)** 5 render + 20 user: không lỗi, p95 API <1s (⏳ ngưỡng), số liệu commit.
2. **(drill/BR-1)** Restore máy sạch thành công bởi người không viết code; thời gian ghi runbook; chỗ tắc đã sửa docs.
3. **(local-first/BR-3)** Nightly 0-key xanh 3 đêm liên tiếp — nghiệm thu FR-21/NFR-6 chính thức.

## Test Notes
k6 script vào repo (`make loadtest`); drill có biên bản ngắn (ai, bao lâu, vướng gì).

## Quyết định đã chốt
- p95 API < 1s dưới tải mục tiêu. ⏳

**Depends:** 9.2, 9.5 · **Design:** — · **FR:** NFR-2/3/6, FR-21

---

# Story 10.6 — Release: docs, checklist, go-live (2đ)

**User story:** As a team, I want quy trình release có gate rõ và theo dõi 48h đầu, so that v1.0 ra production có kiểm soát và học được gì đó cho v1.1.
**Bối cảnh & giá trị:** Điểm kết của plan. BR-1 (không ngoại lệ cho Bảo mật/Vận hành) là cam kết kỷ luật — release trễ 1 tuần rẻ hơn sự cố production tuần đầu.

## Scope
**In:** rà docs khớp code (specs/CONFIGURATION/runbook theo staging thật); Release Checklist plan §6 — mỗi mục người tick + bằng chứng; tag v1.0.0; deploy prod theo runbook §1; bật lịch Mode 1; theo dõi 48h (alert channel + phân công trực); retro release → backlog v1.1.
**Out:** marketing/công bố (ngoài scope kỹ thuật); v1.1 planning chi tiết (sau retro).

## Business Rules
- **BR-1:** mục checklist nhóm Bảo mật/Vận hành không đạt → không release; không có "fix sau".
- **BR-2:** deploy prod đúng runbook — lệch = sửa runbook trước rồi làm lại theo.
- **BR-3:** 48h đầu: mọi alert có người nhận trong 30' (phân công ghi rõ).

## UI/UX
N/A.

## Data & API
N/A. Output: tag, checklist hoàn chỉnh, biên bản retro.

## Acceptance Criteria
1. **(gate)** Checklist 100% có bằng chứng; nhóm Bảo mật/Vận hành không mục nào waive.
2. **(go-live)** Prod chạy 48h không Sev-1; Mode 1 sáng đầu tiên trên prod thành công.
3. **(retro)** Biên bản retro + danh sách v1.1 (TikTok/FB kích hoạt, visual diff, A/B prompt, autoscale…) commit vào docs.

## Test Notes
Không test mới — thực thi và ghi nhận.

## Quyết định đã chốt
- Định nghĩa Sev-1: mất khả năng tạo/duyệt/đăng video hoặc lộ dữ liệu. ⏳

**Depends:** 10.4, 10.5 · **Design:** — · **FR:** Release plan §1
