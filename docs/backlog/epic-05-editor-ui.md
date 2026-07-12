# Epic 5 — Workspace UI: khung, editor, timeline, review, running-state, version (FR-09/10 + UI pipeline)

**Goal:** User không biết JSON sửa được mọi thứ; mọi luồng wireframe v2 có màn thật. Song song Epic 4 bằng fixture.
**Points:** 28 · **Tuần:** 4–8 · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO.

---

# Story 5.1 — Project workspace: topbar + stepper + khung Phân cảnh (5đ)

**User story:** As a Content Creator, I want một khung làm việc nhất quán với stepper luôn cho biết tôi đang ở đâu và cần làm gì, so that không bao giờ lạc trong quy trình 6 bước.
**Bối cảnh & giá trị:** "Pipeline là xương sống UI" — nguyên tắc #1 của ux-design. Đây là màn khung mọi story UI khác lắp vào; BR-1 (xem lại + Sửa lại từ đây) đóng luồng quay-lui mà critique v1 chỉ ra bị hở.

## Scope
**In:** layout `/projects/{id}`: topbar (← Dự án, tên, StatusBadge, slot VersionSwitcher); PipelineStepper 6 trạm đủ 6 trạng thái (design-system §3.2); màn Phân cảnh 3 cột (sidebar thumbnail + SceneForm schema-driven + ScenePlayer); header "Đã duyệt x/y"; ApproveBar chuẩn §3.3; autosave 1s; 422→inline theo field_path; chế độ xem-lại readonly + "Sửa lại từ đây".
**Out:** controls chi tiết (5.2); AssetPicker (5.3); scene ops (5.4); RunningState (5.8); VersionSwitcher nội dung (5.9).

## Business Rules
- **BR-1:** trạm done click → readonly + nút "Sửa lại từ đây" → confirm liệt kê bước sẽ stale → mở chế độ sửa (wireframe **Xem lại bước ✓**).
- **BR-2:** trạm locked click → tooltip điều kiện mở ("Hoàn thành Kịch bản trước").
- **BR-3:** autosave lỗi mạng → badge "⚠ chưa lưu" + retry tự động + giữ nội dung local — không mất chữ đang gõ.
- **BR-4:** SceneForm sinh từ JSON Schema — field mới trong schema tự có control mặc định theo type.
- **BR-5:** duyệt từng cảnh ghi trạng thái; header đếm x/y realtime.
- **BR-6 (mới, PO 2026-07-11):** stepper **5 trạm** (Nghiên cứu → Nội dung → Phân cảnh → Hoàn thiện → Xuất bản); trạm done còn cảnh báo hiển thị **✓⚠** + tooltip liệt kê (design-system §3.2).
- **BR-7 (mới):** topbar có nút **▶ Xem bản mới nhất** — mở preview scene_set/video hiện hành từ bất kỳ trạm nào; tên project ⓘ mở ProjectDrawer (5.10).

## UI/UX
- Màn: wireframe **Phân cảnh** + **Xem lại bước ✓**. States: default · loading (skeleton 3 cột) · empty (chưa có scene_set → CTA "Tạo phân cảnh từ kịch bản") · error (load fail → banner thử lại; 422 → inline) · disabled (readonly mode).
- A11y: stepper `nav`+`aria-current`, ←/→+Enter; form label đầy đủ; focus ring token.

## Data & API
- Endpoints: GET/PUT scenes (§6), approve scene (mới — **cập nhật api-spec §6**: `POST scenes/{id}/approve`); GET project tổng hợp trạng thái stepper.
- Contract change: **có** — thêm scene approve + trường `approved` trong scene response.

## Acceptance Criteria
1. **(happy)** Sửa field → Player <100ms + autosave version mới + badge đúng chu trình.
2. **(biên/BR-1)** Click trạm ✓ Kịch bản → readonly; "Sửa lại từ đây" → confirm nêu "[Phân cảnh] sẽ lỗi thời" → vào sửa được.
3. **(lỗi/BR-3)** Ngắt mạng khi gõ → ⚠ chưa lưu; nối lại → tự lưu; chữ không mất (Playwright offline test).
4. **(biên/BR-4)** Thêm field optional vào schema fixture → form tự render control (không sửa FE).
5. **(a11y)** Điều hướng stepper bằng phím đủ; NVDA đọc trạng thái trạm.
6. **(states)** Đủ 5 states có test/screenshot trong PR.

