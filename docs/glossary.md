# Glossary & Domain Rules

**Version:** 1.0 · Từ vựng thống nhất giữa tài liệu, code, UI. Code dùng đúng tên tiếng Anh trong bảng; UI hiển thị tiếng Việt.

| Thuật ngữ (code) | Tiếng Việt (UI) | Định nghĩa |
|---|---|---|
| **project** | dự án | Một video từ topic → publish; đơn vị sở hữu, versioning, state |
| **mode** `interactive` / `daily_news` | chế độ tương tác / tin tức hàng ngày | Mode 2 / Mode 1 trong SRS |
| **step** | bước | 1 trong: research, outline, script, storyboard, scene_set, produce, render, publish |
| **run** | lượt chạy | Một lần thực thi 1 step (hoặc pipeline) — có `run_id` = correlation_id |
| **step version** | phiên bản | Snapshot content 1 step; version mới nhất không-stale = **current** (hiện hành) |
| **parent_version** | — | Version của step trước mà version này sinh từ; cơ sở cảnh báo stale |
| **stale** | lỗi thời | Version sinh từ dữ liệu upstream đã bị restore/đổi — vẫn dùng được, có cảnh báo |
| **source** | nguồn | 1 bài viết/paper/repo thu thập được; có provider, trusted, pinned, disabled |
| **trusted source** | nguồn tin cậy | Domain thuộc allowlist hệ thống (blog chính thức, arXiv…) — trọng số fact-check cao hơn |
| **partial_content** | nội dung một phần | Source chỉ lấy được title+abstract (paywall) — giảm giá trị làm bằng chứng |
| **claim** | luận điểm | Một khẳng định kiểm chứng được (tên model, số benchmark, ngày…) trích từ nội dung |
| **verdict** `PASS/WARN/FAIL` | đạt / cần xem / mâu thuẫn | Kết quả kiểm chứng 1 claim; verdict tổng project = FAIL > WARN > PASS |
| **gate** | cổng duyệt | Điểm pipeline dừng chờ điều kiện (human approve hoặc verdict) |
| **scene** | phân cảnh | Đơn vị độc lập nhỏ nhất: preview, cache, render riêng; định danh bởi `scene_id` bất biến |
| **Scene JSON** | — | Contract trung tâm (specs/scene-json-schema.md); input duy nhất của Remotion |
| **scene_set** | bộ phân cảnh | Toàn bộ scene của 1 storyboard version — 1 step version loại riêng |
| **layout class** | bố cục | 1 trong 11 class v1 (Hero, TextFocus, MediaFull, MediaText, Comparison, BigNumber, Chart, VersusTable, List, Quote, Code) — **do Layout Classifier chọn, không phải AI**; PascalCase là tên canonical |
| **semantic storyboard / scene tree** | kịch bản ngữ nghĩa | Đầu ra của AI: nội dung + ý đồ (purpose, components theo kind) — không có layout/vị trí/font/animation |
| **classifier** | bộ phân loại bố cục | Rule table deterministic (config): semantic profile → layout class (layout-engine.md §5) |
| **constraint preset** | preset ràng buộc | Định nghĩa bố cục của 1 class dạng flex data (slots/gap/padding) — không toạ độ pixel |
| **layout_override** | ghi đè bố cục | User chọn tay thay classifier; giữ khi regenerate cùng loại nội dung, reset khi đổi bản chất |
| **motion preset** | preset chuyển động | Animation theo component-kind × theme (Animated wrapper) — không cấu hình từng element |
| **dirty scene** | phân cảnh đã sửa | Scene có content_hash đổi từ lần render gần nhất → cần render lại |
| **cache_key** | — | `sha256(canonical_scene_json + template_version + format)` — trùng = dùng lại MP4 cũ |
| **produce** | sản xuất媒 liệu | Bước sinh TTS audio + resolve asset cho mọi scene (trước render) |
| **render** `scene` / `merge` | dựng | Render 1 scene ra MP4 / ghép các scene + audio thành video cuối |
| **format** | định dạng | `vertical_1080x1920` (9:16) hoặc `horizontal_1920x1080` (16:9) |
| **asset** | tài nguyên | Ảnh/video/audio có license đã lưu MinIO; **bắt buộc** có license, không rõ → từ chối |
| **provider** | nhà cung cấp | Một nguồn năng lực bên ngoài (gemini, edge_tts, pexels…) sau adapter |
| **capability** | năng lực | Nhóm chức năng có nhiều provider: LLM, TTS, search, imagegen, asset, storage, publish |
| **chain** | chuỗi ưu tiên | Thứ tự provider cho 1 capability (env `*_CHAIN`); lỗi → failover sang kế tiếp |
| **tier** `cheap/strong/embedding` | — | Độ khó task LLM → quyết định chain nào |
| **failover** | chuyển dự phòng | Tự động chuyển provider kế tiếp khi lỗi/hết quota — phát event `provider.failover` |
| **exhausted** | hết hạn mức | API key hết quota; tự re-activate sau `exhausted_until` |
| **cost cap** | trần chi phí | `DAILY_COST_CAP` — vượt → pause toàn pipeline |
| **publish** | xuất bản | 1 lần đưa video lên 1 nền tảng (hoặc download); có external_id/url |
| **AI disclosure** | khai báo AI | Cờ "nội dung tạo bởi AI" bật khi publish — mặc định bật, không nên tắt |
| **DLQ** | hàng đợi lỗi | Message xử lý fail > max_deliver lần — chờ Admin xem và replay |
| **correlation_id** | — | ID xuyên suốt 1 run qua mọi event/log — dùng để trace |

## Domain rules cần nhớ (hay bị làm sai)

1. **Không bao giờ ghi đè version** — mọi chỉnh sửa tạo version mới; restore cũng tạo trạng thái mới, không xoá.
2. **Scene `scene_id` bất biến** — đổi thứ tự chỉ đổi `scene_number`; diff/cache đều bám `scene_id`/`content_hash`.
3. **AI không sinh Scene JSON và không chọn layout** — AI chỉ sinh Semantic Storyboard (nội dung + ý đồ); Layout Engine deterministic (Tree → Analysis → Classifier → Constraint/Theme/Motion) quyết bố cục (specs/layout-engine.md). Field layout trong prompt output = parse fail.
4. **Render Worker không fetch URL ngoài** — mọi media phải là asset đã resolve (có license) trong MinIO.
5. **Adapter không đọc env, không ghi usage** — đó là việc của config layer và router.
6. **Verdict FAIL không chặn vĩnh viễn** — human override được (có lý do, có audit).
