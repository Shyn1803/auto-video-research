# Task 8-4: Publish theo lịch

**Points:** 3đ · **Epic:** 8 — Publish & Analytics · **Depends:** 8-3, 7-1 · **FR:** FR-12

## User story
As a Content Creator, I want hẹn giờ đăng video vào khung giờ vàng, so that video ra đúng lúc khán giả online mà tôi không phải thức canh.

## Why
FR-12 scheduler + đường auto-publish của Mode 1 (7-3) đi qua đây — một cơ chế duy nhất cho cả hẹn tay lẫn tự động.

## Scope
**In:** scheduled_at → job type publish (7-1); datetime picker timezone VN; huỷ trước giờ; trạng thái "đã lên lịch 20:00" trên card + tab; Mode 1 auto-publish dùng đường này.
**Out:** gợi ý giờ vàng bằng analytics (v1.1); đăng lặp lại.

## Business Rules
1. Giờ quá khứ → chặn nhập (client + server).
2. Huỷ chỉ khi chưa bắt đầu uploading.
3. Job đăng fail → notify + giữ record scheduled để đặt lại — không lặng lẽ bỏ.
4. Timezone hiển thị/nhập là Asia/Ho_Chi_Minh; lưu UTC.

## Acceptance Criteria
1. **(happy)** Hẹn 20:00 → đăng ±2'; trạng thái chuyển đúng chuỗi.
2. **(biên/BR-2)** Huỷ 19:59 → không đăng; huỷ lúc uploading → 409 giải thích.
3. **(biên)** 2 nền tảng 2 giờ → 2 job độc lập chạy đúng.
4. **(lỗi/BR-3)** Fail lúc chạy → notify + nút đặt lại hoạt động.
5. **(BR-4)** Nhập 20:00 VN → DB UTC đúng; hiển thị lại đúng VN.

## Data & API
publishes.scheduled_at; job scheduler 7-1. Contract change: không.

## Decisions already locked
- ⏳ Không giới hạn số lịch chờ.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + freezegun cho giờ; test UTC conversion (DST không cần — VN không DST).
