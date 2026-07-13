# Scene JSON Schema Specification

**Version:** 1.0.0 (schema_version) · Tài liệu: v1.0 · Đi kèm [SRS.md](../SRS.md) FR-08
**Vai trò:** Scene JSON là **contract render** — input duy nhất của Remotion (Player + Render Worker), đơn vị cache. Từ v1.0 (2026-07-11) nó được định vị là **đầu ra resolved của Layout Engine** ([layout-engine.md](layout-engine.md)): AI sinh Semantic Storyboard (không layout) → engine deterministic phân loại layout, giải preset ràng buộc, gắn theme/motion → Scene JSON. Scene lưu kèm `semantic_tree` gốc; `layout` là kết quả classifier, user override được (`layout_override`). Editor sửa ở mức semantic tree; mọi field bố cục dưới đây do engine điền.

**Nguồn schema duy nhất:** Pydantic model tại `backend/app/schemas/scene.py` → export JSON Schema → Zod tại `packages/remotion-templates/src/schema.ts` validate cùng file JSON Schema đó. **Không được định nghĩa tay ở 2 nơi.** Model `SemanticStoryboard` là schema strict riêng cho output LLM; `VideoProject`/`Scene` dưới đây là schema **resolved**, chỉ được Layout Engine tạo.

---

# 1. Cấu trúc tổng thể

## 1.1 VideoProject (root object gửi cho render toàn video)

| Field | Type | Required | Mô tả |
|---|---|---|---|
| `project_id` | string (uuid) | ✔ | |
| `schema_version` | string (semver) | ✔ | `"1.0.0"` |
| `format` | enum `vertical_1080x1920` \| `horizontal_1920x1080` | ✔ | |
| `platform_profile` | enum `generic` \| `tiktok` \| `facebook_reels` \| `youtube_shorts` \| `youtube_video` | ✔ | default `generic`; safe-area + validator output, không phải lựa chọn layout |
| `fps` | int | ✔ | Mặc định `30` |
| `scenes` | Scene[] | ✔ | ≥ 1, thứ tự = thứ tự phát |
| `bgm` | BgmSpec \| null | — | Nhạc nền toàn video |
| `watermark` | ImageRef \| null | — | Logo góc màn hình |

## 1.2 Scene

| Field | Type | Required | Constraint | Mô tả |
|---|---|---|---|---|
| `scene_id` | string (uuid) | ✔ | | Bất biến qua các lần sửa (dùng cho diff version) |
| `schema_version` | string | ✔ | semver | Cho phép scene lệch version trong giai đoạn migration |
| `scene_number` | int | ✔ | ≥ 1 | Thứ tự hiển thị |
| `duration_ms` | int | ✔ | 1000–30000 | Nếu có voice: hệ thống tự điều chỉnh ≥ độ dài audio + 300ms đệm |
| `layout` | enum | ✔ | xem §2 | Quyết định template component |
| `background` | Background | ✔ | | |
| `texts` | TextElement[] | ✔ | 0–5 phần tử | |
| `images` | ImageElement[] | ✔ | 0–3 phần tử | |
| `voice` | VoiceSpec \| null | — | | null = scene không lời |
| `subtitle` | SubtitleSpec | ✔ | | |
| `transition` | Transition | ✔ | | Transition **ra khỏi** scene này; được thực hiện ở bước assemble cuối |

**Scene cache key:** `sha256(canonical_json(scene) + template_version + format + platform_profile)` — canonical = sort keys, bỏ field `scene_number` (đổi thứ tự không phá cache). Cache video cuối là hash riêng của danh sách scene cache key theo thứ tự, transition giữa cảnh, BGM, format, `platform_profile` và template version.

---

# 2. Layout catalog (v1: 11 layout)

*(Mở rộng từ 5 → 11 theo yêu cầu PO 2026-07-11: "video Remotion có nhiều bố cục, không chỉ chữ với ảnh". Nhóm Cơ bản là phạm vi M1/story 2.2; nhóm Dữ liệu + Cấu trúc là story 2.6.)*

Tên class **PascalCase là canonical** toàn hệ (thống nhất với layout-engine.md §5 và wireframe — quyết định review 2026-07-11). `layout` trong Scene JSON là **kết quả Layout Classifier**, không phải lựa chọn của AI; user override qua `layout_override`.

**Nhóm Cơ bản (story 2.2 — M1):**

