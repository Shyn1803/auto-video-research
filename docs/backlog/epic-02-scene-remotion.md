# Epic 2 — Scene JSON contract + Remotion foundation + TTS tiếng Việt

**Goal:** Milestone M1 — video 30s 9:16 giọng Việt + subtitle sync từ Scene JSON viết tay. Spike 2 rủi ro kỹ thuật lớn nhất, chạy song song Epic 1.
**Points:** 26 · **Tuần:** 1–3 (2.6: tuần 4–6, sau M1) · Chuẩn đầy đủ [story-template.md](story-template.md); ⏳ = đề xuất BA chờ PO xác nhận.

---

# Story 2.1 — Scene JSON schema v1: Pydantic + export + Zod (5đ)

**User story:** As a developer, I want một nguồn schema duy nhất mà backend, frontend và Remotion cùng dùng, so that ba bên không bao giờ lệch contract trung tâm của hệ thống.
**Bối cảnh & giá trị:** Scene JSON là contract quan trọng nhất (ADR-4): preview, cache, render, versioning, editor đều đứng trên nó. Lệch schema giữa FE/BE/Remotion là loại bug đắt nhất để tìm — story này mua sự an toàn đó bằng codegen + CI gate.

## Scope
**In:** Pydantic models đầy đủ theo [scene-json-schema.md](../specs/scene-json-schema.md) (VideoProject/Scene/5 layout/các type §3); validator ngoài-schema §5 hai chế độ `auto_fix`/`strict`; `make gen-scene-schema` (JSON Schema → Zod — Zod ở đây **là schema prop chính thức của `<Composition>`** Remotion, không phải lựa chọn tuỳ ý, [remotion-integration.md](../specs/remotion-integration.md) §2.1); fixtures share pytest/vitest (hợp lệ mỗi layout + ≥3 lỗi); CI gate diff; hàm canonical hash.
**Out:** schema v2 elements (chart/video/karaoke); migration runner (viết khi có bump đầu tiên); UI form (5.1 tiêu thụ).

## Business Rules
- **BR-1:** canonical hash: sort keys, UTF-8 NFC, bỏ `scene_number` — đổi thứ tự cảnh không phá cache.
- **BR-2:** `auto_fix` chỉ sửa vi phạm "cắt được" (thừa phần tử, duration lệch, thiếu default) + log warning; kiểu dữ liệu sai → lỗi kể cả auto_fix.
- **BR-3:** mọi lỗi strict có `field_path` máy-đọc-được để FE map inline (spec error format).
- **BR-4:** fixtures là contract test hai chiều — thêm rule validator mới bắt buộc kèm fixture fail tương ứng.

## UI/UX
N/A trực tiếp — nhưng chất lượng `field_path` quyết định UX lỗi ở editor (5.1).

## Data & API
- Bảng: chưa (scenes ở 4.6). File sinh: `packages/remotion-templates/schema/scene-1.0.0.json` + `schema.ts` (Zod) commit vào repo.
- Contract change: khởi tạo contract trung tâm — PR này chính là spec-as-code của scene-json-schema.md.

## Acceptance Criteria
1. **(happy)** Fixture hợp lệ pass pytest+vitest; fixture lỗi fail cả hai cùng field_path.
2. **(biên/BR-2)** 6 texts vào TextFocus (max 3): auto_fix cắt còn 3 + warning; strict → 422 `texts`.
3. **(biên/BR-1)** Đổi scene_number/thứ tự key → hash không đổi; đổi 1 ký tự content → hash đổi.
4. **(lỗi)** `duration_ms: "abc"` → lỗi kiểu cả 2 chế độ (không auto_fix).
5. **(CI)** Sửa Pydantic không chạy gen → CI fail đúng thông điệp.

## Test Notes
Từng rule §5 một unit test đặt tên theo rule; property test hash (random permutation không đổi hash). Fixtures đặt tại `packages/remotion-templates/schema/fixtures/`.

