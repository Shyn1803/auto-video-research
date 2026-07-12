# Design System — AI Video Studio

**Version:** 1.0 · Dark-first · shadcn/ui + Tailwind · Tiếng Việt
Sinh ra từ audit design-critique (2026-07-10). Là nguồn chân lý cho token, component, pattern — [ux-design.md](ux-design.md) tham chiếu sang đây, không định nghĩa lại.

---

# 1. Audit Summary (wireframe v1)

**Score: 62/100** — ngôn ngữ trạng thái tốt, IA và states coverage yếu.

| Vấn đề | Mức | Xử lý trong v2 |
|---|---|---|
| IA trộn 3 tầng trong sidebar; điều hướng bước lặp 2 nơi | 🔴 | Pattern Navigation §4.1 |
| Không có running/empty/error state | 🔴 | Component RunningState §3.4 + quy tắc §3 "5 states bắt buộc" |
| ApproveBar không đồng nhất vị trí | 🔴 | Component ApproveBar §3.3 |
| Trạng thái chỉ bằng màu (chấm provider) | 🟡 | Quy tắc token §2.1 |
| Chữ 11–12px cho nội dung; touch target < 32px | 🟡 | Type scale §2.2, size chuẩn §2.4 |
| Version history tách rời ngữ cảnh | 🟡 | Component VersionSwitcher §3.5 |

---

# 2. Design Tokens

## 2.1 Màu

```css
--background:#0B1120;  --card:#111a2e;  --card-2:#16213a;  --border:#243250;
--foreground:#e2e8f0;  --muted-fg:#94a3b8;   /* nâng từ #8b9bb4 để đạt AA ở 13px */
--primary:#0EA5E9;     --primary-fg:#04141f;
/* Semantic trạng thái — BỘ DUY NHẤT cho verdict/status/render/provider/publish */
--status-pass:#22c55e;  --status-warn:#f59e0b;  --status-fail:#ef4444;
--status-run:#0EA5E9;   --status-idle:#64748b;
/* nền badge tương ứng */
--pass-bg:#052e16; --warn-bg:#3b2405; --fail-bg:#3f0d0d; --run-bg:#082f49; --idle-bg:#1e293b;
```

**Quy tắc bất biến:** trạng thái luôn hiển thị bằng **màu + icon + nhãn text** (✓ Đạt / ⚠ Cần xem / ✗ Lỗi / ● Đang chạy / ○ Chưa). Chấm màu trần bị cấm. Không hardcode hex trong component — chỉ dùng token.

## 2.2 Typography

Inter (UI), JetBrains Mono (số liệu/code/cost).

| Token | Size/LH | Dùng cho |
|---|---|---|
| `text-xs` | 12/16 | **chỉ** nhãn phụ, caption — không bao giờ chứa thông tin phải đọc để ra quyết định |
| `text-sm` | 13/18 | metadata, mô tả phụ (min cho nội dung) |
| `text-base` | 14/20 | body mặc định |
| `text-lg` | 16/24 | tiêu đề card |
| `text-xl` | 20/28 | tiêu đề màn |
| `text-stat` | 28/32 mono | số liệu dashboard |

## 2.3 Spacing / Radius / Motion

Spacing bội số 4 (4-8-12-16-24-32). Radius: control 8px, card 12px, badge full. Motion: 150ms ease-out (hover), 250ms (panel/modal), pulse 1.6s (attention) — tôn trọng `prefers-reduced-motion`.

## 2.4 Kích thước tương tác

Mọi element click được: **min-height 32px** (desktop tool chuẩn), icon-button 32×32 luôn có `aria-label` + tooltip. Focus ring 2px `--primary` offset 2px — bắt buộc mọi interactive element.

---

# 3. Components

Nền shadcn giữ nguyên API. Component domain dưới đây là hợp đồng bắt buộc. **Mỗi component/màn phải định nghĩa đủ 5 states: default · loading · empty · error · disabled** — PR thiếu state nào reviewer từ chối.

## 3.1 StatusBadge

| Prop | Type | Ghi chú |
|---|---|---|
| `kind` | `pass\|warn\|fail\|run\|idle` | map cứng token — không nhận màu tuỳ ý |
| `label` | string | bắt buộc (quy tắc màu+icon+text) |
| `pulse` | bool | chỉ cho `warn` cần hành động |

Icon tự theo kind: ✓ ⚠ ✗ ● ○. A11y: `role="status"`, screen reader đọc "Trạng thái: Đạt".
✅ Dùng cho mọi trạng thái domain. ❌ Không dùng Badge shadcn trần cho trạng thái.

## 3.2 PipelineStepper — **điều hướng duy nhất trong project**

**5 trạm** cố định: `Nghiên cứu → Nội dung → Phân cảnh → Hoàn thiện → Xuất bản` (quyết định PO 2026-07-11: gộp Dàn ý + Kịch bản thành trạm Nội dung — UI một màn 2 sub-step, backend giữ 2 version/2 gate). Fact Check là tab/badge trong Nghiên cứu; Timeline+Render gộp trong Hoàn thiện.

| State trạm | Visual | Hành vi |
|---|---|---|
| done | ✓ xanh lá | click = xem lại (readonly + nút "Sửa lại từ đây") |
| done-warning | ✓⚠ (viền vàng) | đã duyệt nhưng còn cảnh báo (số lệch, asset thiếu); tooltip liệt kê; click về đúng chỗ xử lý |
| current | outline primary | — |
| attention | ⚠ vàng pulse | việc của user đang chờ |
| running | ● xanh + % | click = xem running-state |
| locked | ○ xám | tooltip "Hoàn thành bước X trước" |
| stale | nền vàng nhạt | tooltip lý do stale |

