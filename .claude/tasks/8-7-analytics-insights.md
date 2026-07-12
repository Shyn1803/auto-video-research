# Task 8-7: Analytics Insights — giữ chân, chủ đề, gợi ý hành động

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-5 (retention mở rộng), 8-6 (khung màn), 7-1 (apply schedule) · **FR:** FR-13

## User story
As a Content Creator, I want hệ thống tự rút ra insight từ số liệu và gợi ý hành động, so that tôi ra quyết định nội dung tiếp theo mà không phải tự làm phân tích trên bảng số thô.

## Why
Feedback PO trực tiếp: "analytics chưa thực sự thể hiện được sự phân tích" — 8-6 là *hiển thị*, task này là *phân tích*. Insight là **rule-based trên số liệu thật** (không LLM đoán mò) — mỗi insight phải trích được số + cỡ mẫu.

## Scope
**In:**
- **Giữ chân (Tổng quan):** đường giữ chân trung bình kênh (0/15/30/45s) từ YouTube retention; callout điểm rơi mạnh nhất.
- **Drill-down video:** giữ chân theo giây + map điểm rơi sang ranh giới cảnh (join timeline scene) — "rơi 15% tại cảnh #6"; nguồn view; so với TB kênh (badge ✓/✗ ±%).
- **Theo chủ đề:** gắn `topic_group` cho project (AI phân loại lúc tạo, sửa được); bảng nhóm; gợi ý tỉ trọng chủ đề + nút "Áp dụng vào cấu hình Mode 1".
- **Insight tự động (rule-based):** ~5 rule khởi điểm: so nhóm chủ đề (xem hết), so độ dài (≤50s vs >70s), giờ đăng vs view 48h, cảnh báo CTR giảm so TB, cỡ mẫu kèm mọi insight.
**Out:** insight bằng LLM (v1.1); A/B thumbnail/title (v1.1); demographics (v1.1); nền tảng ngoài YouTube.

## Business Rules
1. Insight chỉ hiện khi đủ cỡ mẫu (mặc định ≥5 video/nhóm) — thiếu → "chưa đủ dữ liệu (3/5 video)".
2. Mọi insight kèm số gốc + cỡ mẫu ("54% vs 41%, 7 vs 5 video").
3. `topic_group` do AI gán khi tạo project (tier cheap, danh sách config cố định); user sửa được; đổi nhóm → số liệu tính lại.
4. "Áp dụng vào Mode 1" chỉ điều chỉnh trọng số ưu tiên chủ đề trong schedules.config, có confirm + audit.
5. Map điểm-rơi→cảnh dùng retention buckets của YouTube (độ phân giải hạn chế) — hiển thị "≈ cảnh #N" (xấp xỉ), tooltip giải thích.

## Acceptance Criteria
1. **(happy)** Seed 14 video 3 nhóm chủ đề đủ mẫu → tab Chủ đề bảng đúng số; Insight ①② hiện đúng công thức kèm cỡ mẫu.
2. **(biên/BR-1)** Nhóm 3 video → insight thay bằng "chưa đủ dữ liệu (3/5)".
3. **(biên/BR-3)** Đổi topic_group 1 video → bảng nhóm tính lại ngay; audit ghi.
4. **(biên/BR-5)** Drill-down video → điểm rơi map "≈ cảnh #N" khớp timeline scene; tooltip xấp xỉ hiện.
5. **(BR-4)** "Áp dụng vào Mode 1" → confirm nêu trọng số cũ→mới → schedules.config đổi + audit.
6. **(quyền)** Creator xem insight; chỉ admin bấm Áp dụng (🅐).

## Data & API
Bảng: `projects.topic_group` (cột mới). Endpoints: `GET /analytics/insights?from&to`, `GET /analytics/topics`, `POST /analytics/apply-topic-weights` 🅐 (mới) → cập nhật api-spec §8 + database-schema. Contract change: **có**.

## Decisions already locked
- ⏳ Insight rule-based v1, không LLM (giải thích được, không bịa).
- ⏳ Danh sách topic_group: công-cụ/hướng-dẫn · tin-model · nghiên-cứu/paper · khác. Ngưỡng cỡ mẫu 5 video/nhóm.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + seed analytics 14 video × 30 ngày × retention là fixture lớn (generator, không tay); mỗi rule 1 unit test công thức + 1 test BR-1 thiếu mẫu.