## Test Notes
Playwright là chính (khung + offline + keyboard); vitest cho form generator (schema→controls). Fixture scene_set từ 2.1.

## Quyết định đã chốt
- Duyệt theo từng cảnh (không duyệt cả bước một nút) — khớp wireframe, cho phép làm dở (PO qua wireframe v2).

**Depends:** 2.1, 2.3, 1.5 · **Design:** wireframe **Phân cảnh**, **Xem lại bước ✓** · **FR:** FR-09

---

# Story 5.2 — Edit controls: text/màu/animation/layout/giọng (3đ)

**User story:** As a Content Creator, I want chỉnh chữ, màu, hiệu ứng, bố cục và lời đọc bằng control trực quan, so that tuỳ biến cảnh mà không hiểu gì về JSON.
**Bối cảnh & giá trị:** FR-09 phần "sửa mọi thứ". Dry-run đổi layout (BR-1) chuyển lỗi validate từ "bực mình sau khi lưu" thành "quyết định có thông tin trước khi đổi".

## Scope
**In:** controls text (content marker bold, role, position, màu + highlight picker), animation (type + delay slider); đổi layout với dry-run cảnh báo phần tử bị cắt; voice panel (textarea, giọng nam/nữ, tốc độ).
**Out:** đổi ảnh (5.3); font tuỳ chỉnh (v1.1 — theme quản font).

## Business Rules
- **BR-1:** đổi layout vi phạm ràng buộc → dialog liệt kê đích danh phần tử bị bỏ; huỷ = nguyên trạng.
- **BR-2:** color picker preset theo theme + custom hex có cảnh báo contrast (không chặn).
- **BR-3:** sửa voice text sau produce → audio cũ đánh dấu stale + badge "giọng đọc sẽ tạo lại".
- **BR-4:** bold marker nhập bằng nút **B** trên selection (user không cần gõ `**`).

## UI/UX
- Trong màn Phân cảnh (wireframe). States: theo màn cha; disabled khi readonly. A11y: picker và slider dùng được bằng phím; nút B có shortcut Ctrl+B.

## Data & API
PUT scene (sẵn). Contract change: không.

## Acceptance Criteria
1. **(happy)** Mỗi control đổi → Player phản ánh ngay; lưu đúng schema.
2. **(biên/BR-1)** Ghi đè MediaText (3 text) → MediaFull (max 2): dialog nêu "chữ 't3' sẽ bị bỏ"; huỷ giữ nguyên + quay về lựa chọn trước.
3. **(biên/BR-3)** Sửa lời đọc cảnh đã produce → badge cảnh báo hiện; produce lại chỉ cảnh này (nối 6.1 BR-4).
4. **(BR-4)** Bôi đen chữ bấm B → content có marker + Player highlight.
5. **(a11y)** Slider delay điều khiển bằng ←/→.

## Test Notes
Vitest control-level; Playwright cho dialog dry-run. Contrast check dùng lib sẵn (không tự viết).

## Quyết định đã chốt
- Không WYSIWYG kéo vị trí tự do — position ngữ nghĩa (top/center/bottom) đúng spec schema v1 (chống scope creep).

**Depends:** 5.1 · **Design:** wireframe **Phân cảnh** cột giữa · **FR:** FR-09

---

# Story 5.3 — AssetPicker: đổi ảnh 3 nguồn (3đ)

**User story:** As a Content Creator, I want đổi ảnh minh hoạ từ kho dự án, máy tính, hoặc kho stock, so that cảnh có hình đúng ý mà mọi ảnh đều sạch bản quyền.
**Bối cảnh & giá trị:** FR-20 phía user. "Mọi đường ra là asset_id có license" là hàng rào pháp lý — UI này là nơi duy nhất user đưa ảnh vào hệ thống.

## Scope
**In:** modal 3 tab (Asset dự án / Tải lên / Tìm stock — query prefill từ `media_intent.query_vi`, sửa được, kết quả kèm license badge + nguồn); upload validate loại/kích thước, license=user_upload; dedupe hash; chặn URL trần UI+API; nút "Tạo bằng AI" hiện khi image_gen chain active.
**Out:** thư viện asset workspace-level (v1.1); crop/chỉnh ảnh (v1.1 — fit cover đủ).

