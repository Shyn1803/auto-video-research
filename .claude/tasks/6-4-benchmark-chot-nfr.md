# Task 6-4: Benchmark & chốt NFR

**Points:** 3đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 6-2 · **FR:** NFR-1

## User story
As a team, I want số đo hiệu năng thật trên máy chuẩn, so that NFR là cam kết có cơ sở và quyết định tối ưu dựa trên dữ liệu.

## Why
SRS v3 cố ý để NFR "chốt sau benchmark" — đây là điểm chốt. Kết quả quyết định nhánh `docs/plan.md` §5 (cắt 10-2 lấy chỗ tối ưu hay không).

## Scope
**In:** script benchmark (render/cảnh mỗi layout ×2 format, video 60s, preview load-time); định nghĩa "máy chuẩn" ghi vào ARCHITECTURE.md; chạy 3 lần lấy median; cập nhật NFR-1 số thật; profiling nếu >2× mục tiêu; báo cáo go/no-go với PO trước tuần 11.
**Out:** load test đa user (10-5); tối ưu thực thi (task riêng nếu cần).

## Business Rules
1. Kết quả xấu không im lặng — bắt buộc issue nguyên nhân + phương án + estimate.
2. Benchmark script vào repo, chạy lại được 1 lệnh (dùng lại ở 9-2 AC-1 và 10-5).

## Acceptance Criteria
1. **(happy)** Bảng số liệu (median 3 runs) commit; NFR-1 cập nhật kèm cấu hình máy chuẩn.
2. **(biên/BR-1)** Nếu 60s-video > 6 phút → issue phân tích (bundling? codec? concurrency?) + quyết định PO ghi lại.
3. **(BR-2)** `make benchmark` chạy lại ra kết quả cùng định dạng.

## Data & API
N/A. Output: bảng số liệu trong ARCHITECTURE.md + NFR-1 SRS cập nhật.

## Decisions already locked
- ⏳ Máy chuẩn = máy dev GPU hiện có (ghi cấu hình cụ thể khi chạy).

## Definition of Done
Không phải test — là đo đạc; script tái dùng làm smoke perf về sau. Update [context/testing-strategy.md](../context/testing-strategy.md) with real numbers once measured, per CLAUDE.md §9 known-gaps policy.
