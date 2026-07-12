# Epic 6 — Produce, Render & Download (FR-11, FR-19/20, FR-12 download)

**Goal:** M4 — topic → MP4 tải được; sửa 1 cảnh chỉ render lại cảnh đó. Bắt đầu dogfooding hàng ngày.
**Points:** 18 · **Tuần:** 9–10 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.

---

# Story 6.1 — Node Produce: TTS batch + asset resolve (5đ)

**User story:** As a system, I want chuẩn bị đủ giọng đọc và ảnh có giấy phép cho mọi cảnh trước khi render, so that render không bao giờ chờ media và video không bao giờ dính ảnh mờ bản quyền.
**Bối cảnh & giá trị:** Node "hậu cần" của pipeline — chậm nhất và dễ lỗi nhất (2 loại provider ngoài). Thiết kế "lỗi cục bộ không giết run" (BR-3) là điều kiện để Mode 1 chạy đêm không người trông.

## Scope
**In:** TTS mọi cảnh song song bounded (semaphore/engine); điền `audio` vào scene JSON + validator nâng duration; asset resolve: `media_intent.query_vi` (semantic tree) → prompt `asset.query` → asset chain (stock → SD local nếu active) → MinIO + license; thiếu → placeholder theme + cờ `asset_missing`; idempotent theo hash (audio + asset).
**Out:** BGM ingest (6.5); render (6.2); sinh ảnh nâng cao (chain lo).

## Business Rules
- **BR-1:** chạy lại chỉ xử lý cảnh thiếu/stale (audio hash đổi khi voice text/giọng đổi — 5.2 BR-3).
- **BR-2:** asset không rõ license → từ chối → provider kế → cuối cùng placeholder. Không bao giờ dùng ảnh thiếu license.
- **BR-3:** lỗi 1 cảnh → cờ lỗi cảnh đó, cảnh khác tiếp tục; node fail chỉ khi >50% cảnh lỗi.
- **BR-4:** ảnh stock chọn theo orientation khớp format project (dọc cho 9:16).
- **BR-5:** audio produce xong → duration cảnh tự nâng nếu thiếu (validator rule) — ghi vào scene JSON version mới.
- **BR-6 (Motion pass-2 — layout-engine §9.4):** sau TTS, gọi Motion Planner re-resolve `motion_plan` bằng word-timestamps thật (stat count-up kết thúc đúng lúc đọc xong số, sync_points theo emphasis); chỉ cập nhật motion_plan — layout không đổi; deterministic, không token.

## UI/UX
Không màn riêng — trạng thái phản ánh: RunningState ("Đang tạo giọng đọc 6/10…"), badge `asset_missing`/lỗi trên SceneThumbnail (5.1), cảnh báo tổng ở màn Phân cảnh.

## Data & API
- Bảng: assets (ghi mới), scenes (update scene_json + hash). Events: step.progress; (Phase NATS: tts/asset.request-done — 9.3).
- Contract change: không (schema audio field đã spec §3.4).

## Acceptance Criteria
1. **(happy)** 10 cảnh, chain pexels → đủ audio+timestamps; ≥8 ảnh thật đúng orientation; thiếu → placeholder + cờ.
2. **(biên/BR-1)** Run lần 2 → 0 call TTS/stock (counter); sửa voice 1 cảnh → chỉ cảnh đó re-TTS.
3. **(biên/BR-3)** Mock TTS fail cảnh 3 → 9 cảnh xong, cảnh 3 cờ lỗi + retry riêng OK.
4. **(lỗi)** Mọi asset provider chết → toàn placeholder + cờ; run hoàn thành; UI cảnh báo tổng.
5. **(BR-2)** Provider trả ảnh không license (mock) → bị loại, thử provider kế (log ghi nhận).

## Test Notes
Semaphore test (không vượt bound); idempotency test là trọng tâm. Fixture media_intent đa dạng (cụ thể/trừu tượng, đủ media_hint).