## Business Rules
- **BR-1:** kết quả stock hiện license + nguồn **trước** khi chọn.
- **BR-2:** upload trùng hash → dùng lại asset cũ + thông báo nhẹ.
- **BR-3:** 0 key stock → tab Tìm disabled + giải thích; admin thấy link Quản trị, creator thấy "nhờ admin thêm key".
- **BR-4:** ảnh chọn từ stock được Asset Worker tải về MinIO trước khi gán (render không fetch ngoài — glossary rule 4); trong lúc tải hiện trạng thái "đang lấy ảnh…".

## UI/UX
- Modal trong màn Phân cảnh (wireframe). States: default · loading (search spinner + skeleton grid) · empty ("không tìm thấy — thử từ khoá khác" + đổi query) · error (provider lỗi → thông báo + tab khác vẫn chạy) · disabled (BR-3).
- A11y: modal focus-trap ESC; grid ảnh điều hướng mũi tên; mỗi ảnh alt = mô tả + license.

## Data & API
- Endpoints: search stock (proxy qua asset chain — mới, **cập nhật api-spec §6**: `GET /assets/search?q=`), upload asset (mới: `POST /assets/upload`).
- Contract change: **có** — 2 endpoint asset mới.

## Acceptance Criteria
1. **(happy)** Tìm "GPU datacenter" → chọn Pexels → asset có license record → Player hiện ảnh.
2. **(biên/BR-2)** Upload ảnh đã tồn tại → tái dùng, không bản ghi mới.
3. **(biên/BR-3)** 0 key → tab Tìm disabled đúng vai trò; 2 tab kia hoạt động.
4. **(bảo mật)** PUT scene chèn url trần qua API → 422.
5. **(BR-4)** Chọn ảnh stock → trạng thái "đang lấy ảnh" → gán asset_id nội bộ (network tab: render/preview không gọi pexels).

## Test Notes
Mock asset chain; Playwright flow 3 tab. Test bảo mật URL trần giữ vĩnh viễn.

## Quyết định đã chốt
- Upload giới hạn 10MB, jpg/png/webp. ⏳

**Depends:** 5.1, 3.2 · **Design:** wireframe modal Đổi ảnh · **FR:** FR-20

---

# Story 5.4 — Scene ops: thêm/xoá/nhân bản/sắp xếp (2đ)

**User story:** As a Content Creator, I want thêm, xoá, nhân bản, kéo-thả sắp xếp phân cảnh, so that cấu trúc video theo đúng nhịp tôi muốn.
**Bối cảnh & giá trị:** FR-09 danh sách thao tác cảnh. Điểm kỹ thuật then chốt: scene_id bất biến (glossary rule 2) — mọi op chỉ đổi scene_number.

## Scope
**In:** kéo-thả (dnd-kit) + nút ↑↓; thêm cảnh (chọn layout, chèn sau cảnh hiện tại); xoá (confirm); nhân bản; mọi op tạo scene_set version.
**Out:** copy cảnh giữa project (v1.1); bulk ops (không cần).

## Business Rules
- **BR-1:** reorder đổi scene_number giữ scene_id (cache/diff sống nhờ điều này).
- **BR-2:** xoá confirm nêu ảnh hưởng ("video ngắn đi 6s").
- **BR-3:** mọi op = version mới (undo = restore 5.9).
- **BR-4:** nhân bản = scene_id **mới**, nội dung copy (cache key tự khác).

## UI/UX
Sidebar wireframe. States theo màn cha; empty sau xoá hết → CTA thêm cảnh/chạy lại storyboard. A11y: ↑↓ tương đương kéo-thả; confirm dialog focus nút an toàn.

## Data & API
Reorder endpoint (§6 sẵn); thêm/xoá/duplicate (§6 sẵn). Contract change: không.

## Acceptance Criteria
1. **(happy)** Kéo #4 → vị trí 2: số cập nhật, id giữ (verify qua API), version mới.
2. **(biên)** Xoá cảnh đang mở → focus cảnh kế; xoá hết → empty state.
3. **(biên/BR-4)** Nhân bản → id mới; sửa bản sao không ảnh hưởng gốc; cache key khác.
4. **(a11y)** Toàn bộ ops làm được không chuột.

