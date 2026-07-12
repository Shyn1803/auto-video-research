# Task 10-4: Security hardening

**Points:** 4đ · **Epic:** 10 — Release · **Depends:** toàn hệ (all prior tasks) · **FR:** NFR-4

## User story
As an operator, I want hệ thống khoá chặt trước khi ra production, so that key người dùng, nội dung và hạ tầng không thành điểm yếu khi hệ chạy công khai 24/7.

## Why
NFR-4 tổng nghiệm thu. Nguyên tắc: kiểm soát bằng **test tự động** (RBAC từ OpenAPI, secret-in-log, dependency scan) — không bằng trí nhớ reviewer. See [rules/security.md](../rules/security.md) and [checklists/security-review.md](../checklists/security-review.md).

## Scope
**In:** rate limit toàn API (user+IP, config); security headers (CSP Next, HSTS); CORS prod allowlist; test tự động "log không chứa secret" (mở rộng pattern 3-4/9-4 toàn hệ); `make rotate-fernet` + drill staging; pip-audit/npm-audit CI fail-on-critical; images non-root + pin digest; RBAC test sinh từ OpenAPI (route thiếu khai báo quyền → CI fail).
**Out:** pentest ngoài (v1.1 nếu thương mại hoá); WAF; SSO.

## Business Rules
1. Route mới bắt buộc khai báo quyền — enforced bằng test sinh từ OpenAPI.
2. Rotation Fernet không downtime — 2-key giai đoạn chuyển, re-encrypt batch.
3. Rate limit trả 429 chuẩn error format + Retry-After.
4. CSP không unsafe-inline cho script (Next config phù hợp).

## Acceptance Criteria
1. **(happy)** Checklist Bảo mật `docs/plan.md` §6 tick đủ kèm bằng chứng (screenshot/log/CI link).
2. **(biên/BR-2)** Rotation trên staging: hệ hoạt động xuyên suốt; key cũ hết hiệu lực sau hoàn tất.
3. **(CI/BR-1)** Route demo không khai quyền → CI fail; dependency critical giả → fail.
4. **(BR-3)** Vượt rate limit → 429 + Retry-After; UI toast lịch sự.
5. **(secret-log)** Test toàn hệ grep secret pass (chạy trên log integration test đầy đủ).

## Data & API
Middleware + CI jobs. Contract change: không (429 đã trong spec).

## Decisions already locked
- ⏳ Rate limit mặc định 100 req/phút/user, 20 req/phút cho auth endpoints.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + RBAC test generator là deliverable tái dùng vĩnh viễn; drill rotation ghi thời gian vào runbook.
