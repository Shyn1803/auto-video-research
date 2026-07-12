# Task 2-5: Subtitle từ timestamps + burn vào video

**Points:** 3đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-2, 2-4 · **FR:** FR-19

## User story
As a viewer, I want phụ đề khớp chính xác lời đọc, so that xem không bật tiếng (đa số trên mobile) vẫn hiểu trọn nội dung.

## Why
70-80% video mạng xã hội được xem không tiếng — subtitle sync là điều kiện sống của định dạng, không phải tính năng phụ.

## Scope
**In:** **kiểm tra `@remotion/captions` trước** (Remotion Agent Skill `/remotion-captions` — dev-guide.md §2.1) — nếu khớp constraint §3.6 scene-json-schema thì dùng package chính chủ; nếu không khớp (ví dụ "không tách cụm số+đơn vị" tiếng Việt), giữ thuật toán tự viết: nhóm timestamps → segments (≤42 ký tự/dòng, cắt ranh giới từ, ưu tiên dấu câu); component subtitle style `line`; sinh segments lúc chuẩn bị props (không lưu trong Scene JSON — spec §3.4); unit test thuật toán.
**Out:** karaoke style (schema v2); vị trí/size subtitle tuỳ chỉnh (v1.1); file .srt xuất riêng (v1.1).

## Business Rules
1. Không tách cụm số+đơn vị ("92,5 phần trăm" nguyên vẹn 1 segment).
2. Segment hiển thị tối thiểu 700ms — ngắn hơn gộp với segment kế.
3. `subtitle.enabled=false` → không render, không chừa khoảng trống.
4. Segment vượt 42 ký tự do 1 từ quá dài → cho phép tràn mềm (không cắt giữa từ).

## Acceptance Criteria
1. **(happy)** Cảnh 6s → phụ đề đúng thời điểm (lệch ≤200ms), 1 dòng, không tràn safe-area.
2. **(biên/BR-1)** "92,5 phần trăm" nguyên cụm 1 segment.
3. **(biên/BR-2)** Từ đơn 300ms → gộp, không nháy.
4. **(BR-3)** Tắt subtitle → khung hình dùng trọn không gian.
5. **(unit)** Bộ test câu dài/số/từ ghép/dấu câu pass.

## Decisions already locked
- Subtitle bật mặc định mọi cảnh có voice (mobile-first).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + property test: mọi input, tổng text segments == text gốc (không mất chữ). PR states which Remotion Skill was invoked / why not used.