## Test Notes
Vitest reducer ops; Playwright kéo-thả + keyboard path.

## Quyết định đã chốt
- Không undo-stack riêng trong editor — version là undo (nhất quán mô hình versioning). 

**Depends:** 5.1 · **Design:** wireframe sidebar Phân cảnh · **FR:** FR-09

---

# Story 5.5 — Màn Hoàn thiện: timeline + BGM + render trigger (5đ)

**User story:** As a Content Creator, I want tinh chỉnh nhịp, chuyển cảnh, nhạc nền rồi bấm tạo video trên một màn, so that bước cuối gọn trong một chỗ và chỉ render phần thay đổi.
**Bối cảnh & giá trị:** FR-10 + cửa vào FR-11. Gộp Timeline+Render thành trạm "Hoàn thiện" là quyết định IA từ critique (stepper 6 trạm khớp state machine).

## Scope
**In:** TimelineBar (resize chặn dưới audio+300ms + tooltip; transition tại khớp nối); BGM picker (nguồn 6.5) + volume/fade; tổng thời lượng realtime; nghe thử giọng/cảnh; Play toàn bộ (Player nối cảnh — "bản xem thử"); khối Tạo video per-format + tiến độ inline (consume 6.2 — mock trước khi 6.2 xong).
**Out:** render logic (6.2); download/publish (6.3); BGM ingest (6.5).

## Business Rules
- **BR-1:** vào màn chỉ khi mọi cảnh approve (trạm lock + guard API).
- **BR-2:** resize hiện tooltip lý do chặn dưới ("giọng đọc 5.2s + đệm").
- **BR-3:** mọi thay đổi ở màn này → cảnh liên quan dirty → nút "Tạo video" đổi nhãn "Tạo lại (2 cảnh thay đổi)".
- **BR-4:** render đang chạy → điều khiển timeline disabled + giải thích (khớp 6.2 BR-4).

## UI/UX
- Màn: wireframe **Hoàn thiện**. States: default · loading (đang tải timeline) · empty N/A (BR-1 guard) · error (render lỗi → từng cảnh retry) · disabled (BR-4).
- A11y: block resize bằng phím (chọn block → ±100ms bằng ←/→); transition picker là menu chuẩn.

## Data & API
- Endpoints: GET/PATCH timeline (§6), POST render (§7). Contract change: không.

## Acceptance Criteria
1. **(happy)** Kéo 6s→5.5s (audio 5.2) OK; 4s → chặn 5.5 + tooltip; transition đổi nghe/nhìn được khi Play.
2. **(biên/BR-3)** Đổi transition cảnh 3 → chỉ cảnh 3 dirty; nhãn nút "Tạo lại (1 cảnh)".
3. **(lỗi/BR-4)** Đang render → timeline khoá + giải thích; xong → mở lại.
4. **(a11y)** Resize bằng phím hoạt động.
5. **(BGM)** Chọn track + volume → Play nghe được; render (khi 6.2 xong) có nhạc đúng mức.

## Test Notes
Mock render progress qua SSE fixture khi 6.2 chưa xong (interface đã chốt event-catalog).

## Quyết định đã chốt
- "Bản xem thử" Player nối cảnh chấp nhận transition xấp xỉ (đã chốt 2.3). Nhãn UI ghi rõ.

**Depends:** 5.1, 2.4, 6.2 (tiến độ thật) · **Design:** wireframe **Hoàn thiện** · **FR:** FR-10, FR-11

---

# Story 5.6 — Màn Nghiên cứu: nguồn + kiểm chứng (5đ)

> 📄 **Bản chi tiết đầy đủ: [stories/story-5.6-research-review.md](stories/story-5.6-research-review.md)** — story mẫu của template (7 BR, 6 AC, states, data-api, quyết định đã chốt). Áp dụng nguyên trạng.

**Depends:** 4.3, 4.4, 5.8 · **Design:** wireframe **Nghiên cứu** · **FR:** FR-02, FR-04

---

# Story 5.7 — Màn "Nội dung" (Dàn ý collapse + Kịch bản — gộp trạm, PO 2026-07-11) (3đ)