| `layout` class | Mô tả | Ràng buộc phần tử |
|---|---|---|
| `Hero` | Màn tiêu đề mở đầu/kết | 1–2 texts (`heading`, `caption`), 0–1 images (logo) |
| `TextFocus` | Chữ lớn giữa màn hình | 1–3 texts, 0 images |
| `MediaFull` | Ảnh full màn + text overlay | 0–2 texts, đúng 1 images |
| `MediaText` | Ảnh 55% / text 45% (dọc); trái-phải (ngang) | 1–3 texts, đúng 1 images |
| `Comparison` | 2 vế so sánh (ảnh/nhóm nội dung) + caption | 0–3 texts, 2 images hoặc 2 group |

**Nhóm Số liệu & dữ liệu (story 2.6):**

| `layout` class | Mô tả | Phần tử đặc thù (xem §3.6) |
|---|---|---|
| `BigNumber` | 1 con số hero (count-up) + nhãn + ngữ cảnh | đúng 1 `number`, 0–1 texts, 0–1 images (nền) |
| `Chart` | Biểu đồ cột animate từ dữ liệu inline (v1: bar) | đúng 1 `chart` (2–6 điểm), 0–2 texts |
| `VersusTable` | Bảng so sánh 2 cột (A vs B) — model/spec | đúng 1 `table` (2 cột, 2–4 hàng), 0–1 texts |

**Nhóm Nội dung có cấu trúc (story 2.6):**

| `layout` class | Mô tả | Phần tử đặc thù |
|---|---|---|
| `List` | 3–6 gạch đầu dòng stagger theo voice | đúng 1 `list` (3–6 items), 0–1 texts |
| `Quote` | Trích dẫn lớn + tác giả/nguồn | đúng 1 `quote_block`, 0–1 images (avatar/logo) |
| `Code` | Khối code highlight (video hướng dẫn) | đúng 1 `code`, 0–1 texts |

Template Remotion = **constraint preset (flexbox)** theo layout class + format — Scene JSON **không chứa toạ độ pixel**; 1 scene render được mọi format qua Responsive Solver. Việc chọn layout do **Layout Classifier** (rule table — layout-engine.md §5) quyết từ semantic profile, **không phải AI và không phải hardcode trong prompt**; user override qua editor (`layout_override`). Element các layout dữ liệu nhận thêm `constraints{}` optional — v1 ignore, chừa chỗ cho solver v2.

`platform_profile` không thay đổi layout class: nó chọn safe-area subtitle/watermark và giới hạn output. Compatibility v1: `tiktok`, `facebook_reels`, `youtube_shorts` chỉ dùng `vertical_1080x1920`; `youtube_video` chỉ dùng `horizontal_1920x1080`; `generic` dùng cả hai.

**Motion:** scene resolved chứa `motion_plan` (tracks enter_at_ms + sync_points — schema tại layout-engine.md §9.3) do **Motion Planner** điền theo two-pass (§9.4: pass 1 ước lượng lúc storyboard, pass 2 chốt bằng word-timestamps sau TTS). Field `animation` per-element trở thành **override của user** — mặc định null = theo planner.

---

# 3. Định nghĩa các type

## 3.1 Background

```json
{ "type": "color",    "color": "#0F172A" }
{ "type": "gradient", "from": "#0F172A", "to": "#1E3A8A", "angle": 135 }
{ "type": "image",    "asset": { "asset_id": "uuid", "url": null }, "overlay_opacity": 0.45 }
```

| Field | Type | Constraint |
|---|---|---|
| `type` | enum `color` \| `gradient` \| `image` | v2: `video` |
| `color`, `from`, `to` | string | hex `#RRGGBB` |
| `angle` | int | 0–360, default 180 |
| `asset` | AssetRef | xem §3.7 |
| `overlay_opacity` | float | 0–1, lớp phủ tối để chữ đọc được, default 0.4 |

## 3.2 TextElement

| Field | Type | Required | Constraint |
|---|---|---|---|
| `id` | string | ✔ | unique trong scene |
| `content` | string | ✔ | 1–200 ký tự; hỗ trợ `**bold**` và `\n` |
| `role` | enum `heading` \| `body` \| `caption` \| `stat` | ✔ | template map role → size/weight |
| `position` | enum `top` \| `center` \| `bottom` | ✔ | vị trí ngữ nghĩa trong vùng text của layout |
| `color` | string \| null | — | hex; null = màu theo theme template |
| `highlight_color` | string \| null | — | màu cho phần `**bold**` |
| `animation` | Animation | ✔ | xem §3.5 |

