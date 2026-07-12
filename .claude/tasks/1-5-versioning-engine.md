# Task 1-5: Versioning engine

**Points:** 5đ · **Epic:** 1 — Nền tảng · **Depends:** 1-4 · **FR:** SRS §6

## User story
As a Content Creator, I want mọi bước có phiên bản với quan hệ nguồn gốc và khôi phục an toàn, so that tôi thử nghiệm nội dung thoải mái mà không sợ mất gì.

## Why
"Mọi dữ liệu có version và khôi phục được" là nguyên tắc thiết kế #4 của SRS. Quy tắc cascade-stale là cốt lõi — xem [patterns/scene-versioning.md](../patterns/scene-versioning.md) và [anti-patterns/overwrite-version.md](../anti-patterns/overwrite-version.md).

## Scope
**In:** bảng `step_versions`; service: create (auto-increment, parent_version), current (max không-stale), restore (cascade stale xuôi dòng theo thứ tự step), compare (text diff outline/script; scene-diff theo scene_id cho storyboard/scene_set); API §3 api-spec.
**Out:** UI VersionSwitcher/So sánh (5-9); visual diff preview (v1.1); nén/dọn version cũ (v1.1).

## Business Rules
1. Không bao giờ UPDATE content — chỉ INSERT version mới (see [anti-patterns/overwrite-version.md](../anti-patterns/overwrite-version.md)).
2. Restore tạo bản ghi hành động (actor) — không xoá, không sửa version nào.
3. Stale chỉ đánh xuôi dòng (restore research không stale chính nó).
4. Current = max(version) WHERE NOT stale; nếu tất cả stale → max(version) kèm cờ `all_stale`.
5. Regenerate khi user đã sửa tay → version mới `parent_version` = bản user-sửa.
6. Compare chỉ trong cùng step; khác step → 400.

## Acceptance Criteria
1. **(happy)** research v1,v2 + script v1(parent rv2): restore rv1 → script stale; response `staled_steps=[script]`.
2. **(biên/BR-5)** User sửa script v2 → regenerate → v3 parent=v2; diff v2↔v3 đúng phần AI đổi.
3. **(biên/BR-4)** Mọi version script stale → current trả max + cờ all_stale.
4. **(biên)** Compare 2 scene_set khác số cảnh → added/removed/changed đúng theo scene_id.
5. **(lỗi)** Restore version không tồn tại → 404; restore khi project RUNNING → 409.

## Data & API
Bảng: `step_versions`. Contract change: **có** — response restore thêm `staled_steps: []`; compare scene_set `{added[], removed[], changed[{scene_id, fields[]}]}` → cập nhật api-spec §3.

## Decisions already locked
- Giữ version vô hạn trong v1 (không auto-prune) — PO 2026-07-10.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + property test cascade (bất biến "current luôn xác định được", "không mất version nào").