**User story:** As a Content Creator, I want biên tập dàn ý và kịch bản với nguồn tham chiếu bên cạnh, so that sửa nội dung nhanh mà không rời ngữ cảnh fact đã kiểm chứng.
**Bối cảnh & giá trị:** FR-05/06 phía user. Banner warning từ node (lệch số, title cắt — 4.5) phải "đập vào mắt" tại đây — đây là chốt chặn con người cuối trước khi nội dung thành hình.

## Scope
**In:** Dàn ý 7 card section editable; Kịch bản (title/description/tags + voice_over textarea); panel phải fact PASS ghim + [source] link; "Sinh lại bằng AI" → RunningState; autosave; render `warnings[]` từ version content thành banner + "xem chỗ lệch".
**Out:** rich-text đầy đủ (plain + marker đủ v1); đếm thời lượng đọc chính xác (hiện ước tính từ ký tự).

## Business Rules
- **BR-1:** warnings hiện banner vàng đầu màn; loại `number_mismatch` có nút highlight đúng con số lệch 2 phía.
- **BR-2:** [source_id] render link → mở panel nguồn tương ứng.
- **BR-3:** ước tính thời lượng đọc hiện cạnh voice_over (≈ ký tự/tốc độ) — lệch mục tiêu ±20% → nhắc nhẹ.

## UI/UX
- Màn: wireframe **Kịch bản** (Dàn ý cùng khung, editor 7 card). States: default · loading (RunningState khi sinh) · empty N/A (luôn có content khi tới bước) · error (banner) · disabled (readonly mode 5.1 BR-1).
- A11y: 7 card tab-order đúng; banner warning `role=alert`.

## Data & API
- Endpoints: versions PUT/GET (§3). Contract: `warnings[]` đã chuẩn ở 4.5.

## Acceptance Criteria
1. **(happy)** Sửa → version mới autosave; approve → RunningState bước kế.
2. **(biên/BR-1)** Version có number_mismatch → banner + highlight đúng số 2 phía.
3. **(BR-3)** Voice_over dài gấp rưỡi mục tiêu → nhắc thời lượng.
4. **(a11y)** Screen reader đọc banner khi vào màn.

## Test Notes
Fixture version có warnings mỗi loại. Playwright: flow sửa → sinh lại → so version.

## Quyết định đã chốt
- **Gộp thành 1 trạm "Nội dung"** (PO 2026-07-11): dàn ý là panel trên cùng — mở rộng khi chờ duyệt, collapse sau duyệt; kịch bản bên dưới. Backend giữ nguyên 2 step/2 version/2 gate (4.5 không đổi). Sửa dàn ý sau khi kịch bản tồn tại → kịch bản stale (cascade 1.5).

**Depends:** 4.5, 5.8 · **Design:** wireframe **Kịch bản** · **FR:** FR-05, FR-06

---

# Story 5.8 — RunningState component + tích hợp mọi bước (3đ) 🆕

**User story:** As a Content Creator, I want màn "đang chạy" nhất quán cho mọi bước AI với thông điệp thật và nút huỷ/chạy ngầm, so that tôi luôn biết hệ thống đang làm gì và không bao giờ nhìn spinner câm.
**Bối cảnh & giá trị:** Phát hiện lớn nhất của design-critique: trạng thái chạy là 50% trải nghiệm nhưng v1 không thiết kế. Component này là "gương mặt" của pipeline.

## Scope
**In:** component theo design-system §3.4: message SSE mới nhất + elapsed + progress (indeterminate khi không % thật) + Chạy ngầm + Huỷ (gọi 4.7); error state phân loại (hết-chain: render danh sách provider+lý do từ AllProvidersFailed; khác: message dịch nghĩa) + Thử lại + chi tiết collapse; tích hợp: mọi Duyệt→bước AI đi qua nó; stepper ●% khi ngầm.
**Out:** API cancel (4.7); notification (7.4).

## Business Rules
- **BR-1:** chỉ hiện message SSE thật — không bịa %; không % → indeterminate.
- **BR-2:** error hết-chain: admin thấy link Quản trị › Providers; creator thấy "báo quản trị viên" (đúng vai).
- **BR-3:** huỷ confirm khi run >30s ("giữ kết quả các bước đã xong").
- **BR-4:** sub-state "đang huỷ…" cho tới event xác nhận (4.7 BR-1).

