# Task 4-4: Node Ranking + FactCheck

**Points:** 5đ · **Epic:** 4 — Pipeline AI · **Depends:** 4-3 · **FR:** FR-03, FR-04

## User story
As a Content Creator, I want mọi thông tin quan trọng được kiểm chéo giữa các nguồn độc lập, so that video không bao giờ nói sai tên, số, ngày — thứ giết uy tín kênh nhanh nhất.

## Why
FR-03/04 — lý do tồn tại của sản phẩm so với "ChatGPT viết kịch bản". Gate PASS/WARN/FAIL đã đặc tả định lượng trong SRS.

## Scope
**In:** ranking (prompt `ranking.score`, trọng số config) → score/reason vào source; factcheck: extract claims (`factcheck.extract_claims`) → gom evidence (embedding search) → verdict/claim (`factcheck.verify_claim`); verdict tổng + gate (FAIL→NEED_REVIEW+notify); API claims + override (§5); fixture kịch bản mâu thuẫn.
**Out:** UI (5-6); notify channel thật (7-4 — tạm log); re-check tự động theo chu kỳ.

## Business Rules
1. PASS cần ≥2 nguồn **độc lập** — khác root domain; 2 bài cùng blog = 1 nguồn.
2. Evidence từ source `partial_content` không đủ cho PASS (tối đa WARN).
3. Override ghi audit, không xoá evidence; verdict tổng tính lại đồng bộ trong cùng request.
4. Claim không tìm được evidence → WARN "không tìm thấy nguồn xác nhận".
5. Disable/xoá source → mọi claim có evidence từ nó tính lại verdict (đồng bộ, cùng response).
6. Claim types theo spec (model_name/benchmark/release_date/paper/github/version/other); extraction bỏ ý kiến chủ quan.

## Acceptance Criteria
1. **(happy)** Fixture 2 nguồn lệch ngày → claim FAIL + evidence 2 phía; project NEED_REVIEW; notify (log) bắn.
2. **(biên/BR-1)** 2 bài cùng openai.com xác nhận → WARN, không PASS.
3. **(biên/BR-5)** Disable nguồn evidence duy nhất của claim PASS → claim WARN, response chứa affected_claims.
4. **(override/BR-3)** Chọn giá trị đúng + lý do → verdict đổi + overall mới; audit query được.
5. **(BR-4)** Claim mồ côi → WARN đúng message.
6. **(quyền)** Creator không owner → 403.

## Data & API
Bảng: claims. Contract change: **có** — response override/patch-source thêm `overall_verdict` + `affected_claims[]` → cập nhật api-spec §5.

## Decisions already locked
- WARN không chặn duyệt; video tự thêm "theo nguồn chưa xác nhận" (PO 2026-07-10).
- ⏳ Trọng số ranking mặc định: mới 0.3 / liên quan 0.3 / tin cậy 0.25 / xác nhận chéo 0.15.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + fixture mâu thuẫn là tài sản test dùng lại ở 5-6, 7-2, E2E.
