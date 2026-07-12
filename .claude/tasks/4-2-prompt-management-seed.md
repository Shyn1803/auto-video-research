# Task 4-2: Prompt Management + seed

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-1 · **FR:** FR-14

## User story
As an Admin, I want prompt lưu DB có version và kích hoạt được không cần deploy, so that tune chất lượng tiếng Việt liên tục.

## Why
FR-14. Chất lượng nội dung Việt phụ thuộc prompt nhiều hơn model; chu kỳ tune phải tính bằng phút, không bằng ngày.

## Scope
**In:** bảng prompts/prompt_versions; seed 8 prompt từ `docs/specs/prompts.md`; Jinja2 render + validate biến khai báo; `get_active_prompt(name)` cache invalidate-on-activate; tab Quản trị › Prompts (list/editor/diff 2 version/activate/rollback); CLI `make prompt-eval`.
**Out:** A/B prompt (v1.1); eval tự chấm bằng LLM (v1.1); prompt per-project.

## Business Rules
1. Đúng 1 version active/prompt (DB partial unique index).
2. Activate bản chưa chạy eval → dialog cảnh báo, không chặn cứng (trust admin, ghi audit).
3. Template dùng biến ngoài `variables[]` → 400 khi lưu.
4. Node không hardcode prompt — CI grep chuỗi template trong `pipeline/` → fail. See [rules/dependency-management.md](../rules/dependency-management.md).
5. Rollback = activate version cũ (không tạo bản sao — lịch sử thẳng).

## Acceptance Criteria
1. **(happy)** Sửa script.generate → v2 → activate → call kế dùng v2 (không restart); rollback v1 OK.
2. **(biên/BR-3)** Lưu template có `{{ bien_la }}` → 400 nêu đúng biến.
3. **(quyền)** Creator → 403; audit ghi ai activate lúc nào.
4. **(eval)** `make prompt-eval PROMPT=script.generate V=2` xuất bảng so sánh 10 topic.
5. **(BR-1)** Race 2 activate đồng thời → 1 thắng, constraint giữ đúng 1 active.

## Data & API
Bảng: prompts/prompt_versions. Endpoints §9. Contract change: không.

## Decisions already locked
- Eval là bước khuyến nghị mạnh, không bắt buộc cứng — tốc độ tune quan trọng giai đoạn đầu.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture eval_topics.json 10 topic là tài sản dùng lâu dài.
