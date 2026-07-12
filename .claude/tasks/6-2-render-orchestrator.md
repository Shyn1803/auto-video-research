# Task 6-2: Render orchestrator + worker in-process + cache + merge

**Points:** 5đ · **Epic:** 6 — Produce, Render & Download · **Depends:** 6-1, 2-2 · **FR:** FR-11

## User story
As a Content Creator, I want tạo video nhanh nhờ chỉ render phần thay đổi, so that vòng sửa–xem cuối cùng tính bằng chục giây thay vì render lại cả video.

## Why
Hiện thực lời hứa trung tâm của SRS ("scene là đơn vị cache/render độc lập"). **Invoke `/remotion-saas` + `/remotion-render` before writing** (dev-guide.md §2.1). Read [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md) first — render-worker only ever calls `renderMedia()` on the `Scene` composition, never `Video`.

## Scope
**In:** cache_key/cảnh (hash 2-1 + template_version + format); queue in-process (interface NATS-like); song song `RENDER_CONCURRENCY`; worker theo pipeline chính thức Remotion `bundle() → selectComposition() → renderMedia()` (`docs/specs/remotion-integration.md` §2.5) → MinIO; bảng renders + SSE render.progress; merge ffmpeg (concat + BGM volume/fade + CRF); retry từng job; per-format batch.
**Out:** worker container (9-2); multi-format UI (10-1 — engine sẵn); GPU encode (v1.1 nếu benchmark cần).

## Business Rules
1. Job idempotent theo cache_key — trùng → phát hiện qua renders/MinIO, bỏ qua.
2. Job fail không huỷ batch; batch kết thúc khi mọi job xong; trạng thái tổng trung thực ("7/8 + 1 lỗi").
3. Merge chỉ khi 100% cảnh done. **Merge is ffmpeg's job — never a second `renderMedia()` call on a whole-video composition** (see [rules/performance.md](../rules/performance.md)).
4. Sửa cảnh khi đang render → batch hiện tại chạy nốt; cảnh sửa dirty cho batch sau.
5. Output theo layout storage cố định (ARCHITECTURE §6); cache TTL dọn bởi cleanup job.
6. `bundle()` **1 lần lúc khởi động**, cache `serveUrl` in-memory, tái dùng cho mọi job sau đó — không bundle lại mỗi render (see [rules/performance.md](../rules/performance.md), [postmortems/](../postmortems/) bundle-caching gap).

## Acceptance Criteria
1. **(happy)** 8 cảnh 3 dirty → 3 render + 5 cache_hit; MP4 đúng thứ tự, audio sync, BGM fade.
2. **(biên/BR-4)** Sửa cảnh giữa batch → batch xong bình thường; nút "Tạo lại (1 cảnh)" hiện.
3. **(lỗi/BR-2)** 1 cảnh fail → batch kết thúc "7/8 + 1 lỗi"; retry cảnh đó → merge chạy.
4. **(biên/BR-1)** Kill worker giữa job → retry không double-render.
5. **(SSE)** Progress từng cảnh + tổng % đúng.

## Data & API
Bảng: renders. Endpoints §7. Events: render.progress. Contract change: không.

## Decisions already locked
- ⏳ CRF 20, preset medium khởi điểm — tune sau benchmark 6-4.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + đo "số lần render thực" bằng counter wrapper quanh CLI call; audio sync kiểm tay checklist (đầu/giữa/cuối). PR states which Remotion Skill was invoked.