`stat` = số liệu nổi bật (ví dụ "92.5%") — template render cỡ rất lớn + đếm số (count-up) nếu content là số.

## 3.3 ImageElement

| Field | Type | Required | Constraint |
|---|---|---|---|
| `id` | string | ✔ | |
| `asset` | AssetRef | ✔ | |
| `fit` | enum `cover` \| `contain` | ✔ | default `cover` |
| `ken_burns` | bool | ✔ | default true với `MediaFull` |
| `caption` | string \| null | — | ≤ 80 ký tự |
| `animation` | Animation | ✔ | |

## 3.4 VoiceSpec & SubtitleSpec

```json
"voice": {
  "text": "Xin chào, hôm nay chúng ta nói về GPT-5.5...",
  "voice_id": "female_default",
  "speed": 1.0,
  "audio": { "path": "audio/{project}/{hash}.mp3", "duration_ms": 4820,
             "timestamps": [{ "word": "Xin", "start_ms": 0, "end_ms": 210 }, "..."] }
}
```

| Field | Type | Constraint |
|---|---|---|
| `text` | string | 1–500 ký tự, tiếng Việt |
| `voice_id` | string | logical id (`female_default`, `male_default`) — map sang engine voice qua env (FR-19) |
| `speed` | float | 0.8–1.3, default 1.0 |
| `audio` | object \| null | **Do Voice Worker điền** sau khi TTS; null = chưa produce. Frontend/AI không set field này. |

```json
"subtitle": { "enabled": true, "style": "line" }
```

| Field | Type | Constraint |
|---|---|---|
| `enabled` | bool | default true |
| `style` | enum `line` (1 dòng dưới) \| `karaoke` (v2) | |

Segment subtitle sinh tự động từ `audio.timestamps` (nhóm ≤ 42 ký tự/dòng) — không lưu trong Scene JSON.

## 3.5 Animation & Transition

```json
"animation": { "type": "fade_in", "delay_ms": 0, "duration_ms": 400 }
"transition": { "type": "fade", "duration_ms": 500 }
```

| | Enum v1 | Constraint |
|---|---|---|
| `animation.type` | `none`, `fade_in`, `slide_up`, `slide_left`, `zoom_in`, `pop` | `delay_ms` 0–5000; `duration_ms` 100–2000 |
| `transition.type` | `none`, `fade`, `slide_left`, `slide_up`, `zoom` | `duration_ms` 200–1500; transition scene cuối bị bỏ qua |

Transition không được render độc lập trong MP4 scene cache. Sau khi scene cache hoàn tất, assembler dùng `xfade` tương ứng và `acrossfade` audio giữa hai scene; `none` là hard cut. Duration video cuối = tổng duration scene trừ tổng thời lượng overlap transition. Nếu một preset Motion Planner không có mapping assembler, validator phải báo lỗi thay vì fallback im lặng.

## 3.6 (mới) Phần tử dữ liệu — dùng bởi nhóm layout Số liệu & Cấu trúc

Mỗi scene chứa **tối đa 1** phần tử loại này (theo ràng buộc layout §2). Mọi dữ liệu là inline trong Scene JSON — không fetch ngoài.

```json
"number":      { "value": "92.5", "suffix": "%", "label": "SWE-bench", "context": "vượt bản trước 11 điểm", "count_up": true }
"chart":       { "kind": "bar", "unit": "%", "points": [ {"label": "GPT-5", "value": 81.5}, {"label": "GPT-5.5", "value": 92.5, "highlight": true} ] }
"table":       { "col_a": "GPT-5.5", "col_b": "Gemini 3", "rows": [ {"label": "SWE-bench", "a": "92.5%", "b": "89.1%", "winner": "a"} ] }
"list":        { "items": [ {"text": "Cài đặt qua **pip**", "icon": "download"}, {"text": "Cấu hình API key"} ] }   // 3–5 items, stagger theo timestamps voice
"quote_block": { "text": "Đây là bước nhảy lớn nhất của agentic coding", "author": "Sam A.", "source": "X/Twitter", "source_id": "S3" }
"code":        { "content": "pip install langgraph\nfrom langgraph import ...", "language": "python", "highlight_lines": [1] }
```

Constraints: `chart.points` 2–6; `table.rows` 2–4, label ≤20 ký tự; `list.items` 3–5, text ≤60 ký tự; `code.content` ≤12 dòng × 48 ký tự (template auto-shrink theo BR 2.2); `quote_block.text` ≤140 ký tự, **bắt buộc `source_id`** nếu là phát ngôn thật (fact-check truy được).