## Quyết định đã chốt
- 11 layout class v1, tên PascalCase canonical (Hero/TextFocus/MediaFull/MediaText/Comparison/BigNumber/Chart/VersusTable/List/Quote/Code) — thêm class = minor version + preset json; class do Classifier chọn, không phải AI (layout-engine.md).
- Số liệu motion chuyển thể từ taste-skill (video-taste.md), hiệu chỉnh nhịp web→video (chậm hơn ~1.5× vì giọng đọc dẫn nhịp thay vì scroll người dùng).

**Depends:** 1.1 · **Design:** — · **FR:** FR-08, AR-3

---

# Story 2.2 — Remotion base layer: SceneRenderer + primitives + 5 preset cơ bản + theme (5đ)

**User story:** As a viewer, I want video có bố cục đẹp nhất quán trên cả khung dọc lẫn ngang, so that nội dung trông chuyên nghiệp trên mọi nền tảng.
**Bối cảnh & giá trị:** Tầng hiện thực Remotion của Layout Engine ([layout-engine.md](../specs/layout-engine.md) §11): **không có composition cứng per-layout** — chỉ 1 `SceneRenderer` đọc preset (data) + bộ primitive theo component-kind + motion wrapper + theme provider. Đây là "bộ mặt" sản phẩm và nơi kiểm chứng NFR render sớm nhất (6.4).

## Scope
**In:** `SceneRenderer` = **`<Composition>` thật của Remotion** với `schema` (Zod, 2.1) + **`calculateMetadata`** resolve width/height/durationInFrames động theo `format`/`duration_ms` ([remotion-integration.md](../specs/remotion-integration.md) §2.1 — không tự viết logic resolve ngoài Remotion); mỗi track MotionPlan render bằng `<Sequence from={ms→frames} durationInFrames layout="none">` (bắt buộc `layout="none"` — mặc định Sequence bọc AbsoluteFill chồng đè, phá preset flex §6); primitives cơ bản `Heading/Body/Media(kenburns)/Subtitle/Watermark` (`**bold**` → highlight); `motion/Animated` wrapper dùng `interpolate()`/`spring()` thật của Remotion (§2.3) + bảng preset khởi điểm; `ThemeProvider` + theme mặc định từ design tokens; **5 preset json** Hero/TextFocus/MediaFull/MediaText/Comparison (mỗi preset × 2 format — layout-engine §6–7); `supportedSchemaRange`; render CLI; render test class×format + golden-frame. Trigger skill: dev-guide.md §2.1.
**Out:** primitives dữ liệu + 6 preset + motion đặc thù (2.6); theme 2–3 (10.2 = chỉ thêm json vào `theme/themes/`); transition ngoài enum v1; watermark/intro-outro tuỳ chỉnh (v1.1).

## Business Rules
- **BR-1:** template không fetch mạng — mọi media là đường dẫn cục bộ trong props (glossary rule 4).
- **BR-2:** text tràn → auto-shrink tới 60% cỡ gốc rồi ellipsis — không bao giờ vỡ khung.
- **BR-3:** scene ngoài schema range → throw mã `SCHEMA_RANGE`, không render-sai-lặng-lẽ.
- **BR-4:** font nhúng trong package (Inter + font Việt fallback) — render không phụ thuộc font hệ thống.
- **BR-5:** mỗi layout = **constraint preset flexbox** dạng data (slots/gap/padding + responsive rules — layout-engine §6–7), không toạ độ tuyệt đối; thêm class mới = thêm preset json (+ primitive nếu có kind mới) — SceneRenderer không đổi.
- **BR-6:** primitive không biết layout — chỉ render nội dung + motion trong slot được cấp; mọi animation đi qua `Animated` wrapper (primitive không tự viết spring).
- **BR-7 (số liệu — video-taste.md §3, mới):** ease mặc định `cubic-bezier(0.16,1,0.3,1)`; duration entrance 450–600ms (dial theme 4–7, mặc định); theme khai `motion_intensity`/`visual_density` (layout-engine §8) — `Animated` đọc dial để scale duration, không hardcode 1 giá trị.

## UI/UX
Theme video ăn theo tokens §2 design-system (đồng bộ nhận diện app↔video). PO duyệt visual 1 lần trên 5 layout × 2 format (10 ảnh chụp trong PR).

