# Task 1-2: Auth JWT + RBAC

**Points:** 3đ · **Epic:** 1 — Nền tảng · **Depends:** 1-1 · **FR:** NFR-4

## User story
As a user, I want đăng nhập an toàn với vai trò admin/creator, so that dữ liệu và thao tác được bảo vệ đúng người.

## Why
Nền của mọi kiểm soát quyền. Làm sai ở đây thì audit, RBAC, publish đều mất giá trị; refresh-rotate chống chiếm phiên là yêu cầu NFR-4.

## Scope
**In:** bảng `users`, `refresh_tokens` (docs/specs/database-schema.md §2.1); argon2id; seed admin từ `ADMIN_EMAIL/PASSWORD`; endpoints `/auth/login|refresh|logout|me` (api-spec §1); refresh cookie httpOnly + rotate; dependency `require_role()`; rate limit login (slowapi); FE trang Login + AuthProvider + interceptor auto-refresh.
**Out:** CRUD user (1-7); quên mật khẩu qua email (v1.1); SSO (ngoài scope v1).

## Business Rules
1. Access 15' / refresh 7d rotate; refresh token cũ bị dùng lại → revoke **cả chuỗi** (phát hiện token bị đánh cắp) + ghi audit.
2. 5 lần sai/15' theo cặp email+IP → 429 kèm `retry_after`.
3. User `is_active=false` → 401 ngay cả khi token còn hạn (check mỗi request qua cache 60s).
4. Mật khẩu tối thiểu 10 ký tự; hash argon2id tham số chuẩn OWASP.

## Acceptance Criteria
1. **(happy)** Login đúng → access + cookie; `GET /auth/me` trả user; refresh rotate hoạt động.
2. **(biên/BR-1)** Dùng lại refresh đã rotate → 401 + cả chuỗi revoke; đăng nhập lại bình thường.
3. **(lỗi/BR-2)** Sai 5 lần → 429 + retry_after; UI hiện đếm ngược.
4. **(quyền)** Creator gọi route 🅐 → 403 error body chuẩn; admin 200.
5. **(biên/BR-3)** Khoá user đang có token sống → request kế ≤60s bị 401.

## Data & API
Bảng: `users`, `refresh_tokens`. Endpoints: api-spec §1 nguyên trạng. Events/audit: login fail vượt ngưỡng → log security; revoke chuỗi → audit record. Contract change: không.

## UI/UX
Màn Login (wireframe). States: default/loading/error(aria-live+countdown)/empty N/A/disabled N/A. A11y: Enter submit, labels, screen-reader errors.

## Decisions already locked
- ⏳ Không "remember me" v1 (refresh 7d là đủ).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + unit đủ nhánh token service (rotate/reuse/expire) + integration login flow, no external network calls in tests.
