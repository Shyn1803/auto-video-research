# Task 3-1: Adapter base + registry + config layer

**Points:** 3đ · **Epic:** 3 — Provider framework · **Depends:** 1-1 · **FR:** FR-21

## User story
As a developer, I want khung adapter chuẩn cho mọi năng lực bên ngoài, so that thêm provider mới là 1 file + 1 decorator, không đụng business logic.

## Why
FR-21 là yêu cầu trung tâm của SRS ("local-first, kích hoạt bằng key"). Pattern adapter là việc lặp lại nhiều nhất toàn dự án (≥15 adapter đến release) — see [patterns/provider-adapter.md](../patterns/provider-adapter.md).

## Scope
**In:** base class 7 capability (LLM/TTS/Search/ImageGen/AssetStock/Storage/Publish) + `@register_{cap}(name)`; hợp nhất TTSAdapter 2-4 vào khung; `ProviderSettings` (env override DB); `ProviderError(retryable)`; adapter mẫu + test mẫu làm chuẩn copy.
**Out:** router chain (3-2); adapter cụ thể (3-3+); notification adapter (7-4 — dùng cùng khung).

## Business Rules
1. Adapter không đọc env/DB trực tiếp — nhận `ProviderSettings`.
2. Adapter không ghi usage/log nghiệp vụ — chỉ raise/return (việc của router). See [anti-patterns/direct-provider-call.md](../anti-patterns/direct-provider-call.md).
3. Registry trùng tên → fail startup (không ghi đè lặng lẽ).
4. Mỗi adapter khai báo `is_paid` tĩnh — quên khai = mặc định True (an toàn chi phí).

## Acceptance Criteria
1. **(happy)** Provider demo mới: 1 file + decorator → có trong registry, gọi được qua router mock.
2. **(lỗi/BR-3)** 2 adapter trùng tên → app không start, message chỉ rõ 2 file.
3. **(BR-4)** Adapter không khai is_paid → được coi paid (test).
4. **(chuẩn)** mypy strict pass; test mẫu chạy không network.

## Decisions already locked
- 7 capability cố định v1 — thêm capability mới cần ADR nhỏ.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + test mẫu là tài liệu sống, review PR đầu tiên khắt khe (là khuôn cho ~15 adapter sau).
