---
stepsCompleted: [init, discovery, core-experience, emotional-response, design-system,
                 visual-foundation, user-journeys, component-strategy, ux-patterns,
                 responsive-accessibility, complete]
inputDocuments: [docs/SRS.md, docs/specs/api-spec.md, docs/backlog/epics.md, docs/glossary.md]
---

# UX Design Specification — AI Content Research & Video Automation Platform

**Version:** 1.0 · **Ngày:** 2026-07-10 · Phạm vi wireframe: các màn Phase 1 (Epic 1–6)

---

# 1. Discovery — Người dùng & bối cảnh

| Persona | Bối cảnh sử dụng | Điều họ cần từ UI |
|---|---|---|
| **Content Creator** (chính) | Làm 1–5 video/ngày, thao tác lặp pipeline nhiều lần, không rành kỹ thuật/JSON | Luôn biết "đang ở bước nào, cần làm gì tiếp"; sửa nội dung trực quan; không bao giờ thấy JSON |
| **Admin** | Kiểm tra hệ thống vài lần/ngày | Nhìn 1 màn biết: provider nào sống, tiền tiêu bao nhiêu, gì đang lỗi |

**Nguyên tắc trải nghiệm cốt lõi (Core Experience):**

1. **Pipeline là xương sống UI** — mọi màn project đều có stepper cố định hiển thị 8 bước; bước hiện tại luôn rõ, bước cần user hành động có badge.
2. **Review-first**: mặc định của mọi bước AI là "xem → sửa → duyệt", nút Approve luôn ở vị trí cố định (góc phải dưới).
3. **Không chặn người dùng**: AI đang chạy vẫn xem được kết quả bước trước; sửa scene không chặn scene khác.
4. **Mọi hành động hoàn tác được** — versioning hiển thị như "lịch sử" thân thiện, không như git.

**Cảm xúc mục tiêu (Emotional Response):** tin cậy (thấy nguồn, thấy fact-check) + kiểm soát (duyệt từng bước) + tốc độ (preview tức thì). Tránh: cảm giác "hộp đen AI".

---

# 2. Information Architecture (v2 — sau design-critique 2026-07-10)

**IA 2 tầng** (chi tiết pattern: [design-system.md](design-system.md) §4.1):

```
Tầng 1 — Sidebar global:
/login
/projects            # Dashboard 2 khối: "📥 Chờ duyệt hôm nay" (Mode 1 + NEED_REVIEW) + "Dự án của tôi"
/analytics           # 3 tab: Tổng quan (KPI + trend + giữ chân + Insight tự động) · Theo video (bảng + drill-down giữ chân/nguồn view) · Theo chủ đề (nhóm + gợi ý chủ đề tiếp theo)
Nhóm QUẢN TRỊ (5 mục riêng, ẩn với Creator — tách sau feedback "1 menu gộp quá nhiều"):
/admin/van-hanh      # 🔌 Vận hành: ma trận Providers + chi phí (hôm nay/30 ngày theo task)
/admin/tu-dong-hoa   # 🤖 Tự động hoá: gate Mode 1 + thống kê PASS-đúng + lịch chạy
/admin/cau-hinh-ai   # 🧠 Cấu hình AI: 2 tab API Keys · Prompts
/admin/nguoi-dung    # 👥 Người dùng
/admin/hang-doi      # 📮 Hàng đợi & Worker (Phase NATS)

Tầng 2 — Project workspace  /projects/{id}
  Topbar: ← Dự án | tên ⓘ (mở ProjectDrawer: Thông tin/Cài đặt) + StatusBadge + VersionSwitcher + nút "▶ Xem bản mới nhất"
  PipelineStepper 5 trạm — ĐIỀU HƯỚNG DUY NHẤT trong project:
    Nghiên cứu (tab Kiểm chứng) → Nội dung (Dàn ý collapse + Kịch bản; 2 gate backend) → Phân cảnh → Hoàn thiện (timeline+render) → Xuất bản
  Content + ApproveBar (sticky bottom-right, mọi màn)
  Trạm done có cảnh báo hiển thị ✓⚠ (design-system §3.2)
  Điểm vào thay thế: "Có sẵn kịch bản" (modal Tạo dự án) → fact-check trên script → thẳng Phân cảnh (story 4.8)
```

