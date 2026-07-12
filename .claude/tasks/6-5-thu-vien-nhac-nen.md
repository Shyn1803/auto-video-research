# Task 6-5: Thư viện nhạc nền có giấy phép

**Points:** 2đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 5-5, FR-20 infra · **FR:** FR-10, FR-20

## User story
As a Content Creator, I want chọn nhạc nền từ thư viện có sẵn giấy phép, so that video có nhạc hợp không khí mà không bao giờ lo gậy bản quyền.

## Why
Gap: Timeline có BGM picker nhưng không ai nạp nhạc. Bản quyền nhạc là rủi ro bị gỡ video/claim doanh thu cao nhất trên YouTube.

## Scope
**In:** seed ~10 track (Pixabay Music/YouTube Audio Library — tải thủ công, license đầy đủ) vào assets(audio); API list BGM; admin upload track (license chọn từ danh sách chuẩn, bắt buộc); preview nghe trong picker (5-5).
**Out:** tìm nhạc theo mood bằng AI (v1.1); creator upload nhạc (admin only — rủi ro license); fade tuỳ chỉnh per-track.

## Business Rules
1. Track không license record → không xuất hiện trong picker (query-level filter).
2. License yêu cầu attribution → dòng ghi công tự nối vào description khi tải/đăng (6-3 BR-4, 8-3).
3. Admin upload: license + source_url bắt buộc; loại file mp3/m4a ≤15MB.

## Acceptance Criteria
1. **(happy)** Picker hiện ≥10 track nghe thử được; chọn → render có nhạc đúng volume/fade.
2. **(biên/BR-2)** Track cần ghi công → description có attribution.
3. **(lỗi/BR-3)** Upload thiếu license → 400 đúng field.
4. **(quyền)** Creator không upload được track.

## Data & API
Bảng: assets (media_type=audio). Endpoints: `GET /assets/bgm` (mới) + admin upload (dùng chung 5-3 upload) → cập nhật api-spec §6. Contract change: **có**.

## Decisions already locked
- 10 track seed do BA chọn đa dạng mood (tech/calm/upbeat) — danh sách trong PR.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + seed track là tài sản repo (Git LFS hoặc script tải kèm checksum — ⏳ chọn cách lưu).