## Data & API
N/A — package TS thuần. Contract: `supportedSchemaRange` trong package.json.

## Acceptance Criteria
1. **(happy)** Fixture mỗi layout render 2 format: đúng resolution, duration ±100ms; PO duyệt visual.
2. **(biên/BR-2)** Heading 200 ký tự → shrink+ellipsis không tràn (snapshot test).
3. **(biên)** Cùng scene 9:16 vs 16:9 → bố cục responsive đúng thiết kế từng layout.
4. **(lỗi/BR-3)** Scene 2.0.0 vào template ^1.0 → lỗi SCHEMA_RANGE.
5. **(BR-4)** Render trong container sạch không font hệ thống → chữ Việt đúng (có dấu).

## Test Notes
Render test CI: 1 layout × 1 format mỗi PR (nhanh); đủ 10 tổ hợp nightly. Baseline screenshot cho visual regression từ story này.

## Quyết định đã chốt
- ⏳ Nhạc count-up cho `stat` chỉ khi content là số thuần — text lẫn số thì hiện tĩnh (tránh hiệu ứng sai).

**Depends:** 2.1 · **Design:** design-system §2 tokens · **FR:** FR-08, FR-11

---

# Story 2.3 — Remotion Player preview trong Next.js (3đ)

**User story:** As a Content Creator, I want xem phân cảnh ngay trong trình duyệt khi chỉnh sửa, so that vòng lặp chỉnh–xem tính bằng giây thay vì chờ render.
**Bối cảnh & giá trị:** "Preview tức thì" là lời hứa NFR-1 và lý do chọn kiến trúc Remotion Player (ADR-6: Player và worker cùng template → preview = render, không lệch pixel).

## Scope
**In:** `ScenePlayer` wrap `<Player>` thật của `@remotion/player` (props: `component`, `inputProps`=scene JSON, `durationInFrames`, `fps`, `compositionWidth/Height` theo format, `controls`, `ref`) — [remotion-integration.md](../specs/remotion-integration.md) §2.4; import cùng package composition với worker; scrub dùng `playerRef.current.seekTo(frame)`, progress dùng `playerRef.current.addEventListener('frameupdate', ...)` (không tự viết cơ chế theo dõi); **2 composition riêng trong `Root.tsx`** (§4.1): `Scene` (1 cảnh — dùng ở màn Phân cảnh 5.1 + render-worker) và `Video` (nối toàn bộ cảnh qua `<Sequence>` + `<Audio>` BGM — chỉ dùng ở Player màn Hoàn thiện 5.5, KHÔNG bao giờ render thật); lazy-load + skeleton; chế độ frame tĩnh (thumbnail cho 5.1, dùng `seekTo` + capture).
**Out:** editor form (5.1); audio waveform (không cần v1).

## Business Rules
- **BR-1:** props đổi → re-render ngay (key theo content hash), không giữ state cũ.
- **BR-2:** chưa có audio produce → phát hình không tiếng + hint "chưa tạo giọng đọc"; có audio → phát đồng bộ.
- **BR-3:** bundle Remotion lazy — route không cần preview không tải chunk này.

## UI/UX
- Màn: cột phải wireframe **Phân cảnh**. States: default (player) · loading (skeleton tỉ lệ đúng format) · empty (chưa chọn cảnh → hướng dẫn) · error (composition crash → thông báo + mã lỗi, không trắng trang) · disabled N/A.
- A11y: controls có aria-label; Space = play/pause khi focus player.

## Data & API
N/A — client-side thuần, props từ state.

## Acceptance Criteria
1. **(happy)** Sửa scene JSON state → player cập nhật <100ms không network call.
2. **(biên/BR-2)** Cảnh chưa produce → im lặng + hint; sau produce → có tiếng đúng timing.
3. **(nhất quán)** 1 frame giữa: player vs render CLI cùng scene giống nhau (kiểm tay, ghi vào PR).
4. **(perf/BR-3)** Trang Dashboard không tải remotion chunk (kiểm network).
5. **(lỗi)** Composition throw → error state có mã, app không crash (error boundary).

## Test Notes
Vitest component với fixture 2.1; kiểm bundle bằng next build analyze trong PR đầu.