Quy tắc rút từ critique v1:
- **Không lặp điều hướng**: các bước không xuất hiện trong sidebar; Fact Check là tab trong Nghiên cứu, không phải trạm riêng.
- **RunningState là màn first-class**: mọi nút Duyệt dẫn tới bước AI kế đi qua màn "Đang chạy…" (message SSE thật, nút Chạy ngầm/Huỷ) — không nhảy màn trực tiếp.
- **Version tại chỗ**: VersionSwitcher trên topbar từng bước; History tổng chỉ là view phụ.
- **Scenes đóng vòng**: header "Đã duyệt 6/8" + CTA "Sang Hoàn thiện ▸" trong ApproveBar (disable kèm lý do).

---

# 3. Visual Foundation — Design Tokens

Nền tảng: **shadcn/ui + Tailwind**, theme tối mặc định (công cụ sản xuất video — nền tối giúp preview nổi bật), có light mode.

```css
/* globals.css — CSS variables (shadcn convention) */
--background: 222 47% 7%;        /* #0B1120 nền chính */
--card:       222 41% 11%;       /* panel */
--primary:    199 89% 48%;       /* #0EA5E9 sky-500 — action chính */
--secondary:  222 30% 20%;
--muted-foreground: 215 16% 57%;
--destructive: 0 72% 51%;
/* Semantic trạng thái (dùng nhất quán toàn app) */
--status-pass:   142 71% 45%;    /* xanh lá — PASS/approved/done */
--status-warn:   38 92% 50%;     /* vàng — WARN/stale/need review */
--status-fail:   0 72% 51%;      /* đỏ — FAIL/failed */
--status-running: 199 89% 48%;   /* xanh dương — đang chạy (kèm spinner) */
```

Typography: Inter (UI) — hỗ trợ tiếng Việt tốt; JetBrains Mono (số liệu/cost). Scale: 12/14 (body)/16/20/24. Spacing: bội số 4px. Radius: 8px (card 12px). Icon: Lucide.

Quy tắc màu trạng thái: **duy nhất** bộ `--status-*` cho mọi trạng thái (verdict, project status, render job, provider health) — user học 1 lần dùng mọi nơi.

---

# 4. User Journeys & Wireframes (Phase 1)

## 4.1 Journey chính: Topic → Video (Mode 2)

```
Dashboard → [+ Tạo Project] → nhập topic → tự vào Research (AI chạy, progress)
→ review nguồn (pin/xoá) → Approve → Outline (sửa) → Approve → Script (sửa) → Approve
→ Scenes (AI sinh storyboard → editor) → duyệt từng scene → Timeline → [Tạo Video]
→ progress render → Publish: xem + Download
```

Quy tắc journey: sau Approve, bước kế tự chạy và UI tự chuyển — user không phải bấm "Run". Quay lại bước cũ bất kỳ lúc nào qua stepper (bước sau thành stale → cảnh báo vàng).

## 4.2 Dashboard `/projects`

