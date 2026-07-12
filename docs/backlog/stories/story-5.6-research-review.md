# Story 5.6 — Màn Nghiên cứu: review nguồn + Kiểm chứng (5đ — tăng từ 3đ sau khi soi đủ scope)

**User story:** As a Content Creator, I want xem/lọc nguồn và xử lý từng claim kiểm chứng trên một màn, so that tôi tin nội dung video trước khi cho AI viết tiếp.
**Bối cảnh & giá trị:** Đây là gate chống hallucination (FR-02/04) — màn duy nhất user "trả nợ tin cậy" cho toàn pipeline. Nếu màn này khó dùng, user sẽ duyệt bừa → video sai → mất uy tín kênh. Wireframe v2 đặt Kiểm chứng làm tab mặc định khi có claim ⚠/✗.

## Scope
**In:**
- Tab **Nguồn**: list SourceCard (pin/loại/xoá, badge tin cậy/partial, score+reason), thêm URL tay, filter.
- Tab **Kiểm chứng**: list ClaimRow nhóm theo verdict (✗ trước, ⚠ giữa, ✓ cuối), evidence expand, override flow, panel nguồn liên quan bên phải (highlight 2 chiều claim↔nguồn).
- ApproveBar: "Duyệt & tiếp tục ▸" theo BR-1; "Nghiên cứu lại".
- RunningState khi research/factcheck đang chạy (tái dùng component, không tự chế).

**Out:**
- Logic crawl/verdict (story 4.3/4.4 — màn này chỉ consume API).
- Sửa nội dung tóm tắt nguồn (không có trong SRS — nếu PO muốn, story mới).
- So sánh version research (VersionSwitcher — story 1.5 UI).

## Business Rules
- **BR-1 (gate):** Nút Duyệt disabled khi ∃ claim `FAIL` chưa xử lý. Claim `WARN` không chặn nhưng hiển thị cảnh báo tổng "2 thông tin sẽ được nói kèm 'theo nguồn chưa xác nhận'".
- **BR-2 (override):** Xử lý claim FAIL = chọn 1 trong: (a) chọn giá trị đúng từ evidence (radio) + lý do bắt buộc ≥10 ký tự; (b) loại claim khỏi video. Cả hai ghi audit (actor, lý do, thời điểm) và **không xoá** evidence gốc.
- **BR-3 (tính lại):** Sau override, verdict tổng project tính lại ngay (client nhận qua response, không cần reload).
- **BR-4 (nguồn bị loại):** Disable/xoá một nguồn đang là evidence duy nhất của claim PASS → claim đó tự hạ WARN + toast cảnh báo nêu tên claim.
- **BR-5 (pin):** Nguồn pinned không thể xoá (phải bỏ pin trước); pinned luôn được truyền vào các bước AI sau.
- **BR-6 (thêm URL):** URL trùng nguồn hiện có (theo url_hash) → focus nguồn đó thay vì tạo mới; URL crawl fail → nguồn hiện trạng thái lỗi + nút thử lại, không chặn màn.
- **BR-7 (stale):** Nếu user vào màn khi các bước sau đã tồn tại (quay lại sửa), banner stale theo pattern chung; Duyệt lại → xác nhận "3 bước sau sẽ đánh dấu lỗi thời".

## UI/UX
- Màn: wireframe.html → **Nghiên cứu**; components: SourceCard, ClaimRow (design-system §3.7), ApproveBar §3.3, RunningState §3.4.
- 5 states: default (wireframe) · loading = RunningState "Đang đọc nguồn X (4/12)" · empty (0 nguồn sau research — hiếm): "Không tìm được nguồn cho chủ đề này" + [Thử từ khoá khác] [Thêm URL tay] · error = pattern hết chain §3.4 · disabled = readonly khi project không ở NEED_REVIEW/REVISING (xem lại từ stepper ✓).
- A11y: ClaimRow là accordion (`aria-expanded`); radio evidence điều hướng mũi tên; highlight claim↔nguồn không chỉ bằng màu (border + icon 🔗).

## Data & API
- Đọc: `GET /projects/{id}/sources`, `GET /projects/{id}/claims` (api-spec §4, §5).
- Ghi: `PATCH sources/{sid}` (pin/disable), `DELETE sources/{sid}`, `POST sources` (URL tay), `POST claims/{cid}/override`, `POST steps/research/approve`.
- Contract change: **có** — response `override` cần trả thêm `overall_verdict` mới + danh sách claim bị hạ verdict (BR-3, BR-4) → cập nhật api-spec §5 trong PR.
- Events: `factcheck.verdict` (đã có); audit vào `status_history` khi approve.

## Acceptance Criteria
- **AC-1 (happy):** Given project NEED_REVIEW có 1 FAIL + 1 WARN + 5 PASS, When mở màn, Then tab Kiểm chứng mở sẵn, FAIL trên đầu, nút Duyệt disabled kèm tooltip "Còn 1 claim mâu thuẫn". When override chọn giá trị + lý do, Then verdict tổng thành WARN, nút Duyệt enable, cảnh báo WARN hiển thị.
- **AC-2 (biên — BR-4):** Given claim PASS có evidence duy nhất từ nguồn S, When loại S, Then claim hạ WARN ngay + toast nêu tên claim; When bật lại S, Then claim trở về PASS.
- **AC-3 (biên — BR-6):** When thêm URL đã tồn tại, Then không tạo bản ghi mới, scroll+focus nguồn cũ; When thêm URL crawl fail, Then card lỗi + [Thử lại], màn vẫn thao tác được.
- **AC-4 (lỗi):** Given API claims trả 500, When mở màn, Then error state có [Thử lại], không trắng màn; sources vẫn hiện nếu load được (2 tab độc lập).
- **AC-5 (quyền):** Creator không phải owner → 403 → màn "không có quyền"; Admin mở được readonly + thao tác như owner.
- **AC-6 (keyboard):** Toàn bộ flow xử lý 1 claim FAIL làm được không dùng chuột (tab→mũi tên→nhập lý do→Enter); `Ctrl+Enter` = Duyệt khi enabled.

## Test Notes
- Fixture: bộ claims 1 FAIL/1 WARN/5 PASS + evidence chéo với 12 sources (dùng chung fixture 4.4).
- Tự động: vitest cho BR-1/3/4 logic hiển thị; Playwright cho AC-1, AC-6 (nằm trong E2E journey); pytest contract test cho response override mới.
- Test tay: highlight 2 chiều claim↔nguồn; đọc màn bằng screen reader 1 lần.

## Quyết định đã chốt
- "WARN có chặn Duyệt không?" → **Không**, chỉ cảnh báo + video tự thêm disclaimer (PO, 2026-07-10).
- "Override có sửa được nội dung claim không?" → **Không** trong v1, chỉ chọn evidence hoặc loại bỏ (PO, 2026-07-10).

**Depends:** 4.3, 4.4 (API), 1.5 (stale banner), design-system components · **Design:** wireframe v2 Nghiên cứu · **FR:** FR-02, FR-04