## Quyết định đã chốt
- Placeholder = nền gradient theme + icon chủ đề (không ảnh xám xấu) — video vẫn dùng được khi thiếu stock. ⏳
- Ngưỡng fail node 50%. ⏳

**Depends:** 4.6, 2.4, 3.2 · **Design:** badge SceneThumbnail · **FR:** FR-19, FR-20

---

# Story 6.2 — Render orchestrator + worker in-process + cache + merge (5đ)

**User story:** As a Content Creator, I want tạo video nhanh nhờ chỉ render phần thay đổi, so that vòng sửa–xem cuối cùng tính bằng chục giây thay vì render lại cả video.
**Bối cảnh & giá trị:** Hiện thực lời hứa trung tâm của SRS ("scene là đơn vị cache/render độc lập" — nguyên tắc #3). Interface queue giống NATS consumer để 9.2 tách worker không đổi logic.

## Scope
**In:** cache_key/cảnh (hash 2.1 + template_version + format); queue in-process (interface NATS-like); song song `RENDER_CONCURRENCY`; worker theo pipeline chính thức Remotion `bundle() → selectComposition() → renderMedia()` ([remotion-integration.md](../specs/remotion-integration.md) §2.5) → MinIO; bảng renders + SSE render.progress; merge ffmpeg (concat + BGM volume/fade + CRF); retry từng job; per-format batch. Trigger skill: dev-guide.md §2.1.
**Out:** worker container (9.2); multi-format UI (10.1 — engine sẵn); GPU encode (v1.1 nếu benchmark cần).

## Business Rules
- **BR-1:** job idempotent theo cache_key — trùng → phát hiện qua renders/MinIO, bỏ qua.
- **BR-2:** job fail không huỷ batch; batch kết thúc khi mọi job xong (kể cả fail); trạng thái tổng trung thực ("7/8 + 1 lỗi").
- **BR-3:** merge chỉ khi 100% cảnh done.
- **BR-4:** sửa cảnh khi đang render → batch hiện tại chạy nốt; cảnh sửa dirty cho batch sau (5.5 BR-4 khoá UI tương ứng).
- **BR-5:** output theo layout storage cố định (ARCHITECTURE §6); cache TTL dọn bởi cleanup job.
- **BR-6 (mới — remotion-integration.md §2.5):** worker `bundle()` **1 lần lúc khởi động**, cache `serveUrl` in-memory, tái dùng cho mọi job sau đó — không bundle lại mỗi render (bundle tốn vài giây, sai giả định ban đầu là gọi CLI trực tiếp mỗi job). Ảnh hưởng trực tiếp benchmark 6.4.

## UI/UX
Tiến độ inline màn Hoàn thiện + modal chi tiết (⚡ cache / ● đang / ✓ / ✗ + retry) — wireframe. Error từng cảnh có nút thử lại riêng.

## Data & API
- Bảng: renders (schema §2.5). Endpoints §7 (render/renders/retry). Events: render.progress.
- Contract change: không.

## Acceptance Criteria
1. **(happy)** 8 cảnh 3 dirty → 3 render + 5 cache_hit; MP4 đúng thứ tự, audio sync, BGM fade (kiểm tay 3 video).
2. **(biên/BR-4)** Sửa cảnh giữa batch → batch xong bình thường; nút "Tạo lại (1 cảnh)" hiện.
3. **(lỗi/BR-2)** 1 cảnh fail → batch kết thúc "7/8 + 1 lỗi"; retry cảnh đó → merge chạy.
4. **(biên/BR-1)** Kill worker giữa job → retry không double-render (đo số lần render thực).
5. **(SSE)** Progress từng cảnh + tổng % đúng.

## Test Notes
Render test dùng template 2.2 + fixture; đo "số lần render thực" bằng counter wrapper quanh CLI call. Audio sync kiểm tay có checklist (đầu/giữa/cuối video).

## Quyết định đã chốt
- CRF 20, preset medium khởi điểm — tune sau benchmark 6.4. ⏳

**Depends:** 6.1, 2.2 · **Design:** wireframe **Hoàn thiện** khối render · **FR:** FR-11

---

# Story 6.3 — Màn Xuất bản: video + download + metadata (3đ)

**User story:** As a Content Creator, I want xem video cuối, tải về và copy sẵn tiêu đề/mô tả/tags, so that đăng tay lên bất kỳ nền tảng nào trong 1 phút.
**Bối cảnh & giá trị:** Đường publish "luôn hoạt động" (FR-12 tầng download) — giá trị dùng được ngay từ M4 khi chưa có nền tảng nào duyệt API.

## Scope
**In:** player video final theo format; Download presigned (per-format); metadata copy (từng cái + tất cả); publish record `download` → PUBLISHED; bảng nền tảng đúng trạng thái provider (✓/⚠ chờ duyệt/○ chưa key — hàng khác của 8.1/10.3 hiện đúng nhãn từ giờ).
**Out:** đăng tự động (8.x); hẹn giờ (8.4).

## Business Rules
- **BR-1:** presigned URL 24h; hết → nút "Tạo link mới".
- **BR-2:** lần tải đầu (format bất kỳ) → PUBLISHED (1 lần chuyển); tải tiếp không đổi trạng thái.
- **BR-3:** màn truy cập được từ READY trở đi (kể cả PUBLISHED — xem lại/tải lại).
- **BR-4:** metadata copy gồm cả attribution BGM nếu track yêu cầu (6.5 BR-2).

## UI/UX
- Màn: wireframe **Xuất bản**. States: default · loading (video đang tải) · empty N/A (guard READY) · error (presigned lỗi → tạo lại) · disabled (chưa READY → trạm lock).
- A11y: video player controls chuẩn; nút copy có phản hồi "đã copy" đọc được.

## Data & API
- Bảng: publishes. Endpoints: §7 video + §8 publish-preview/publish(download).
- Contract change: không.

## Acceptance Criteria
1. **(happy)** Tải 9:16 → file đúng; PUBLISHED; quay lại tải 16:9 vẫn được, trạng thái không đổi.
2. **(biên/BR-1)** URL 24h+ → "Tạo link mới" hoạt động.
3. **(copy/BR-4)** "Copy tất cả" đủ 3 phần + attribution khi có.
4. **(states)** Chưa READY → trạm lock đúng; render lỗi → error state đúng.

## Test Notes
Playwright flow M4 end-to-end kết thúc tại đây — trở thành E2E chuẩn của test-plan.

## Quyết định đã chốt
- PUBLISHED khi tải (không cần xác nhận "đã đăng thật") — đơn giản, đúng ngữ nghĩa "đã xuất xưởng". ⏳

**Depends:** 6.2 · **Design:** wireframe **Xuất bản** · **FR:** FR-12

---

# Story 6.4 — Benchmark & chốt NFR (3đ)

**User story:** As a team, I want số đo hiệu năng thật trên máy chuẩn, so that NFR là cam kết có cơ sở và quyết định tối ưu dựa trên dữ liệu.
**Bối cảnh & giá trị:** SRS v3 cố ý để NFR "chốt sau benchmark" — đây là điểm chốt. Kết quả quyết định nhánh plan §5 (cắt 10.2 lấy chỗ tối ưu hay không).

## Scope
**In:** script benchmark (render/cảnh mỗi layout ×2 format, video 60s, preview load-time); định nghĩa "máy chuẩn" ghi vào ARCHITECTURE.md; chạy 3 lần lấy median; cập nhật NFR-1 số thật; profiling nếu >2× mục tiêu; báo cáo go/no-go với PO trước tuần 11.
**Out:** load test đa user (10.5); tối ưu thực thi (story riêng nếu cần — quyết định từ báo cáo này).

## Business Rules
- **BR-1:** kết quả xấu không im lặng — bắt buộc issue nguyên nhân + phương án + estimate.
- **BR-2:** benchmark script vào repo, chạy lại được 1 lệnh (dùng lại ở 9.2 AC-1 và 10.5).

## UI/UX
N/A.

## Data & API
N/A. Output: bảng số liệu trong ARCHITECTURE.md + NFR-1 SRS cập nhật.

## Acceptance Criteria
1. **(happy)** Bảng số liệu (median 3 runs) commit; NFR-1 cập nhật kèm cấu hình máy chuẩn.
2. **(biên/BR-1)** Nếu 60s-video > 6 phút → issue phân tích (bundling? codec? concurrency?) + quyết định PO ghi lại.
3. **(BR-2)** `make benchmark` chạy lại ra kết quả cùng định dạng.

## Test Notes
Không phải test — là đo đạc; script tái dùng làm smoke perf về sau.

## Quyết định đã chốt
- Máy chuẩn = máy dev GPU hiện có (ghi cấu hình cụ thể khi chạy). ⏳

**Depends:** 6.2 · **Design:** — · **FR:** NFR-1

---

# Story 6.5 — Thư viện nhạc nền có giấy phép (2đ) 🆕

**User story:** As a Content Creator, I want chọn nhạc nền từ thư viện có sẵn giấy phép, so that video có nhạc hợp không khí mà không bao giờ lo gậy bản quyền.
**Bối cảnh & giá trị:** Gap: Timeline có BGM picker nhưng không ai nạp nhạc. Bản quyền nhạc là rủi ro bị gỡ video/claim doanh thu cao nhất trên YouTube — license record bắt buộc là hàng rào.

## Scope
**In:** seed ~10 track (Pixabay Music/YouTube Audio Library — tải thủ công, license đầy đủ) vào assets(audio); API list BGM; admin upload track (license chọn từ danh sách chuẩn, bắt buộc); preview nghe trong picker (5.5).
**Out:** tìm nhạc theo mood bằng AI (v1.1); creator upload nhạc (rủi ro license — admin only); fade tuỳ chỉnh per-track (mặc định đủ).

## Business Rules
- **BR-1:** track không license record → không xuất hiện trong picker (query-level filter).
- **BR-2:** license yêu cầu attribution → dòng ghi công tự nối vào description khi tải/đăng (6.3 BR-4, 8.3).
- **BR-3:** admin upload: license + source_url bắt buộc; loại file mp3/m4a ≤15MB.

## UI/UX
Picker trong màn Hoàn thiện (wireframe): list track + nút nghe 10s + tên/license badge. States: default · loading · empty ("chưa có nhạc — admin thêm tại Quản trị") · error · disabled N/A.

## Data & API
- Bảng: assets (media_type=audio). Endpoints: `GET /assets/bgm` (mới) + admin upload (dùng chung 5.3 upload với media_type) → **cập nhật api-spec §6**.
- Contract change: **có** — endpoint bgm list.

## Acceptance Criteria
1. **(happy)** Picker hiện ≥10 track nghe thử được; chọn → render có nhạc đúng volume/fade.
2. **(biên/BR-2)** Track cần ghi công → description có attribution (kiểm ở 6.3 copy + 8.3 đăng).
3. **(lỗi/BR-3)** Upload thiếu license → 400 đúng field.
4. **(quyền)** Creator không upload được track.

## Test Notes
Seed track là tài sản repo (Git LFS hoặc script tải kèm checksum). ⏳ chọn cách lưu.

## Quyết định đã chốt
- 10 track seed do BA chọn đa dạng mood (tech/calm/upbeat) — danh sách trong PR.

**Depends:** 5.5, FR-20 infra · **Design:** picker wireframe **Hoàn thiện** · **FR:** FR-10, FR-20

---

## 🏁 M4 (cuối tuần 10)
Topic → video hoàn toàn trong UI. Dogfooding: PO tạo ≥1 video/ngày; bug thực tế ưu tiên vào 20% buffer.
