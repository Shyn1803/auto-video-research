# Task 10-6: Release — docs, checklist, go-live

**Points:** 2đ · **Epic:** 10 — Release · **Depends:** 10-4, 10-5 · **FR:** Release plan §1

## User story
As a team, I want quy trình release có gate rõ và theo dõi 48h đầu, so that v1.0 ra production có kiểm soát và học được gì đó cho v1.1.

## Why
Điểm kết của `docs/plan.md`. BR-1 (không ngoại lệ cho Bảo mật/Vận hành) là cam kết kỷ luật — release trễ 1 tuần rẻ hơn sự cố production tuần đầu.

## Scope
**In:** rà docs khớp code (specs/CONFIGURATION/runbook theo staging thật); Release Checklist `docs/plan.md` §6 — mỗi mục người tick + bằng chứng; tag v1.0.0; deploy prod theo runbook §1; bật lịch Mode 1; theo dõi 48h (alert channel + phân công trực); retro release → backlog v1.1.
**Out:** marketing/công bố; v1.1 planning chi tiết (sau retro).

## Business Rules
1. Mục checklist nhóm Bảo mật/Vận hành không đạt → không release; không có "fix sau".
2. Deploy prod đúng runbook — lệch = sửa runbook trước rồi làm lại theo.
3. 48h đầu: mọi alert có người nhận trong 30' (phân công ghi rõ).

## Acceptance Criteria
1. **(gate)** Checklist 100% có bằng chứng; nhóm Bảo mật/Vận hành không mục nào waive.
2. **(go-live)** Prod chạy 48h không Sev-1; Mode 1 sáng đầu tiên trên prod thành công.
3. **(retro)** Biên bản retro + danh sách v1.1 (TikTok/FB kích hoạt, visual diff, A/B prompt, autoscale…) commit vào docs.

## Data & API
N/A. Output: tag, checklist hoàn chỉnh, biên bản retro.

## Decisions already locked
- ⏳ Định nghĩa Sev-1: mất khả năng tạo/duyệt/đăng video hoặc lộ dữ liệu.

## Definition of Done
Không test mới — thực thi và ghi nhận. This is the final task in the 230-point backlog — after this, update [memory/project-memory.md](../memory/project-memory.md) with the v1.0 milestone and retro findings per CLAUDE.md §8 Continuous Learning Policy.