## UI/UX
- Màn: wireframe **RunningState + Error**. States: chính nó là loading-state; error như wireframe; empty/disabled N/A.
- A11y: `aria-live=polite` message; nút focus được; reduced-motion tôn trọng (progress không nhấp nháy).

## Data & API
Consume SSE (1.6) + cancel (4.7). Contract change: không.

## Acceptance Criteria
1. **(happy)** Duyệt Kịch bản → RunningState "Đang tạo phân cảnh…" message thật → tự chuyển editor khi xong.
2. **(biên)** Chạy ngầm → dashboard card ●% → click quay lại đúng màn đúng tiến độ.
3. **(lỗi/BR-2)** AllProvidersFailed → danh sách provider+lý do; đúng nội dung theo vai admin/creator.
4. **(BR-4)** Huỷ → "đang huỷ…" → về trạng thái đã huỷ kèm "chạy tiếp?".
5. **(a11y)** NVDA đọc message cập nhật; reduced-motion không animation pulse.

## Test Notes
Storybook/fixture cho 4 trạng thái component; Playwright flow duyệt→running→auto-chuyển.

## Quyết định đã chốt
- Không ước lượng "còn X phút" v1 (dễ sai gây mất tin) — chỉ elapsed + message. ⏳

**Depends:** 1.6, 4.1, 4.7 · **Design:** wireframe **RunningState** · **FR:** NFR-1

---

# Story 5.9 — VersionSwitcher + màn So sánh/History (3đ) 🆕

**User story:** As a Content Creator, I want xem, so sánh, khôi phục phiên bản ngay tại bước đang đứng, so that thử nghiệm nội dung thoải mái và quay lại trong 2 cú click.
**Bối cảnh & giá trị:** Critique v1: History tách rời ngữ cảnh khiến versioning "có mà như không". Story này biến engine 1.5 thành giá trị nhìn thấy được — lý do user dám bấm "Sinh lại".

## Scope
**In:** dropdown `v3 ▾` topbar (list: thời gian/tác giả/badge stale+tooltip); Xem (readonly overlay); So sánh với hiện hành (màn diff side-by-side text; scene-diff list added/removed/changed); Khôi phục (confirm hệ quả — dùng service 1.5); History tổng (route phụ bảng mọi bước).
**Out:** visual diff 2 preview (v1.1 — đã ghi nhận); so sánh chéo step (BR 1.5-6 cấm).

## Business Rules
- **BR-1:** khôi phục từ switcher = service 1.5 duy nhất (một đường).
- **BR-2:** đang có thay đổi chưa autosave → chuyển version hoãn tới lưu xong (≤1.5s), không mất chữ.
- **BR-3:** badge stale tooltip nêu nguồn gốc ("dựa trên Nghiên cứu v2 — đã thay bằng v1").
- **BR-4:** diff hiển thị thêm/xoá bằng prefix + màu (không chỉ màu — a11y).

## UI/UX
- Màn: wireframe topbar (vswitch) + **So sánh phiên bản**. States: default · loading (diff đang tính) · empty (chỉ 1 version → dropdown ghi "chưa có phiên bản khác") · error banner · disabled (readonly vẫn xem/so sánh được, không khôi phục khi RUNNING).
- A11y: dropdown phím + ESC; diff đọc được bằng screen reader (prefix "thêm:"/"xoá:").

## Data & API
Endpoints versions/compare/restore (§3 — 1.5 đã chuẩn `staled_steps`). Contract change: không.

## Acceptance Criteria
1. **(happy)** So sánh script v1↔v2 → highlight đúng dòng; đóng quay về đúng chỗ.
2. **(biên)** Khôi phục scene_set v2 → confirm "Hoàn thiện sẽ lỗi thời" → trạm sau chuyển stale trên stepper.
3. **(biên/BR-2)** Đang gõ → chuyển version → hoãn lưu xong mới chuyển, không mất chữ.
4. **(empty)** Bước 1 version → dropdown thông báo đúng, không lỗi.
5. **(quyền)** Project RUNNING → nút khôi phục disabled + tooltip.