## 3.7 AssetRef & BgmSpec

```json
"asset": { "asset_id": "uuid-in-assets-table", "url": null }
```

Quy tắc: ưu tiên `asset_id` (đã qua FR-20, có license). `url` trực tiếp chỉ cho phép domain allowlist (Pexels/Pixabay CDN) và sẽ được Asset Worker tải về, chuyển thành `asset_id` trước khi render — **Render Worker không bao giờ fetch URL ngoài**.

```json
"bgm": { "asset_id": "uuid", "volume": 0.12, "fade_out_ms": 2000 }
```

---

# 4. Ví dụ Scene hoàn chỉnh

```json
{
  "scene_id": "b3f1c9e2-4a5d-4c8e-9f21-7d3e8a1b2c4d",
  "schema_version": "1.0.0",
  "scene_number": 2,
  "duration_ms": 6000,
  "layout": "MediaText",
  "background": { "type": "gradient", "from": "#0F172A", "to": "#1E3A8A", "angle": 135 },
  "texts": [
    { "id": "t1", "content": "GPT-5.5 đạt **92.5%** trên SWE-bench",
      "role": "heading", "position": "top", "color": null, "highlight_color": "#38BDF8",
      "animation": { "type": "slide_up", "delay_ms": 200, "duration_ms": 400 } },
    { "id": "t2", "content": "Vượt phiên bản trước 11 điểm", "role": "body",
      "position": "bottom", "color": null, "highlight_color": null,
      "animation": { "type": "fade_in", "delay_ms": 600, "duration_ms": 400 } }
  ],
  "images": [
    { "id": "i1", "asset": { "asset_id": "9a8b7c6d-...", "url": null },
      "fit": "cover", "ken_burns": true, "caption": null,
      "animation": { "type": "fade_in", "delay_ms": 0, "duration_ms": 500 } }
  ],
  "voice": { "text": "GPT-5.5 vừa đạt 92,5 phần trăm trên SWE-bench, vượt phiên bản trước tới 11 điểm.",
             "voice_id": "female_default", "speed": 1.0, "audio": null },
  "subtitle": { "enabled": true, "style": "line" },
  "transition": { "type": "slide_left", "duration_ms": 500 }
}
```

---

# 5. Validation rules (ngoài JSON Schema)

Thực thi ở Pydantic validator, chạy khi: AI sinh scene, user save scene, trước khi enqueue render.

1. Số lượng texts/images khớp ràng buộc layout (§2). Vi phạm khi AI sinh → tự sửa (cắt bớt) + log warning; vi phạm khi user save → 422 kèm chi tiết.
2. `duration_ms` ≥ `voice.audio.duration_ms + 300` khi audio đã produce — validator tự nâng duration, không báo lỗi.
3. Tổng `animation.delay_ms + duration_ms` của mọi element ≤ `duration_ms` scene.
4. Màu hex hợp lệ; contrast text/background ≤ khuyến cáo → warning (không chặn).
5. `asset_id` phải tồn tại trong bảng `assets` và `license` không rỗng.
6. Tổng duration video ≤ `MAX_VIDEO_DURATION_MS` (env, default 180000).

---

# 6. Versioning & Migration

* **Minor/patch** (thêm field optional, thêm enum value): template mới đọc được JSON cũ — không cần migration. Ví dụ 1.1.0 thêm `subtitle.style="karaoke"`.
* **Major** (đổi/xoá field, đổi cấu trúc): bắt buộc kèm migration script `backend/app/schemas/migrations/scene_v{from}_to_v{to}.py` (pure function JSON→JSON, có test). Khi mở project cũ, backend tự migrate lên version mới nhất **tạo version mới** trong `step_versions` (không ghi đè).
* Template Remotion khai báo `supportedSchemaRange` (semver range) trong package; Render Worker từ chối job ngoài range với lỗi rõ ràng.
* JSON Schema export commit tại `packages/remotion-templates/schema/scene-{version}.json` — CI fail nếu Pydantic đổi mà file export chưa regenerate.

## Lộ trình v2 (định hướng, không cam kết cấu trúc)

`chart` kind `line`/`pie` (v1 chỉ `bar`), `video` element + background video, `lower_third`, `timeline` layout (mốc thời gian), karaoke subtitle, custom font per project, toạ độ tự do (free canvas) cho power user.
