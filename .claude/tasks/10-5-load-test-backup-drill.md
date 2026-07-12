# Task 10-5: Load test + backup drill + nghiệm thu local-first

**Points:** 3đ · **Epic:** 10 — Release · **Depends:** 9-2, 9-5 · **FR:** NFR-2/3/6, FR-21

## User story
As a team, I want bằng chứng hệ chịu tải mục tiêu, khôi phục được từ backup, và chạy đủ với 0 API key, so that release dựa trên kiểm chứng chứ không hy vọng.

## Why
3 mục "Vận hành" của Release Checklist. BR-1 (người không viết code làm drill) kiểm luôn chất lượng runbook — tài liệu chưa ai làm theo là tài liệu chưa xong.

## Scope
**In:** k6/locust: 5 render đồng thời + 20 user UI trên staging → số liệu vào ARCHITECTURE.md; đánh giá autoscale cần/chưa (quyết định cho v1.1); restore drill máy sạch theo runbook (đo thời gian, do người không viết code thực hiện); CI job E2E `.env` 0 key (nightly với Ollama thật).
**Out:** stress đến gãy; multi-region.

## Business Rules
1. Drill do người không viết code làm theo runbook — mọi chỗ tắc = bug tài liệu → sửa runbook trong task này.
2. Load test chạy trên staging cấu hình = production (không test trên dev).
3. Nightly 0-key phải xanh 3 đêm liên tiếp mới tick (chống may mắn).

## Acceptance Criteria
1. **(load)** 5 render + 20 user: không lỗi, p95 API <1s (⏳ ngưỡng), số liệu commit.
2. **(drill/BR-1)** Restore máy sạch thành công bởi người không viết code; thời gian ghi runbook; chỗ tắc đã sửa docs.
3. **(local-first/BR-3)** Nightly 0-key xanh 3 đêm liên tiếp — nghiệm thu FR-21/NFR-6 chính thức.

## Data & API
N/A. Output: số liệu ARCHITECTURE.md; thời gian restore vào runbook; CI job mới.

## Decisions already locked
- ⏳ p95 API < 1s dưới tải mục tiêu.

## Definition of Done
k6 script vào repo (`make loadtest`); drill có biên bản ngắn (ai, bao lâu, vướng gì). This is measurement + operational verification, not just code — see [checklists/before-release.md](../checklists/before-release.md).
