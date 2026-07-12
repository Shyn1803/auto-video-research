# Task 1-7: Quản lý người dùng (Admin)

**Points:** 2đ · **Epic:** 1 — Nền tảng · **Depends:** 1-2 · **FR:** Personas §3

## User story
As an Admin, I want tạo/khoá/đổi vai trò người dùng, so that kiểm soát được ai dùng hệ thống và với quyền gì.

## Why
Persona Admin (SRS §3) có quyền "Quản lý người dùng" nhưng backlog gốc bỏ sót — gap phát hiện khi rà luồng. Không có task này thì thêm thành viên thứ 3 phải sửa DB tay.

## Scope
**In:** CRUD users 🅐 (api-spec §1); tab Quản trị › Người dùng (list, tạo với mật khẩu tạm, đổi role, khoá/mở); audit thao tác; revoke phiên khi khoá (nối 1-2 BR-3).
**Out:** self-service đổi/quên mật khẩu (v1.1); mời qua email (v1.1); nhóm/workspace (ngoài scope v1).

## Business Rules
1. Không tự khoá/hạ quyền chính mình.
2. Khoá user → mọi refresh token revoke ngay.
3. Luôn còn ≥1 admin active — thao tác vi phạm → 409 kèm giải thích.
4. Mật khẩu tạm buộc đổi ở lần đăng nhập đầu (cờ `must_change_password`).

## Acceptance Criteria
1. **(happy)** Tạo creator + mật khẩu tạm → đăng nhập được → bị buộc đổi mật khẩu → vào bình thường.
2. **(biên/BR-2)** Khoá user đang đăng nhập → request kế ≤60s 401.
3. **(lỗi/BR-3)** Khoá admin cuối → 409 giải thích rõ.
4. **(quyền)** Creator không thấy tab; API → 403.
5. **(BR-1)** Nút khoá/đổi role trên dòng chính mình disabled + tooltip.

## Data & API
Bảng: `users` (+cột `must_change_password`); audit vào bảng chung. Contract change: **có** — thêm `must_change_password` flow vào `/auth/login` response → cập nhật api-spec §1.

## UI/UX
Wireframe Quản trị › Người dùng. States: default/loading(skeleton)/empty(hướng dẫn thêm)/error/disabled(BR-1+tooltip). A11y: bảng caption, select role label, confirm dialog.

## Decisions already locked
- ⏳ V1 không email mời — admin đưa mật khẩu tạm trực tiếp (đội nhỏ nội bộ).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture 2 user + case 1-admin-duy-nhất; Playwright khoá → session kia văng.