## Test Notes
Fixture 3 version có stale; Playwright flow so sánh→khôi phục→stepper stale.

## Quyết định đã chốt
- History tổng giữ (route phụ, ít dùng) — giá trị audit; không đầu tư UI đẹp cho nó v1. ⏳

**Depends:** 1.5, 5.1 · **Design:** wireframe **So sánh phiên bản** + topbar · **FR:** SRS §6

---

# Story 5.10 — ProjectDrawer: Thông tin & Cài đặt dự án (2đ) 🆕

**User story:** As a Content Creator, I want mở nhanh thông tin tổng quan và cài đặt của dự án từ bất kỳ màn nào, so that quay lại project cũ vẫn nắm ngay "video này nói gì, trạng thái sao, tốn bao nhiêu" và chỉnh cấu hình không phải rời workspace.
**Bối cảnh & giá trị:** Gap kép từ review luồng: (1) FR-01 cho sửa project nhưng không màn nào chứa PATCH; (2) vào project 2 tuần tuổi mất phương hướng vì nhảy thẳng bước hiện tại. Một drawer giải cả hai, không thêm trạm/route.

## Scope
**In:** drawer trượt phải (design-system §3.7), mở từ tên project ⓘ topbar; tab **Thông tin**: tóm tắt 2 câu (AI sinh 1 lần sau research, cache), verdict tổng + link, thời lượng/số cảnh/format/giọng/theme, **chi phí AI ước tính** (sum llm_usage theo project), nguồn count, hoạt động gần đây (5 dòng từ status_history + version log); tab **Cài đặt**: đổi tên/format/giọng mặc định/theme (PATCH), Nhân bản, Lưu trữ (chuyển từ dashboard card menu vào đây).
**Out:** ghi chú/comment (v1.1); chia sẻ project (ngoài scope); chỉnh sâu chi phí (màn Vận hành lo).

## Business Rules
- **BR-1:** đổi giọng mặc định → cảnh chưa produce dùng giọng mới; cảnh đã produce giữ nguyên (đổi từng cảnh ở editor) — nêu rõ trong UI khi đổi.
- **BR-2:** đổi format/theme → cảnh báo hệ quả render lại (tái dùng pattern 10.2 BR-2).
- **BR-3:** Lưu trữ từ drawer confirm như dashboard; project archive mở drawer chỉ-đọc + nút Khôi phục.
- **BR-4:** chi phí hiển thị nhãn "ước tính" (nhất quán 3.5 BR-4).

## UI/UX
- Màn: wireframe **Drawer**. States: default · loading (skeleton dòng) · empty N/A · error (từng khối độc lập — chi phí lỗi không chặn thông tin) · disabled (archive read-only BR-3).
- A11y: focus-trap, ESC đóng, trả focus về tên project; tabs phím.

## Data & API
- Endpoint mới `GET /projects/{id}/summary` (gộp: metadata + verdict + cost + activity) → **cập nhật api-spec §2**; PATCH sẵn có.
- Tóm tắt AI: thêm output nhẹ vào node research (1 câu gọi tier cheap, cache trong project).
- Contract change: **có** — endpoint summary.

## Acceptance Criteria
1. **(happy)** Mở drawer từ màn Phân cảnh → đủ thông tin đúng dữ liệu (so seed); đóng ESC quay đúng focus.
2. **(biên/BR-1)** Đổi giọng khi 5/8 cảnh đã produce → thông báo rõ phạm vi ảnh hưởng; produce lại chỉ 3 cảnh mới dùng giọng mới.
3. **(biên/BR-3)** Project archive → drawer read-only + Khôi phục hoạt động.
4. **(lỗi)** Endpoint cost lỗi → khối chi phí hiện "không tải được" + thử lại, phần khác nguyên vẹn.
5. **(quyền)** 🅞 — creator khác 403.

## Test Notes
Vitest tab/focus-trap; integration summary endpoint (so khớp seed llm_usage).

## Quyết định đã chốt
- Tóm tắt 2 câu sinh 1 lần sau research (không realtime) — đủ dùng, rẻ. ⏳

**Depends:** 5.1, 1.3, 3.5 (llm_usage) · **Design:** wireframe **Drawer** · **FR:** FR-01
