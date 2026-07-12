# Task 2-3: Remotion Player preview trong Next.js

**Points:** 3đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-2 · **FR:** FR-09, AR-4

## User story
As a Content Creator, I want xem phân cảnh ngay trong trình duyệt khi chỉnh sửa, so that vòng lặp chỉnh–xem tính bằng giây thay vì chờ render.

## Why
"Preview tức thì" là NFR-1 và lý do chọn kiến trúc Remotion Player ([decisions/0006-remotion-player-shared-template.md](../decisions/0006-remotion-player-shared-template.md): Player và worker cùng template → preview = render, không lệch pixel). **Invoke `/remotion-interactivity` before writing** (dev-guide.md §2.1).

## Scope
**In:** `ScenePlayer` wrap `<Player>` thật của `@remotion/player` (props: `component`, `inputProps`=scene JSON, `durationInFrames`, `fps`, `compositionWidth/Height` theo format, `controls`, `ref` — `docs/specs/remotion-integration.md` §2.4); import cùng package composition với worker; scrub dùng `playerRef.current.seekTo(frame)`, progress dùng `addEventListener('frameupdate', ...)`; **2 composition riêng trong `Root.tsx`** ([patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)): `Scene` (1 cảnh — dùng ở Phân cảnh 5-1 + render-worker) và `Video` (nối toàn bộ cảnh qua `<Sequence>` + `<Audio>` BGM — chỉ dùng ở Player Hoàn thiện 5-5, KHÔNG bao giờ render thật); lazy-load + skeleton; chế độ frame tĩnh (thumbnail cho 5-1, dùng `seekTo` + capture).
**Out:** editor form (5-1); audio waveform (không cần v1).

## Business Rules
1. Props đổi → re-render ngay (key theo content hash), không giữ state cũ.
2. Chưa có audio produce → phát hình không tiếng + hint; có audio → phát đồng bộ.
3. Bundle Remotion lazy — route không cần preview không tải chunk này.

## Acceptance Criteria
1. **(happy)** Sửa scene JSON state → player cập nhật <100ms không network call.
2. **(biên/BR-2)** Cảnh chưa produce → im lặng + hint; sau produce → có tiếng đúng timing.
3. **(nhất quán)** 1 frame giữa: player vs render CLI cùng scene giống nhau (kiểm tay, ghi vào PR).
4. **(perf/BR-3)** Trang Dashboard không tải remotion chunk (kiểm network).
5. **(lỗi)** Composition throw → error state có mã, app không crash (error boundary).

## Decisions already locked
- Preview "cả video" ở màn Hoàn thiện dùng Player nối cảnh — chấp nhận transition xấp xỉ (transition thật chỉ trong render thật); UI ghi rõ "bản xem thử".

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + vitest component với fixture 2-1; kiểm bundle bằng next build analyze trong PR đầu. PR states which Remotion Skill was invoked.
