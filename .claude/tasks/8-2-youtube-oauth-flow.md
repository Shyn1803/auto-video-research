# Task 8-2: YouTube OAuth flow

**Points:** 5đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-1, 3-4 · **FR:** FR-12, FR-21

## User story
As an Admin, I want kết nối kênh YouTube qua OAuth ngay trong trang Quản trị, so that hệ thống đăng thay tôi mà tôi không phải đưa mật khẩu Google cho ai.

## Why
YouTube là nền tảng auto-publish chính của v1. Refresh token là secret nhạy cảm nhất hệ thống nắm giữ — BR bảo mật khắt khe tương ứng. See [rules/security.md](../rules/security.md).

## Scope
**In:** Google OAuth (client id/secret env — FR-21): flow connect trong Quản trị › API Keys; refresh token mã hoá (api_keys provider `youtube_oauth`); auto refresh access; revoke/reconnect; đa kênh (default + chọn khi đăng).
**Out:** app verification với Google (việc PO — checklist runbook); OAuth nền tảng khác (10-3 dùng pattern này).

## Business Rules
1. Refresh token chỉ trong DB mã hoá — không log/response/error message.
2. Refresh fail (revoked phía Google) → trạng thái "mất kết nối" + notify + hướng dẫn; hàng YouTube ở màn publish tự chuyển ⚠.
3. State param chống CSRF trong OAuth flow; redirect URI cố định từ env.
4. Ngắt kết nối → xoá token + revoke phía Google (best effort).

## Acceptance Criteria
1. **(happy)** Connect → consent → kênh hiện tên+avatar; token mã hoá trong DB.
2. **(biên/BR-2)** Giả lập 401 refresh → "mất kết nối" + notify; reconnect phục hồi.
3. **(bảo mật/BR-1,3)** Grep log/response không token; callback sai state → 403.
4. **(đa kênh)** 2 kênh → đăng chọn đúng kênh; default hoạt động.
5. **(BR-4)** Ngắt kết nối → token xoá; đăng YouTube → trạng thái "chưa cấu hình".

## Data & API
Bảng: api_keys (provider youtube_oauth, key_encrypted = refresh token). Endpoints: `GET /admin/oauth/youtube/start`, `GET /admin/oauth/youtube/callback` (mới) → cập nhật api-spec §9. Contract change: **có**.

## Decisions already locked
- Privacy video mặc định **unlisted**; đổi qua config.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + mock Google OAuth server trong integration test; flow thật kiểm tay 1 lần (ghi vào PR).