```
┌────────────────────────────────────────────────────────────────┐
│ ☰ Projects                                    [🔍 Tìm] [+ Tạo] │
├────────────────────────────────────────────────────────────────┤
│ Filter: [Tất cả ▾] [Đang làm] [Chờ duyệt] [Hoàn thành]         │
├────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ GPT-5.5 có gì mới?                    ● NEED_REVIEW      │  │
│ │ topic: GPT-5.5 · sửa 2 giờ trước                          │  │
│ │ [Research ✓][Fact ⚠][Outline ][Script ][Scenes ][...]     │  │ ← mini-stepper
│ └──────────────────────────────────────────────────────────┘  │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ MCP là gì?                             ● RENDERING  63%   │  │
│ └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

Card = trạng thái + mini-stepper + hành động tiếp theo click được ("Cần duyệt Fact Check →"). Menu ⋮: Clone, Archive, History.

## 4.3 Layout project + Stepper (khung mọi màn con)

```
┌────────────────────────────────────────────────────────────────┐
│ Projects / GPT-5.5 có gì mới?                    ● NEED_REVIEW │
│ ①Research─②Fact─③Outline─④Script─⑤Scenes─⑥Timeline─⑦Video─⑧Pub │
│    ✓        ⚠!      ○        ○       ○        ○       ○     ○  │
├────────────────────────────────────────────────────────────────┤
│                    (nội dung bước hiện tại)                    │
│                                                                │
│                                  ┌──────────────────────────┐ │
│                                  │      [Chạy lại]  [Duyệt ▸]│ │ ← action bar cố định
└──────────────────────────────────└──────────────────────────┘─┘
```

Stepper: ✓ xong (xanh lá), ⚠ cần user (vàng, pulse), ● đang chạy (xanh dương + %), ○ chưa tới, màu vàng nhạt = stale. Click bước ✓ = xem lại/quay về.

## 4.4 Research — review nguồn + Fact Check

```
┌─ Research: 12 nguồn ──────────────┬─ Fact Check: ⚠ WARN ───────┐
│ [+ Thêm URL]                       │ ✓ PASS  GPT-5.5 đạt 92.5%  │
│ ┌───────────────────────────────┐ │         SWE-bench (2 nguồn)│
│ │📌 openai.com/blog  ★98  Tin cậy│ │ ⚠ WARN  Giá API $2/1M      │
│ │  "GPT-5.5 ra mắt..."  [tóm tắt]│ │         (1 nguồn) [nguồn→] │
│ │  2026-07-08        [📌][🚫][🗑]│ │ ✗ FAIL  Ngày phát hành      │
│ ├───────────────────────────────┤ │   nguồn A: 07-01           │
│ │ reddit.com/r/...  ★61          │ │   nguồn B: 07-05           │
│ │  partial ⚠ paywall             │ │   [Chọn đúng ▾][Bỏ claim]  │
│ └───────────────────────────────┘ │                            │
└───────────────────────────────────┴────────────────────────────┘
```

Claim FAIL bắt buộc xử lý (override chọn nguồn đúng, kèm lý do) trước khi nút Duyệt enable. Mỗi claim expand ra trích dẫn nguyên văn từng nguồn.

## 4.5 Outline / Script — editor văn bản

2 cột: trái = editor (outline: 7 section card có label Hook/Intro/...; script: textarea lớn + fields title/description/tags), phải = panel nguồn tham chiếu (readonly, claim PASS ghim trên đầu). Autosave badge "Đã lưu ✓". Nút [Sinh lại bằng AI] tạo version mới — không ghi đè bản đang sửa.

## 4.6 Scene Editor (màn phức tạp nhất)

```
┌─ Scenes (8) ────┬─ Scene 2/8 ──────────────┬─ Preview ────────┐
│ ┌────┐          │ Bố cục [⚙Tự động: MediaText▾]│ ┌────────────┐ │
│ │ #1 │ title    │ ─ Text ────────────────  │ │              │ │
│ │ ✓  │          │ Heading: [GPT-5.5 đạt    │ │   (Remotion  │ │
│ ├────┤          │   **92.5%** SWE-bench ]  │ │    Player    │ │
│ │ #2 │◄ đang sửa│ Vị trí [top▾] Màu [🎨]   │ │     9:16)    │ │
│ │ ⚠  │          │ Hiệu ứng [slide_up ▾]    │ │              │ │
│ ├────┤          │ ─ Ảnh ─────────────────  │ │              │ │
│ │ #3 │          │ [thumbnail] [Đổi ảnh]    │ └──────────────┘ │
│ │ ✓  │          │ ─ Giọng đọc ───────────  │ ▶ ⏸  0:02/0:06   │
│ └────┘          │ [textarea lời đọc]       │ [🔊 Nghe thử]    │
│ [+ Thêm scene]  │ Giọng [Nữ▾] Tốc độ [1.0] │                  │
│ (kéo thả sắp xếp)│                          │ [Duyệt scene ✓]  │
└─────────────────┴──────────────────────────┴──────────────────┘
```

- Form sinh từ JSON Schema (schema-driven) — thêm field vào schema là form tự có.
- Mọi thay đổi → Player cập nhật ngay; autosave 1s; lỗi validate hiện inline đúng field.
- Thumbnail sidebar: ✓ đã duyệt / ⚠ dirty chưa duyệt. Duyệt hết → nút sang Timeline enable.
- Đổi ảnh: modal 3 tab — Asset của project / Upload / Tìm stock (query editable, kết quả kèm license badge).

## 4.7 Timeline

```
┌────────────────────────────────────────────────────────────────┐
│ ▶ Preview toàn bộ            BGM: [Tech Upbeat ▾] vol ──●── 12%│
├────────────────────────────────────────────────────────────────┤
│ │#1 title 4s│▓#2 6s▓│#3 5s│#4 7s│#5 5s│#6 6s│#7 4s│#8 5s│ =42s│
│  ↔ kéo mép để đổi duration    giữa các block: [fade▾]          │
├────────────────────────────────────────────────────────────────┤
│                                          [◂ Scenes] [Tạo Video]│
└────────────────────────────────────────────────────────────────┘
```

Kéo mép block = duration (chặn dưới theo audio, tooltip giải thích). Click khớp nối = đổi transition. Tổng thời lượng realtime.

## 4.8 Render & Publish

Bấm [Tạo Video] → modal progress: danh sách scene với trạng thái (cache ⚡ / đang render ● / xong ✓ / lỗi ✗ + [Thử lại]), progress tổng. Xong → player video final + [⬇ Tải MP4] + khối metadata (title/description/tags từng cái có nút copy). Phase 2 thêm nút [Đăng YouTube].

## 4.9 Admin — Providers

```
┌ Capability ─ Provider (theo thứ tự chain) ─────────────────────┐
│ LLM strong   ●gemini(2 keys)  ●groq  ○openrouter: no key       │
│ LLM cheap    ●ollama qwen2.5:14b (GPU 8.2/12GB)                │
│ TTS          ●edge-tts  ○local: chưa cài  ⊘fpt: ALLOW_PAID=off │
│ Search       ●searxng  ●tavily(quota 412/1000)                 │
│ Asset        ●pexels  ○pixabay: no key                         │
│ Storage      ●minio                                            │
│              [Health check lại]     Hôm nay: $0.00 / cap $1.00 │
└────────────────────────────────────────────────────────────────┘
```

● xanh = active, ○ xám = inactive (kèm lý do), ⊘ = bị chặn bởi policy. Đây là màn "một cái nhìn biết hệ thống chạy bằng gì".

---

# 5. Component Strategy

Nền shadcn/ui (Button, Card, Dialog, Form, Tabs, Toast, Badge, Skeleton...). Component domain tự xây:

| Component | Dùng ở | Ghi chú |
|---|---|---|
| `PipelineStepper` | mọi màn project + mini trên card | trạng thái 5 kiểu, click điều hướng |
| `StatusBadge` | mọi nơi có trạng thái | map duy nhất status → màu `--status-*` |
| `ApproveBar` | mọi bước review | vị trí cố định; disable kèm lý do (tooltip) |
| `SourceCard` | research | pin/disable/xoá, badge trusted/partial |
| `ClaimRow` | fact check | expand evidence, override flow |
| `SceneThumbnail` | scene sidebar | render tĩnh frame giữa (Player thumbnail) |
| `SceneForm` | scene editor | schema-driven từ JSON Schema |
| `ScenePlayer` | editor + timeline | wrap Remotion Player, controls chuẩn |
| `AssetPicker` | đổi ảnh | 3 tab, license badge bắt buộc |
| `TimelineBar` | timeline | drag resize + transition picker |
| `RenderProgress` | render modal | consume SSE |
| `VersionHistory` | history + mỗi bước | list version, compare, restore + cảnh báo stale |
| `ProviderMatrix`, `CostChart` | admin | |

---

# 6. UX Patterns (quy ước toàn app)

* **Loading**: skeleton cho dữ liệu; bước AI chạy = progress message thật từ SSE ("Đang đọc arxiv.org… 4/12"), không spinner câm.
* **Lỗi provider**: toast vàng "Gemini quá tải, đã tự chuyển Groq" — thông báo, không bắt user làm gì. Lỗi hết chain: banner đỏ trong bước + [Thử lại] + link admin nếu là admin.
* **Empty state**: mỗi màn có hướng dẫn hành động đầu tiên (dashboard trống → "Tạo project đầu tiên"; nguồn trống → "Thêm URL hoặc chạy Research").
* **Confirm**: chỉ dialog xác nhận cho hành động mất dữ liệu thật (xoá scene, restore version gây stale) — nêu rõ hệ quả ("3 bước sau sẽ đánh dấu lỗi thời"). Còn lại tin vào undo/version.
* **Stale**: banner vàng đầu bước: "Bản này dựa trên Research v2 — bạn đã khôi phục v1. [Giữ nguyên] [Sinh lại từ v1]".
* **Autosave**: mọi editor; badge "Đã lưu ✓ / Đang lưu…"; không có nút Save thủ công.
* **Toast** góc phải dưới, 5s, tối đa 3 cùng lúc; lỗi có nút hành động.
* **Ngôn ngữ UI**: tiếng Việt toàn bộ; thuật ngữ theo glossary.md (verdict = "Đạt/Cần xem/Mâu thuẫn").

# 7. Responsive & Accessibility

* **Desktop-first** (công cụ sản xuất): tối ưu ≥ 1280px; 1024–1280 panel phải (preview) thu gọn thành tab; < 1024 chỉ hỗ trợ xem trạng thái + duyệt (read + approve), không hỗ trợ scene editor — hiện thông báo lịch sự.
* Keyboard: stepper và scene list điều hướng mũi tên; Approve = `Ctrl+Enter`; editor tab-order logic; mọi thao tác chuột có đường keyboard trừ kéo-thả (có nút thay thế ↑↓).
* ARIA: stepper = `nav` + `aria-current`; trạng thái không chỉ bằng màu — luôn kèm icon + text (✓/⚠/✗); focus ring rõ trên nền tối.
* Contrast: mọi cặp màu token đạt WCAG AA (kiểm bằng tooling trong CI frontend); font tối thiểu 14px.
* Video preview: có nút tắt tiếng; subtitle bật mặc định trong preview.

# 8. Mapping Design ↔ User Story

Wireframe tương tác: **[wireframe.html](wireframe.html)** — mở trực tiếp trong browser, điều hướng được giữa các màn. Wireframe HTML là **hợp đồng bố cục**: vị trí ApproveBar, Stepper, cấu trúc 3 cột Scene Editor cố định; chi tiết pixel dev tự quyết theo shadcn.

| Màn (wireframe.html v2) | Component chính ([design-system](design-system.md)) | User story ([backlog](../backlog/epics.md)) |
|---|---|---|
| Login | — | 1.2 |
| Dashboard nhóm vòng đời (hàng đợi + đang chạy/dở/đã đăng, thumbnail) | StatusBadge | 1.3, 7.2, 7.5 (duyệt nhanh) |
| Modal Tạo dự án (+ nhánh "Có sẵn kịch bản") | — | 1.3, 4.8 |
| ProjectDrawer (Thông tin/Cài đặt, chi phí AI) | ProjectDrawer §3.7 | 5.10 |
| Project workspace (topbar + stepper 6 trạm) | PipelineStepper §3.2, VersionSwitcher §3.5 | 5.1 (khung), 4.1 (trạng thái run), 1.5 (version tại chỗ) |
| RunningState + error state | RunningState §3.4 | 4.1 (SSE/interrupt), 1.6, 3.2 (error hết chain) |
| Nghiên cứu (tab Nguồn / Kiểm chứng) | SourceCard, ClaimRow §3.7 | 5.6 (UI), 4.3 + 4.4 (API/data) |
| Nội dung (Dàn ý collapse + Kịch bản) | ApproveBar §3.3 | 5.7 (UI), 4.5 (API/data) |
| Phân cảnh (3 cột + progress header + gallery 11 bố cục) | SceneThumbnail §3.6, AssetPicker | 5.1–5.4, 2.3, 2.6 (layout mở rộng) |
| Hoàn thiện (timeline + render gộp) | TimelineBar, RenderProgress | 5.5, 6.2 |
| Xuất bản | StatusBadge trạng thái nền tảng | 6.3, 8.1, 8.3, 8.4, 10.1, 10.3 |
| Tạo dự án (modal) | — | 1.3 |
| Xem lại bước ✓ (readonly + "Sửa lại từ đây") | PipelineStepper done-state | 5.1 (BR-1), 1.5 |
| So sánh phiên bản | VersionSwitcher §3.5 | 5.9 |
| Analytics — Tổng quan (KPI/trend/giữ chân/Insight) | CostChart pattern | 8.6, 8.7 (insight) |
| Analytics — Theo video (drill-down) | — | 8.6, 8.7 |
| Analytics — Theo chủ đề (nhóm + gợi ý) | — | 8.7 |
| Quản trị › Vận hành (Providers + chi phí) | ProviderMatrix | 3.4 (hiển thị), 3.5 |
| Quản trị › Tự động hoá (gate + lịch chạy) | — | 7.1, 7.3 |
| Quản trị › Cấu hình AI (Keys/Prompts) | — | 3.4, 4.2, 8.2 |
| Quản trị › Người dùng | — | 1.7 |
| Quản trị › Hàng đợi & Worker | — | 9.4 |

Quy tắc nghiệm thu story UI: so màn thật với màn tương ứng trong wireframe.html — đúng bố cục khối và luồng thao tác là đạt; khác biệt cố ý phải ghi trong PR.

# 9. Bàn giao & phạm vi

* Component list §5 là danh sách xây dựng — mỗi component gắn story đầu tiên cần nó.
* Hi-fi mockup (Figma) không bắt buộc; wireframe.html là nguồn tham chiếu bố cục chính thức cho đến khi UI thật thay thế.
