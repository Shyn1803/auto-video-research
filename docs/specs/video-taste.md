# Video Taste Layer — nguyên tắc "gu thẩm mỹ" cho Layout Engine

**Version:** 1.0 · Chuyển thể có chọn lọc từ [taste-skill](https://github.com/Leonxlnx/taste-skill) (skill "chống AI-slop" cho landing page web) sang bối cảnh video timeline (Remotion).
**Vai trò:** taste-skill là quy tắc cho DOM/scroll/CSS — **không dùng nguyên**. Tài liệu này lọc phần nguyên tắc thẩm mỹ chuyển thể được, bỏ phần đặc thù web, và biến thành **luật engine** (không phải hướng dẫn AI) — nhất quán với nguyên tắc "AI không quyết định bố cục/chuyển động".

---

# 1. Những gì KHÔNG áp dụng (loại rõ để không ai mang nhầm vào sau này)

| taste-skill pattern | Vì sao không dùng cho video |
|---|---|
| GSAP ScrollTrigger, pin, horizontal-scroll-hijack, sticky-stack | Video không có scroll/viewport — timeline tuyến tính theo frame |
| `backdrop-filter`, `prefers-reduced-transparency`, Tailwind breakpoints `sm/md/lg` | Đặc thù responsive-web; video có đúng 2 format cố định (§7 layout-engine), không breakpoint |
| Dark/light mode toggle, `prefers-color-scheme` | Video xuất ra là file cố định, không có "chế độ" runtime |
| SEO, form UX, nav/menu patterns, redesign protocol | Không tồn tại trong domain video |
| Web WCAG (focus ring, keyboard nav trên trang) | Video vẫn cần contrast/subtitle-readability (giữ lại — xem §4) nhưng không cần phần tương tác |

# 2. Ba Dial — chuyển thành thuộc tính Theme (không phải AI chọn)

taste-skill dùng 3 dial 1–10 gate mọi quyết định layout/motion/density. Video chỉ cần **2 dial** (không có "symmetry vs asymmetry" vì layout đã cố định bởi Classifier — DESIGN_VARIANCE không áp dụng):

| Dial | 1–3 | 4–7 | 8–10 |
|---|---|---|---|
| **MOTION_INTENSITY** | Tĩnh: fade/slide đơn giản, không stagger nhanh | Chuẩn: bảng preset §9.1 layout-engine mặc định | Mạnh: overshoot, glitch, pulse liên tục |
| **VISUAL_DENSITY** | Thoáng: 1 phần tử chính/cảnh, padding lớn | Chuẩn: layout hiện tại (2–5 phần tử) | Dày: nhiều số liệu/bullet, `font-mono` cho số |

**Theme mapping khởi điểm** (thay cho mô tả định tính cũ):

| Theme | MOTION_INTENSITY | VISUAL_DENSITY |
|---|---|---|
| Dark mặc định (tin tức công nghệ) | 6 | 4 |
| Sáng / tối giản (10.2) | 4 | 3 |
| Gradient động / Cyberpunk (10.2) | 8 | 4 |

Dial là **thuộc tính theme trong config**, resolve tại tầng Motion Planner (layout-engine §9) — không phải input AI, không phải lựa chọn user per-scene (chỉ chọn theme).

# 3. Số liệu motion cụ thể (lấp khoảng trống §9.1 cũ)

Nguồn: taste-skill Section 4/5/7 (đã hiệu chỉnh nhịp độ web→video — video chậm hơn vì có giọng đọc dẫn nhịp, không phải scroll người dùng điều khiển).

| Tham số | Giá trị | Dùng khi |
|---|---|---|
| Ease "vào" mặc định | `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-expo, "premium") | heading/body/media entrance |
| Spring (nhấn mạnh) | `stiffness: 100, damping: 20` | stat pulse, sync_point highlight |
| Duration entrance | 450–600ms (MOTION_INTENSITY 4–7); 300ms (1–3); 600–800ms + overshoot (8–10) | mọi primitive, scale theo dial |
| Stagger fallback (không có anchor/timestamps) | 90ms/item | List, bullet không voice-sync |
| Exit/transition cảnh | 400–500ms | theo cặp purpose (§9.2 layout-engine) |

Áp dụng: `motion/presets.ts` (layout-engine §11) đọc dial của theme → chọn duration/ease trong khoảng trên; **không hardcode 1 giá trị cứng cho mọi theme** như bản §9.1 cũ.

# 4. Nguyên tắc "taste" chuyển thành luật engine (không phải hướng dẫn AI)

## 4.1 "Motion must be motivated" — đã là triết lý cốt lõi, nay đặt tên chính thức

> Trước khi thêm bất kỳ track chuyển động nào: nó truyền đạt gì? Hợp lệ: đồng bộ giọng đọc (narration-sync), phân cấp (thứ gì quan trọng hơn), kể chuyện theo trình tự, phản hồi trạng thái. Không hợp lệ: "cho đẹp".

Thực thi: mọi track trong `MotionPlan` phải có `reason` (`narration_sync | hierarchy | sequence`) — validator (2.1) chặn track không lý do khi `strict`.

## 4.2 Chống lặp bố cục (sửa lỗi kiến trúc đã phát hiện)

taste-skill: *"Section-layout-repetition ban — 1 layout family dùng tối đa 1 lần/trang; 3 cảnh zigzag liên tiếp = Pre-Flight Fail."*

**Vị trí đúng:** quy tắc này thuộc về **Layout Classifier** (layout-engine §5) — deterministic, chạy sau khi mọi cảnh đã phân loại. Đây KHÔNG phải hướng dẫn cho AI (bản prompts.md §7 hiện tại đã đúng — không hề nhắc tới layout/diversity, đúng nguyên tắc "AI không quyết layout"). Rà lại phát hiện quy tắc chống lặp **chưa tồn tại ở bất kỳ tầng nào** của engine trước bản này — bổ sung formal ở đây để tránh drift trong tương lai (dev/PO sau này bị cám dỗ nhét lại vào prompt vì "dễ hơn").

**Rule mới — Classifier §5, chạy sau khi mọi cảnh đã phân loại (post-pass):**
- Không quá 2 cảnh liên tiếp cùng layout class.
- Class xuất hiện >40% tổng số cảnh (trừ `Hero`/`TextFocus` dùng cho hook/cta) → cảnh có điểm rule gần nhau nhất bị đẩy sang class runner-up trong rule table.
- Video ≥8 cảnh phải dùng ≥4 class khác nhau (áp lực đa dạng — đối phó rủi ro "mass-produced content" đã ghi SRS.md §12).

## 4.3 Color/Shape consistency lock → Theme Engine

- **1 accent color/theme**, saturation < 80% mặc định — áp cho `highlight_color`, chart `highlight` point, winner badge.
- **1 bộ radius/theme** (all-sharp / all-soft 12–16px / all-pill) — không trộn trong cùng video.
- Theme token schema (10.2) thêm `accent_saturation_max`, `radius_scale` bên cạnh dial §2.

## 4.4 Kỷ luật nội dung (đối chiếu — phần lớn ta đã có, siết thêm 2 điểm)

| taste-skill | Trạng thái ở ta |
|---|---|
| Số liệu giả-chính-xác bị cấm | **Đã mạnh hơn**: mọi `stat/chart_data/table_data` bắt buộc `source_id` từ fact-check (scene-json-schema §3.6) |
| Headline ngắn, không tràn | Có (2.2 BR-2 auto-shrink) — bổ sung: ưu tiên **giảm cỡ chữ trước, không giảm nội dung** (khớp "font-scale error, never copy-length error") |
| 1 tông giọng/trang | Bổ sung BR script (4.5): giữ 1 văn phong xuyên suốt (đã ngầm định, nay ghi rõ) |
| Tên/số liệu không có vẻ AI-bịa | Trùng với nguyên tắc chống hallucination cốt lõi của cả hệ thống (SRS §10) |

## 4.5 Contrast & readability (phần a11y transferable)

- Subtitle/text-overlay luôn đạt contrast tối thiểu tương đương WCAG AA trên nền động (ken-burns/gradient) — validator (2.1) kiểm tại thời điểm render (lấy màu trung bình vùng nền).
- Không dùng chuyển động làm phương tiện truyền tải thông tin duy nhất (số liệu quan trọng phải đọc được ở khung hình tĩnh bất kỳ, không chỉ lúc animate).

# 5. Vocabulary tham chiếu (đổi tên cho đúng domain video)

taste-skill có "Reference Vocabulary" (tên pattern để giao tiếp). Bản video tương đương — đã là 11 layout class (scene-json-schema §2) + motion preset (§9.1) — không cần thêm; tránh phình thuật ngữ khi domain đã gọn hơn web.

# 6. Thay đổi cụ thể trong hệ thống do tài liệu này kéo theo

| File | Thay đổi |
|---|---|
| [prompts.md](prompts.md) §7 | Không đổi — xác nhận đã đúng (không có hướng dẫn layout cho AI) |
| [layout-engine.md](layout-engine.md) §5 | **Bổ sung mới** post-pass chống lặp (§4.2 trên) — quy tắc chưa từng tồn tại trước bản này |
| [layout-engine.md](layout-engine.md) §9 | Số liệu motion cụ thể (§3 trên) thay mô tả định tính; `MotionPlan.tracks[].reason` bắt buộc |
| design-system.md | Theme token thêm dial + accent/radius lock |
| Story 4.6 | +BR: post-pass chống lặp, `reason` bắt buộc trên track |
| Story 2.2/2.6 | Dùng bảng số §3 làm giá trị cụ thể cho motion preset |