## Quyết định đã chốt
- Preview "cả video" ở màn Hoàn thiện dùng Player nối cảnh — chấp nhận transition xấp xỉ; transition thật được ffmpeg assembler áp vào MP4 cuối từ scene cache (6.2). Ghi rõ trong UI "bản xem thử". ⏳

**Depends:** 2.2 · **Design:** wireframe **Phân cảnh** cột phải · **FR:** FR-09, AR-4

---

# Story 2.4 — TTS adapter + edge-tts tiếng Việt (5đ)

**User story:** As a Content Creator, I want giọng đọc tiếng Việt tự nhiên kèm timestamp từng từ, so that video có lời thuyết minh và phụ đề khớp mà không cần thu âm.
**Bối cảnh & giá trị:** Giọng đọc là 50% chất lượng cảm nhận của video tin tức. edge-tts là lựa chọn 0đ tốt nhất cho tiếng Việt (HoaiMy/NamMinh) nhưng là service không chính thức → adapter interface là bảo hiểm (rủi ro đã ghi plan §5).

## Scope
**In:** `TTSAdapter` base (available/synthesize/ProviderError); adapter `edge_tts` (2 giọng, speed); MP3 + duration + word timestamps; cache MinIO theo hash(text+voice+speed+engine); mock adapter test; endpoint `POST scenes/{id}/tts-preview`.
**Out:** viXTTS/F5/FPT adapters (chèn theo plan §5 khi cần); chuẩn hoá số→chữ (trách nhiệm prompt script 4.5 BR-2).

## Business Rules
- **BR-1:** text rỗng/toàn khoảng trắng → lỗi validate, không gọi engine.
- **BR-2:** text >500 ký tự → chia theo câu, ghép audio + nối timestamps offset chính xác.
- **BR-3:** cache hit không gọi engine (counter đo được).
- **BR-4:** lỗi engine → `ProviderError(retryable)` — adapter không tự retry (việc của router/node).
- **BR-5:** voice_id logic (`female_default`) map engine voice qua config — đổi engine không đổi dữ liệu scene.

## UI/UX
Tiêu thụ bởi khối Giọng đọc (5.2) + nút Nghe thử (5.5, 1.3 modal). Preview trả URL audio ngắn hạn.

## Data & API
- Storage: `audio/{project}/{hash}.mp3` (ARCHITECTURE §6); bảng ghi audio metadata trong scene JSON (spec §3.4 — worker điền).
- Endpoint mới: tts-preview (đã có api-spec §6). Contract change: không.

## Acceptance Criteria
1. **(happy)** "Xin chào các bạn" nữ 1.0 → MP3 + timestamps từng từ; PO nghe duyệt chất lượng 3 câu mẫu.
2. **(biên/BR-2)** Đoạn 800 ký tự → 1 audio liền mạch, timestamps liên tục đúng offset (test tự động so tổng duration).
3. **(biên/BR-3)** Gọi lần 2 cùng input → cache hit, engine counter không tăng.
4. **(lỗi/BR-4)** Engine 403 → ProviderError(retryable=true); mock node retry hoạt động.
5. **(BR-5)** Đổi config map voice → cùng scene ra giọng khác, không sửa scene JSON.

## Test Notes
Test edge-tts thật đánh dấu `@external` chạy nightly; PR dùng mock. Fixture câu Việt có số, tên riêng, từ mượn ("GPT", "benchmark").

## Quyết định đã chốt
- 2 giọng v1 (nữ mặc định) — thêm giọng = config, không story mới (PO qua wireframe).

**Depends:** 1.1 · **Design:** khối Giọng đọc wireframe **Phân cảnh** · **FR:** FR-19

---

# Story 2.5 — Subtitle từ timestamps + burn vào video (3đ)

**User story:** As a viewer, I want phụ đề khớp chính xác lời đọc, so that xem không bật tiếng (đa số trên mobile) vẫn hiểu trọn nội dung.
**Bối cảnh & giá trị:** 70-80% video mạng xã hội được xem không tiếng — subtitle sync không phải tính năng phụ mà là điều kiện sống của định dạng. Timestamps từ 2.4 làm việc này gần miễn phí.

