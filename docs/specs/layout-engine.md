# Layout Engine Specification

**Version:** 1.0 · Kiến trúc theo mô hình Gamma-style layered engine (đề xuất PO 2026-07-11)
**Nguyên tắc trung tâm:** **AI không chọn layout.** AI chỉ sinh nội dung + ý đồ (Semantic Storyboard). Layout Engine — deterministic, test được — quyết định bố cục, kích thước, motion. Remotion chỉ render.

**Đi kèm:** [scene-json-schema.md](scene-json-schema.md) (contract đầu ra) · [prompts.md](prompts.md) §7 (contract đầu vào AI) · [ARCHITECTURE.md](../ARCHITECTURE.md)

---

# 1. Pipeline tầng

```
AI Prompt → Research → [AI] Semantic Storyboard        ← AI dừng ở đây
                              │
                              ▼
                      ① Scene Tree (normalize)
                              ▼
                      ② Semantic Analysis              ← hiểu "1 heading + 1 body + 1 image" ≠ "3 component"
                              ▼
                      ③ Layout Classifier              ← rule-based, deterministic
                              ▼
                      ④ Constraint Resolver            ← v1: preset flex theo class; v2: solver tổng quát
                              ▼
                      ⑤ Responsive Solver              ← 16:9 / 9:16 từ cùng tree, không gọi lại AI
                              ▼
                      ⑥ Theme Engine                   ← token hoá, độc lập layout
                              ▼
                      ⑦ Motion Engine                  ← preset theo loại component × theme
                              ▼
                      Scene JSON (resolved)  →  Remotion render
```

Tầng ①–⑦ là **pure function** (tree in → JSON out): unit-test 100%, không LLM, chạy <100ms/scene — nghĩa là đổi format/theme/motion **không tốn token, không sinh lại nội dung**.

---

# 2. Đầu vào — Semantic Storyboard (AI output)

AI (prompt `storyboard.generate`) chỉ sinh cấu trúc này. **Không có** layout, x/y, width, font, animation.

```json
{
  "scenes": [
    {
      "purpose": "hook | explain | evidence | compare | steps | quote | demo | conclusion | cta",
      "narration": "lời đọc của cảnh (trọn câu)",
      "components": [
        { "kind": "heading",     "text": "AI Agent", "emphasis": ["Agent"] },
        { "kind": "body",        "text": "Tương lai của tự động hoá" },
        { "kind": "media_intent","query_vi": "sơ đồ AI agent hoạt động", "media_hint": "diagram|photo|screenshot|logo" },
        { "kind": "stat",        "value": "92.5", "suffix": "%", "label": "SWE-bench", "source_id": "S1" },
        { "kind": "bullet",      "text": "Cài đặt qua pip" },
        { "kind": "quote",       "text": "…", "author": "…", "source_id": "S3" },
        { "kind": "chart_data",  "unit": "%", "points": [{"label": "GPT-5", "value": 81.5}], "source_id": "S1" },
        { "kind": "table_data",  "col_a": "GPT-5.5", "col_b": "Gemini 3", "rows": [...], "source_id": "S1" },
        { "kind": "code",        "content": "pip install …", "language": "bash" },
        { "kind": "group",       "label": "Con người", "children": [ …components… ] }
      ]
    }
  ]
}
```

10 `kind` cố định v1. `group` cho phép AI diễn đạt cấu trúc 2 cột (2 group = so sánh) mà vẫn không đụng layout. Số liệu (`stat`/`chart_data`/`table_data`) và `quote` **bắt buộc `source_id`** — truy được fact-check.

# 3. ① Scene Tree

Normalize storyboard thành cây Pydantic (validate kind, giới hạn: ≤8 components/scene, bullet 3–6, group ≤2, lồng group tối đa 1 cấp). Đây là **source of truth nội dung** — versioning (`step_versions.scene_set` lưu tree + resolved JSON), editor sửa trên tree.

# 4. ② Semantic Analysis

Đặc trưng hoá cây thành profile: `{n_heading, n_body, n_bullet, n_media, n_stat, has_chart, has_table, has_quote, has_code, n_group, dominant}` — `dominant` = component chiếm trọng tâm nội dung (stat đứng một mình ≠ stat kèm 3 đoạn body).

# 5. ③ Layout Classifier — bảng rule v1 (deterministic, thứ tự ưu tiên)

