# Task 8-6: Analytics dashboard

**Points:** 2đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-5 · **FR:** FR-13

## User story
As a Content Creator, I want dashboard tổng quan hiệu quả video theo thời gian và nền tảng, so that quyết định chủ đề tiếp theo dựa trên con số.

## Why
FR-13 phần hiển thị — vòng lặp học của cả sản phẩm.

## Scope
**In:** màn Analytics: 4 số tổng, chart theo ngày, bảng video (sort CTR/completion/views), filter platform + khoảng ngày; empty state; nút ✎ nhập tay per-row.
**Out:** so sánh A/B chủ đề (v1.1); export CSV (v1.1); per-video detail page.

## Business Rules
1. Metric nền tảng không cung cấp → "—" + tooltip lý do (không hiện 0 gây hiểu sai).
2. Số dashboard khớp DB tuyệt đối (test so khớp seed).
3. Nguồn số liệu (tự động/nhập tay) hiển thị per-row.

## Acceptance Criteria
1. **(happy)** Khớp wireframe; filter platform/ngày đúng; sort bảng đúng.
2. **(biên/BR-1)** TikTok completion → "—" + tooltip "nền tảng không cung cấp qua API".
3. **(BR-2)** Seed biết trước → 4 số tổng khớp query tay.
4. **(empty)** 0 video đăng → empty state + CTA.

## Data & API
Endpoints §8 dashboard/videos. Contract change: không.

## Decisions already locked
- 4 số tổng: Video/Views/Giờ xem/Xem hết + delta so kỳ trước.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + seed metrics 14 video × 30 ngày × 2 nền tảng; vitest cho aggregate hiển thị.