## Scope
**In:** **kiểm tra `@remotion/captions` trước** (Remotion Agent Skill `/remotion-captions` — [remotion-integration.md](../specs/remotion-integration.md) §1) — nếu khớp constraint §3.6 scene-json-schema thì dùng package chính chủ thay tự viết; nếu không khớp (ví dụ quy tắc "không tách cụm số+đơn vị" đặc thù tiếng Việt), giữ thuật toán tự viết: nhóm timestamps → segments (≤42 ký tự/dòng, cắt ranh giới từ, ưu tiên dấu câu); component subtitle style `line` trong template; sinh segments lúc chuẩn bị props (không lưu trong Scene JSON — spec §3.4); unit test thuật toán.
**Out:** karaoke style (schema v2); vị trí/size subtitle tuỳ chỉnh (v1.1); file .srt xuất riêng (v1.1 — YouTube tự sinh từ audio).

## Business Rules
- **BR-1:** không tách cụm số+đơn vị ("92,5 phần trăm" nguyên vẹn 1 segment).
- **BR-2:** segment hiển thị tối thiểu 700ms — ngắn hơn gộp với segment kế.
- **BR-3:** `subtitle.enabled=false` → không render, không chừa khoảng trống.
- **BR-4:** segment vượt 42 ký tự do 1 từ quá dài → cho phép tràn mềm (không cắt giữa từ).

## UI/UX
Style theo template (nền đen mờ, chữ trắng, safe-area đáy tránh UI TikTok/YouTube). Bật/tắt ở editor (5.2 dùng field sẵn).

## Data & API
N/A — pure function + component. Contract change: không.

## Acceptance Criteria
1. **(happy)** Cảnh 6s → phụ đề đúng thời điểm (lệch ≤200ms, kiểm tay 3 mẫu), 1 dòng, không tràn safe-area.
2. **(biên/BR-1)** "92,5 phần trăm" nguyên cụm 1 segment.
3. **(biên/BR-2)** Từ đơn 300ms → gộp, không nháy.
4. **(BR-3)** Tắt subtitle → khung hình dùng trọn không gian.
5. **(unit)** Bộ test câu dài/số/từ ghép/dấu câu pass.

## Test Notes
Thuật toán là pure function — property test: mọi input, tổng text segments == text gốc (không mất chữ).

## Quyết định đã chốt
- Subtitle bật mặc định mọi cảnh có voice (PO qua nguyên tắc mobile-first của định dạng).

**Depends:** 2.2, 2.4 · **Design:** template vùng subtitle · **FR:** FR-19

---

# Story 2.6 — 6 layout class dữ liệu & cấu trúc: constraint preset + motion preset (5đ) 🆕

**User story:** As a Content Creator, I want các bố cục chuyên cho số liệu, so sánh, danh sách, trích dẫn và code — với hiệu ứng chuyển động phù hợp từng loại nội dung, so that video tin công nghệ đa dạng và truyền tải đúng bản chất thông tin.
**Bối cảnh & giá trị:** Feedback PO 2026-07-11 + kiến trúc Layout Engine ([layout-engine.md](../specs/layout-engine.md)): mỗi layout class = **constraint preset (flexbox) + motion preset theo loại component** — không phải template toạ độ cứng. Story này dựng 6 class nhóm Dữ liệu + Cấu trúc (`BigNumber`, `Chart`, `VersusTable`, `List`, `Quote`, `Code`) và **bảng motion preset dùng chung** (layout-engine §9) cho cả 5 class cơ bản của 2.2.

## Scope
**In:** 6 composition = constraint preset flex (slots, gap, padding — layout-engine §6) + responsive rules 2 format (§7); **motion preset table** (§9.1) + **renderer cho MotionPlan** (§9.3): mỗi track = `<Sequence from>` + Animated, sync_points = interpolate mốc tuyệt đối — countUp kết thúc theo `end_by_ms`, list stagger theo `enter_at_ms` từng item, highlight theo sync_point; áp cả cho 5 class 2.2; Pydantic + Zod 6 element types (mở rộng 2.1); SceneForm control tương ứng; gallery override trong editor; render test matrix 11 class × 2 format.
**Out:** chart line/pie, Timeline/Gallery class, lower_third (v1.1 — spec đã ghi); solver tổng quát (v1.1); classifier (4.6).