| # | Điều kiện (profile) | Layout class | Ghi chú |
|---|---|---|---|
| 1 | purpose=hook/conclusion + heading, ≤1 media | `Hero` | mở/kết |
| 2 | has_chart | `Chart` | |
| 3 | has_table hoặc 2 group có số liệu | `VersusTable` | |
| 4 | 2 group | `Comparison` | 2 cột |
| 5 | dominant=stat | `BigNumber` | |
| 6 | n_bullet ≥ 3 | `List` | stagger |
| 7 | has_quote | `Quote` | |
| 8 | has_code | `Code` | |
| 9 | n_media ≥ 3 | `Gallery` | **v1.1** — v1 hạ về MediaText + warning |
| 10 | n_media = 1 + text | `MediaText` | |
| 11 | n_media = 1, ≤1 text ngắn | `MediaFull` | |
| 12 | fallback | `TextFocus` | chữ lớn |

11 class v1 spec chi tiết ràng buộc phần tử tại scene-json-schema §2 — **tên class PascalCase là canonical toàn hệ** (schema/code/UI/backlog cùng dùng, đã thống nhất 2026-07-11). Rule table là **data trong config** (reviewable, sửa không deploy).

## 5.1 Post-pass chống lặp bố cục *(mới — video-taste.md §4.2, adapted từ taste-skill "section-layout-repetition ban")*

Chạy **sau** khi mọi cảnh trong video đã được classify (không phải per-cảnh) — mục đích chống rủi ro "mass-produced content" (SRS.md §12):

1. Không quá **2 cảnh liên tiếp** cùng layout class → cảnh thứ 3 trùng bị hạ xuống class runner-up (điểm rule gần nhất trong bảng §5) nếu semantic profile vẫn khớp; không khớp class nào khác → giữ nguyên + warning (nội dung thắng thẩm mỹ).
2. 1 class chiếm **>40% tổng số cảnh** (loại trừ `Hero`/`TextFocus` dùng cho hook/cta, tối đa 2 cảnh mỗi video) → cảnh có margin thấp nhất giữa class hiện tại và runner-up trong rule table bị chuyển sang runner-up.
3. Video ≥8 cảnh phải đạt **≥4 class khác nhau** — không đạt → warning hiển thị cho user (không tự ý đổi thêm, tránh vòng lặp).

Đây là **luật engine, không phải hướng dẫn AI** — Semantic Storyboard (prompt §7) không biết và không cần biết về đa dạng layout.

**Override:** user đổi layout trong editor = `layout_override` trên scene (gallery hiện có). Override thắng classifier; regenerate nội dung cùng cấu trúc semantic → giữ override; cấu trúc đổi loại → override reset + thông báo.

# 6. ④ Constraint Resolver

**v1 — preset theo class (flexbox):** mỗi class là một preset ràng buộc, KHÔNG toạ độ pixel:

```json
"Hero": {
  "direction": "column", "justify": "center", "align": "center",
  "padding": "8%", "gap": 32,
  "slots": [ {"for": "heading", "grow": 0}, {"for": "media", "grow": 1, "max_height": "45%"}, {"for": "body", "grow": 0} ]
}
```

Remotion component render preset bằng CSS flex (React — tự nhiên). Thêm class mới = thêm preset + component, không đụng engine.

**v2 — solver tổng quát (roadmap, sau release):** component tự khai constraints (`preferredWidth: 40%`, `aspectRatio: 16:9`, `align`) → engine giải (flexbox solver / cassowary) → layout là **kết quả giải ràng buộc, không phải chọn template**. Điều kiện kích hoạt v2: khi cần >~15 class hoặc nhu cầu variant/scene phức hợp mà preset không tả nổi. Schema v1 đã chừa chỗ: element nhận `constraints{}` optional (ignore ở v1).

# 7. ⑤ Responsive Solver

Cùng tree + class → resolve theo format, không AI:

| | 16:9 (1920×1080) | 9:16 (1080×1920) |
|---|---|---|
| Type scale | heading 72 / body 36 / stat 120 | heading 92 / body 44 / stat 150 |
| Comparison | 2 cột ngang | 2 khối dọc |
| MediaText | ảnh trái 45% – text phải | ảnh trên 55% – text dưới |
| Safe area | caption đáy 5% | đáy 12% (UI TikTok) |

Bảng scale/quy tắc per-class nằm trong preset (config).

# 8. ⑥ Theme Engine

Theme = token set độc lập hoàn toàn với layout — đổi theme không đổi tree/class/preset (đúng chuẩn Gamma, design-system §2). Mở rộng 2026-07-11 (video-taste.md §2–4.3): mỗi theme khai thêm:

