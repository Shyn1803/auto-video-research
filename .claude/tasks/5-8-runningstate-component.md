# Task 5-8: RunningState component + tích hợp mọi bước

**Points:** 3đ · **Epic:** 5 — Workspace UI · **Depends:** 1-6, 4-1, 4-7 · **FR:** NFR-1

## User story
As a Content Creator, I want màn "đang chạy" nhất quán cho mọi bước AI với thông điệp thật và nút huỷ/chạy ngầm, so that tôi luôn biết hệ thống đang làm gì và không bao giờ nhìn spinner câm.

## Why
Phát hiện lớn nhất của design-critique: trạng thái chạy là 50% trải nghiệm nhưng v1 không thiết kế. Component này là "gương mặt" của pipeline.

## Scope
**In:** component theo design-system §3.4: message SSE mới nhất + elapsed + progress (indeterminate khi không % thật) + Chạy ngầm + Huỷ (gọi 4-7); error state phân loại (hết-chain: render danh sách provider+lý do từ AllProvidersFailed; khác: message dịch nghĩa) + Thử lại + chi tiết collapse; tích hợp: mọi Duyệt→bước AI đi qua nó; stepper ●% khi ngầm.
**Out:** API cancel (4-7); notification (7-4).

## Business Rules
1. Chỉ hiện message SSE thật — không bịa %; không % → indeterminate.
2. Error hết-chain: admin thấy link Quản trị › Providers; creator thấy "báo quản trị viên" (đúng vai).
3. Huỷ confirm khi run >30s ("giữ kết quả các bước đã xong").
4. Sub-state "đang huỷ…" cho tới event xác nhận (4-7 BR-1).

## Acceptance Criteria
1. **(happy)** Duyệt Kịch bản → RunningState "Đang tạo phân cảnh…" message thật → tự chuyển editor khi xong.
2. **(biên)** Chạy ngầm → dashboard card ●% → click quay lại đúng màn đúng tiến độ.
3. **(lỗi/BR-2)** AllProvidersFailed → danh sách provider+lý do; đúng nội dung theo vai admin/creator.
4. **(BR-4)** Huỷ → "đang huỷ…" → về trạng thái đã huỷ kèm "chạy tiếp?".
5. **(a11y)** NVDA đọc message cập nhật; reduced-motion không animation pulse.

## Data & API
Consume SSE (1-6) + cancel (4-7). Contract change: không.

## Decisions already locked
- ⏳ Không ước lượng "còn X phút" v1 — chỉ elapsed + message.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + Storybook/fixture cho 4 trạng thái component; Playwright flow duyệt→running→auto-chuyển.