A11y: `<nav aria-label="Tiến trình">`, `aria-current="step"`, mũi tên ←/→ di chuyển, Enter mở.

## 3.3 ApproveBar

Vị trí **cố định duy nhất**: sticky bottom-right của content area — mọi màn bước, kể cả Scenes (bỏ nút duyệt lơ lửng giữa cột). Cấu trúc: `[hành động phụ (ghost)] [hành động chính (primary)]`.

| State | Hành vi |
|---|---|
| enabled | primary + `Ctrl+Enter` |
| disabled | mờ 45% + **tooltip lý do bắt buộc** ("Còn 1 claim mâu thuẫn", "2/8 scene chưa duyệt") |
| loading | spinner trong nút, disable cả bar |

## 3.4 RunningState *(mới — pattern quan trọng nhất bị thiếu ở v1)*

Khối chuẩn hiển thị khi AI/render đang chạy — dùng chung mọi bước:

```
┌──────────────────────────────────────┐
│  ● Đang sinh Kịch bản…    (elapsed)  │
│  ▸ "Đang đọc arxiv.org (4/12)"       │  ← message thật từ SSE step.progress
│  ▓▓▓▓▓▓░░░░ 60%                      │
│  [Chạy ngầm]  [Huỷ]                  │
└──────────────────────────────────────┘
```

| Prop | Ghi chú |
|---|---|
| `runId` | subscribe SSE |
| `onCancel` | huỷ run (confirm) |
| allowBackground | user rời màn, stepper vẫn hiện ● % |

Error state của nó = banner đỏ + lỗi đã dịch nghĩa + `[Thử lại]` + chi tiết kỹ thuật collapse. Empty… không áp dụng. **Mọi nút "Duyệt" dẫn tới bước AI kế phải đi qua RunningState** — không nhảy màn trực tiếp.

## 3.5 VersionSwitcher *(mới)*

Dropdown `v3 ▾` cạnh tiêu đề mỗi bước: list version (thời gian, tác giả, badge stale) → xem / so sánh với hiện hành / khôi phục (confirm nêu hệ quả stale). Màn History tổng vẫn giữ (audit toàn cảnh) nhưng không còn là đường duy nhất.

## 3.6 SceneThumbnail + SceneProgressHeader *(bổ sung)*

Thumbnail: trạng thái ✓/⚠/✗(lỗi asset) + số. Header màn Scenes: **"Đã duyệt 6/8" + CTA "Sang Hoàn thiện ▸"** (disabled kèm lý do khi chưa đủ) — đóng vòng hở luồng v1.

## 3.7 ProjectDrawer *(mới — story 5.10)*

Drawer trượt phải, mở từ tên project ⓘ trên topbar (mọi màn workspace). 2 tab: **Thông tin** (tóm tắt, verdict, thời lượng/format/giọng/theme, **chi phí AI ước tính**, hoạt động gần đây) + **Cài đặt** (đổi tên/format/giọng/theme, Nhân bản, Lưu trữ). ESC/✕ đóng; focus-trap; không phải route (URL không đổi). Topbar còn có nút **▶ Xem bản mới nhất** (mở preview scene_set/video hiện hành từ bất kỳ trạm nào — 5.1 BR).

## 3.8 Các component giữ nguyên từ ux-design §5

SourceCard, ClaimRow (thêm: hover claim → highlight SourceCard liên quan), AssetPicker, TimelineBar, RenderProgress, ProviderMatrix (sửa: chấm → StatusBadge), CostChart.

---

# 4. Patterns

## 4.1 Navigation — IA 2 tầng (thay v1)

```
Tầng 1 — Sidebar global (mỏng, cố định):
  📁 Dự án   📊 Analytics   ⚙️ Quản trị (chỉ admin)   👤 User menu
Tầng 2 — Project workspace (chiếm toàn màn khi mở project):
  Topbar: ← Dự án | Tên project + StatusBadge + VersionSwitcher
  PipelineStepper (điều hướng duy nhất trong project)
  Content + ApproveBar
```

Quản trị = 1 route với tab ngang: Providers · API Keys · Prompts · Schedules · Queue · Chi phí. Creator không thấy mục Quản trị.

## 4.2 Dashboard — nhóm theo vòng đời

Thứ tự nhóm (nhóm rỗng ẩn): **📥 Chờ duyệt hôm nay** (Mode 1 READY + NEED_REVIEW, duyệt 1 click) → **⚡ Đang chạy** → **✏️ Đang làm dở** → **✓ Đã đăng (7 ngày)** → link "Xem tất cả (gồm lưu trữ)". Card: thumbnail frame cảnh 1 + tên + StatusBadge + "bước x/5 · tên trạm" + next-action (không mini-stepper). Filter chiều Mode (Của tôi / Tự động). Video Mode 1 đã đăng tự lưu trữ sau 30 ngày (cleanup job — số liệu analytics không mất).

## 4.3 Feedback

Toast góc phải dưới (info 5s; lỗi sticky + action). Failover provider = toast info "đã tự chuyển" — không cần user làm gì. Hết chain = error banner trong RunningState. Confirm dialog chỉ cho hành động mất dữ liệu, luôn nêu hệ quả cụ thể.

## 4.4 Forms

Autosave mọi editor (badge Đã lưu ✓/Đang lưu…); validate 422 → inline đúng field + scroll tới; không nút Save tay; không disable field khi loading — dùng skeleton.

---

# 5. Governance

- Thêm/đổi component: cập nhật file này **trong cùng PR** (docs là một phần của change — dev-guide §5).
- Token mới phải qua file này trước khi vào code; CI lint chặn hex hardcode trong `src/components`.
- Nghiệm thu story UI = so với [wireframe.html](wireframe.html) (bố cục) + file này (states/tokens/a11y).
