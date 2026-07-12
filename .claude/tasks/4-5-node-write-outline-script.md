# Task 4-5: Node Write — outline + script

**Points:** 3đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-4, 4-2 · **FR:** FR-05, FR-06

## User story
As a Content Creator, I want dàn ý rồi kịch bản tiếng Việt có dẫn nguồn từng phần, so that tôi chỉ biên tập thay vì viết từ đầu, và luôn truy được mọi câu về nguồn.

## Why
FR-05/06. Ràng buộc "chỉ dùng fact đã kiểm chứng" là điểm nối giữa fact-check và nội dung — nơi hallucination bị chặn lần cuối trước khi thành lời đọc.

## Scope
**In:** outline (prompt §5 — 7 phần, dẫn [source_id], chỉ claim PASS/WARN-đã-duyệt); script (prompt §6 — giữ số liệu; check tự động tập số outline ⊆ script, lệch → retry 1 → cờ warning); 2 sub-step approve riêng; PUT version sửa tay.
**Out:** UI (5-7); tone/style tuỳ chọn (v1.1).

## Business Rules
1. Claim FAIL "loại khỏi video" → nội dung đó không xuất hiện outline/script (lọc context trước prompt).
2. voice_over viết số thành chữ đọc được; validator cảnh báo nếu còn ký hiệu (%/$) trong voice_over.
3. Title >70 ký tự → cắt thông minh tại ranh giới từ + cờ cho user xem.
4. Claim WARN dùng trong script → câu đó kèm "theo nguồn chưa xác nhận" (prompt yêu cầu + validator kiểm sự hiện diện).

## Acceptance Criteria
1. **(happy)** Outline 7 phần đủ [source_id]; script đúng cấu trúc; tập số khớp.
2. **(biên/BR-1)** Claim FAIL bị loại → không xuất hiện trong outline.
3. **(biên/BR-4)** Claim WARN được dùng → câu chứa "theo nguồn chưa xác nhận".
4. **(lỗi/BR-2,3)** Script lệch số sau retry → version có warnings; title dài → cắt + warning.
5. **(version)** Sửa outline tay → script sinh từ bản sửa (parent đúng — 1-5 BR-5).

## Data & API
Dữ liệu: step_versions (outline, script) + warnings trong content JSONB. Contract change: **có** — chuẩn hoá `warnings[]` trong content version → ghi vào api-spec §3.

## Decisions already locked
- ⏳ Không chặn cứng khi lệch số sau retry — con người quyết (cờ warning + UI nêu rõ).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + check "tập số ⊆" là pure function, unit kỹ (định dạng 92,5 vs 92.5 vs chữ, so sánh sau chuẩn hoá).
