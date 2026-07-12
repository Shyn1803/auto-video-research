# Task 2-1: Scene JSON schema v1 — Pydantic + export + Zod

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 1-1 (parallel with Track A) · **FR:** FR-08, AR-3

## User story
As a developer, I want một nguồn schema duy nhất mà backend, frontend và Remotion cùng dùng, so that ba bên không bao giờ lệch contract trung tâm của hệ thống.

## Why
Scene JSON là contract quan trọng nhất ([decisions/0004-scene-json-contract.md](../decisions/0004-scene-json-contract.md)): preview, cache, render, versioning, editor đều đứng trên nó.

## Scope
**In:** Pydantic models đầy đủ theo `docs/specs/scene-json-schema.md` (VideoProject/Scene/5 layout/các type §3); validator ngoài-schema §5 hai chế độ `auto_fix`/`strict`; `make gen-scene-schema` (JSON Schema → Zod — Zod là schema prop chính thức của `<Composition>` Remotion, xem `docs/specs/remotion-integration.md` §2.1); fixtures share pytest/vitest (hợp lệ mỗi layout + ≥3 lỗi); CI gate diff; hàm canonical hash.
**Out:** schema v2 elements (chart/video/karaoke); migration runner; UI form (5-1 tiêu thụ).

## Business Rules
1. Canonical hash: sort keys, UTF-8 NFC, bỏ `scene_number` — đổi thứ tự cảnh không phá cache.
2. `auto_fix` chỉ sửa vi phạm "cắt được" (thừa phần tử, duration lệch, thiếu default) + log warning; kiểu dữ liệu sai → lỗi kể cả auto_fix.
3. Mọi lỗi strict có `field_path` máy-đọc-được để FE map inline.
4. Fixtures là contract test hai chiều — thêm rule validator mới bắt buộc kèm fixture fail tương ứng.

## Acceptance Criteria
1. **(happy)** Fixture hợp lệ pass pytest+vitest; fixture lỗi fail cả hai cùng field_path.
2. **(biên/BR-2)** 6 texts vào TextFocus (max 3): auto_fix cắt còn 3 + warning; strict → 422 `texts`.
3. **(biên/BR-1)** Đổi scene_number/thứ tự key → hash không đổi; đổi 1 ký tự content → hash đổi.
4. **(lỗi)** `duration_ms: "abc"` → lỗi kiểu cả 2 chế độ.
5. **(CI)** Sửa Pydantic không chạy gen → CI fail đúng thông điệp.

## Data & API
File sinh: `packages/remotion-templates/schema/scene-1.0.0.json` + `schema.ts` (Zod) commit vào repo. Contract change: khởi tạo contract trung tâm.

## Decisions already locked
- 11 layout class v1, PascalCase canonical (Hero/TextFocus/MediaFull/MediaText/Comparison/BigNumber/Chart/VersusTable/List/Quote/Code) — thêm class = minor version + preset json; class do Classifier chọn, không phải AI. See [rules/naming.md](../rules/naming.md), [anti-patterns/layout-name-drift.md](../anti-patterns/layout-name-drift.md).
- Số liệu motion chuyển thể từ taste-skill (`docs/specs/video-taste.md`), hiệu chỉnh nhịp web→video (chậm hơn ~1.5×).

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + từng rule §5 một unit test; property test hash (random permutation không đổi hash).