```json
{
  "motion_intensity": 6,        // 1-10, video-taste.md §2 — scale duration/ease Motion Planner §9.1
  "visual_density": 4,          // 1-10 — số phần tử/cảnh, padding preset
  "accent_saturation_max": 0.8, // 1 accent color, giới hạn bão hoà — video-taste.md §4.3
  "radius_scale": "soft-16px"   // sharp | soft-16px | pill — khoá 1 giá trị/theme
}
```

Không tồn tại theme không khai dial (bắt buộc — tránh rơi về mô tả định tính "mạnh/nhẹ" thiếu số).

# 9. ⑦ Motion Planner *(nâng cấp 2026-07-11 từ "bảng preset tĩnh" thành bộ đạo diễn deterministic; số liệu hiệu chỉnh từ video-taste.md §3)*

**Đầu vào:** scene tree (kèm tín hiệu AI: `purpose`, `beat`, `emphasis`, `narration_anchor`) + **word timestamps từ TTS** + theme motion profile (dial `MOTION_INTENSITY`/`VISUAL_DENSITY` — video-taste.md §2).
**Đầu ra:** `MotionPlan` per scene. **AI không chọn animation** — chỉ khai tín hiệu ngữ nghĩa nằm sẵn trong nội dung nó viết.

## 9.1 Bảng preset kiểu chuyển động (WHAT — kind × theme, số liệu cụ thể)

Ease mặc định: `cubic-bezier(0.16, 1, 0.3, 1)`. Duration/stagger scale theo `MOTION_INTENSITY` của theme: 300ms (dial 1–3) · 450–600ms (dial 4–7, mặc định) · 600–800ms + overshoot (dial 8–10).

| Component | Preset mặc định (dial 4–7) | Dial 8–10 ("mạnh") |
|---|---|---|
| heading | slideUp 500ms, ease chuẩn | slideUp + overshoot 700ms / glitchIn |
| body/caption | fadeIn 450ms | fadeIn nhanh 350ms |
| media | kenBurns (MediaFull) / zoomIn 550ms | zoomIn nhanh 400ms |
| stat | countUp 600ms | countUp + spring pulse (`stiffness:100 damping:20`) |
| list | stagger — theo timestamps; fallback 90ms/item | stagger nhanh — fallback 60ms/item |
| chart | bar-grow lần lượt 500ms/bar | grow 350ms/bar + glow |
| quote | fadeIn 500ms + quote-mark scale | — |
| transition cảnh | 400–500ms theo cặp purpose §9.2 | — |

## 9.2 Quy tắc choreography (WHEN/HOW MUCH — phần mới)

1. **Narration-sync (quan trọng nhất) — "Motion must be motivated" (video-taste.md §4.1):** component có `narration_anchor` → `enter_at` = timestamp từ đầu tiên của anchor; stat count-up **kết thúc đúng lúc giọng đọc xong con số**; từ `emphasis`/bold → sync_point highlight (scale/màu) đúng word timestamp. Mọi track phải khai `reason` (`narration_sync|hierarchy|sequence`) — track không lý do bị validator (2.1) chặn ở chế độ strict.
2. **Thứ tự tự nhiên:** không anchor → vào theo thứ tự component, phân bổ theo nhịp câu (không chia đều máy móc).
3. **Beat profile:** `reveal` (mặc định — lần lượt), `contrast` (2 vế vào đối xứng, Comparison/VersusTable), `escalation` (stagger nhanh dần, List/Chart), `calm` (chỉ fade, explain dài).
4. **Purpose cường độ:** hook/cta = nhanh + mạnh (300ms, overshoot nhẹ); explain/evidence = vừa; conclusion = chậm ra.
5. **Attention budget:** tối đa 1 chuyển động lớn tại một thời điểm; không entrance mới trong 500ms cuối cảnh; media nền không giật khi text đang vào.
6. **Transition giữa cảnh** chọn theo cặp purpose (hook→explain: slide; …→compare: wipe đôi; …→conclusion: fade chậm) — bảng config.

## 9.3 MotionPlan schema (engine điền vào Scene JSON resolved)

```json
"motion_plan": {
  "tracks": [
    { "component_id": "t1", "preset": "slideUp", "reason": "sequence", "enter_at_ms": 0,
      "sync_points": [ { "at_ms": 1840, "effect": "highlight", "target": "92.5%" } ] },
    { "component_id": "n1", "preset": "countUp", "reason": "narration_sync", "enter_at_ms": 1400, "end_by_ms": 2600 }
  ],
  "transition_out": { "type": "slide_left", "duration_ms": 500 }
}
```