## Business Rules
- **BR-1:** dữ liệu chart/table/number là **inline trong Scene JSON**, không fetch ngoài (glossary rule 4); constraints theo spec §3.6 (points 2–6, rows 2–4, items 3–5…).
- **BR-2:** `quote_block` là phát ngôn thật → bắt buộc `source_id` truy được fact-check; không nguồn → validator chặn (strict) / engine hạ class về TextFocus (auto_fix + warning).
- **BR-3:** List stagger khớp voice: item i xuất hiện khi từ đầu tiên của ý i được đọc (map qua timestamps); không có timestamps → fallback 90ms/item (dial 4–7) hoặc 60ms/item (dial 8–10) — video-taste.md §3.
- **BR-4:** số trong number/chart/table phải khớp fact đã kiểm chứng — mapper 4.6 chỉ điền từ claims/key_facts, kèm [source_id] trong metadata cảnh.
- **BR-5:** mỗi class mới pass đủ render test 2 format + auto-shrink (BR 2.2-2) trước khi được **bật trong rule table của Layout Classifier** (4.6) — AI không biết đến danh sách layout, việc bật/tắt class là config của engine.

## UI/UX
- Editor: gallery + optgroup select (wireframe **Phân cảnh**); SceneForm sinh control theo element type (bảng editable cho points/rows/items). States theo màn cha; form control mới có empty hint ("thêm 2–6 cột dữ liệu").
- Video: style theo design tokens; count-up dùng JetBrains Mono; winner badge dùng bộ màu status.

## Data & API
- Schema: 6 element types mới trong `scene.py` → regenerate JSON Schema/Zod (vẫn 1.0.0 — chưa release, không cần migration) → **cập nhật scene-json-schema.md đã làm** + fixtures mỗi layout (hợp lệ + lỗi).
- Prompt: `storyboard.generate` guidance đã cập nhật (prompts.md §7); mapper 4.6 mở rộng bảng content-type → layout.
- Contract change: **có** — schema mở rộng + fixtures.

## Acceptance Criteria
1. **(happy)** Fixture 6 layout render 2 format đúng spec; PO duyệt visual (12 ảnh trong PR); count-up/bar-grow/stagger chạy đúng nhịp.
2. **(biên/BR-3)** List 4 items với voice 8s → xuất hiện đúng lúc từng ý được đọc (kiểm tay 2 mẫu + unit map timestamps).
3. **(biên/BR-2)** quote không source_id: strict → 422; auto_fix → hạ TextFocus + warning.
4. **(lỗi)** chart 7 points → validator chặn đúng field_path; table label 25 ký tự → 422.
5. **(pipeline)** Bật 6 class trong rule table classifier → storyboard 3 topic thật (Ollama): classifier chọn ≥3 class mới hợp lý theo semantic profile, scene_set strict-valid (nghiệm thu tay — AI không hề biết layout).
6. **(editor)** Ghi đè sang Chart trong gallery → form đổi sang bảng nhập points; Player cập nhật ngay.

## Test Notes
Fixtures 6 layout vào bộ share (2.1); render test matrix nightly 22 tổ hợp; unit stagger-mapping là pure function.

## Quyết định đã chốt
- 6 layout này thuộc v1 (không đợi v2) — quyết định PO 2026-07-11. Lịch: tuần 4–6, sau M1, không chặn critical path (DEV-B làm song song Epic 5).
- ⏳ Màu chart: 1 màu primary + highlight — không palette nhiều màu (nhất quán theme, tránh loè loẹt).

**Depends:** 2.1, 2.2, 2.4 (timestamps) · **Design:** wireframe **Phân cảnh** gallery · **FR:** FR-08, FR-11

---

## 🏁 M1 (cuối tuần 2)
JSON tay 5 cảnh đủ 5 layout → TTS → render CLI → MP4 30s 9:16 giọng Việt + phụ đề sync. PO nghiệm thu, lưu video làm baseline chất lượng.
