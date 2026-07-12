# Task 5-9: VersionSwitcher + màn So sánh/History

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 1-5, 5-1 · **FR:** SRS §6

## User story
As a Content Creator, I want xem, so sánh, khôi phục phiên bản ngay tại bước đang đứng, so that thử nghiệm nội dung thoải mái và quay lại trong 2 cú click.

## Why
Critique v1: History tách rời ngữ cảnh khiến versioning "có mà như không". Task này biến engine 1-5 thành giá trị nhìn thấy được.

## Scope
**In:** dropdown `v3 ▾` topbar (list: thời gian/tác giả/badge stale+tooltip); Xem (readonly overlay); So sánh với hiện hành (màn diff side-by-side text; scene-diff list added/removed/changed); Khôi phục (confirm hệ quả — dùng service 1-5); History tổng (route phụ bảng mọi bước).
**Out:** visual diff 2 preview (v1.1); so sánh chéo step (cấm).

## Business Rules
1. Khôi phục từ switcher = service 1-5 duy nhất (một đường).
2. Đang có thay đổi chưa autosave → chuyển version hoãn tới lưu xong (≤1.5s), không mất chữ.
3. Badge stale tooltip nêu nguồn gốc.
4. Diff hiển thị thêm/xoá bằng prefix + màu (không chỉ màu — a11y).

## Acceptance Criteria
1. **(happy)** So sánh script v1↔v2 → highlight đúng dòng; đóng quay về đúng chỗ.
2. **(biên)** Khôi phục scene_set v2 → confirm "Hoàn thiện sẽ lỗi thời" → trạm sau chuyển stale trên stepper.
3. **(biên/BR-2)** Đang gõ → chuyển version → hoãn lưu xong mới chuyển, không mất chữ.
4. **(empty)** Bước 1 version → dropdown thông báo đúng, không lỗi.
5. **(quyền)** Project RUNNING → nút khôi phục disabled + tooltip.

## Data & API
Endpoints versions/compare/restore (§3 — 1-5 đã chuẩn `staled_steps`). Contract change: không.

## Decisions already locked
- ⏳ History tổng giữ (route phụ, ít dùng) — giá trị audit; không đầu tư UI đẹp cho nó v1.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture 3 version có stale; Playwright flow so sánh→khôi phục→stepper stale.