Remotion: mỗi track = `<Sequence from={ms→frames}>` + `Animated` wrapper; sync_points = interpolate mốc tuyệt đối.

## 9.4 Two-pass resolve (ràng buộc luồng quan trọng)

Timestamps thật chỉ có **sau TTS (node produce)** → engine resolve 2 lần, đều deterministic + không token:
- **Pass 1 (storyboard):** layout + MotionPlan ước lượng (ước tốc độ đọc) — đủ cho preview sớm trong editor.
- **Pass 2 (sau produce):** chốt MotionPlan bằng word timestamps thật; chỉ cập nhật `motion_plan` — layout không đổi. Cache key tính trên JSON cuối → cơ chế cache nguyên vẹn.

User override per-element vẫn được (field animation trong editor = override, mặc định "theo đạo diễn tự động").

# 10. Đầu ra — Scene JSON (resolved)

Scene JSON ([scene-json-schema.md](scene-json-schema.md)) giữ nguyên vai trò **contract render + cache** nhưng định vị lại: nó là **sản phẩm resolved của engine** (class + slots đã giải + theme ref + motion đã chọn), kèm `semantic_tree` gốc để editor sửa ở mức ý nghĩa. Cache key giữ nguyên cơ chế (hash resolved JSON).

# 11. Tầng hiện thực Remotion — base components (package `@app/remotion-templates`)

Theo kiến trúc engine, Remotion **không có 11 composition cứng** — chỉ có **1 SceneRenderer** + bộ primitive, preset là data:

```
packages/remotion-templates/src/
├── SceneRenderer.tsx        # composition DUY NHẤT: nhận Scene JSON resolved
│                            #  → tra preset theo layout class + format → render slots bằng flex
├── primitives/              # 1 component / component-kind (map 1-1 với §2)
│   ├── Heading.tsx  Body.tsx  Media.tsx  (ảnh/kenburns, nhận asset path cục bộ)
│   ├── Stat.tsx (countUp)  BulletList.tsx (stagger theo timestamps)
│   ├── ChartBar.tsx  VersusTable.tsx  Quote.tsx  Code.tsx
│   └── Subtitle.tsx  Watermark.tsx
├── motion/
│   ├── Animated.tsx         # wrapper: nhận motion preset ref → spring/interpolate tương ứng
│   └── presets.ts           # bảng §9 (kind × theme → animation), data
├── theme/
│   ├── ThemeProvider.tsx    # context token (màu/font/radius/mật độ motion)
│   └── themes/*.json        # 10.2 chỉ thêm file json ở đây
├── presets/
│   └── layouts/*.json       # constraint preset mỗi class × format (§6–7) — DATA, không code
└── schema.ts                # Zod (sinh từ Pydantic — không đổi)
```

Nguyên tắc tầng này:
1. **Thêm layout class mới = thêm 1 file preset json** (+ primitive mới nếu có kind mới) — SceneRenderer không đổi.
2. Primitive **không biết layout** — chỉ render nội dung + motion của chính nó trong slot được cấp.
3. `Animated` là đường duy nhất áp animation — primitive không tự viết spring (nhất quán + theme đổi được mật độ motion).
4. Player (2.3) và Render Worker (9.2) cùng import SceneRenderer — bất biến AR-4 giữ nguyên.
5. Đơn vị test: preset json validate bằng schema riêng; primitive có story/fixture; SceneRenderer golden-frame test theo class × format.

# 12. Mapping sang backlog

| Tầng | Story | Ghi chú |
|---|---|---|
| Semantic Storyboard (prompt) | 4.6 (sửa) | AI bỏ chọn layout |
| ①②③ Tree + Analysis + Classifier + **post-pass chống lặp (§5.1)** | 4.6 (sửa — vẫn deterministic mapper, nay có spec tầng rõ) | rule table = config |
| ④⑤ Preset resolver + responsive + **base components (§11)** | 2.2 (SceneRenderer + primitives cơ bản + 5 preset) + 2.6 (primitives dữ liệu + 6 preset) | không có composition cứng per-layout |
| ⑥ Theme **+ dial/lock (§8)** | 10.2 | dial bắt buộc mọi theme |
| ⑦ Motion Planner **(số liệu §9.1, `reason` bắt buộc)** | 2.6 (gộp — preset table) | |
| Solver tổng quát + Gallery/Timeline class | **v1.1 roadmap** | plan §7 |
| **Video Taste Layer** ([video-taste.md](video-taste.md)) | 4.6, 2.2, 2.6, 10.2 (nguồn số liệu + luật) | adapted từ taste-skill, không phải input AI |
