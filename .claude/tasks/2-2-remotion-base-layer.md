# Task 2-2: Remotion base layer — SceneRenderer + primitives + 5 preset cơ bản + theme

**Points:** 5đ · **Epic:** 2 — Scene JSON + Remotion · **Depends:** 2-1 · **FR:** FR-08, FR-11

## User story
As a viewer, I want video có bố cục đẹp nhất quán trên cả khung dọc lẫn ngang, so that nội dung trông chuyên nghiệp trên mọi nền tảng.

## Why
Tầng hiện thực Remotion của Layout Engine — [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md): **không có composition cứng per-layout**, chỉ 1 `SceneRenderer` đọc preset (data). **Invoke Remotion Agent Skill `/remotion-markup` before writing** (dev-guide.md §2.1).

## Scope
**In:** `SceneRenderer` = `<Composition>` thật của Remotion với `schema` (Zod, 2-1) + `calculateMetadata` resolve width/height/durationInFrames động (`docs/specs/remotion-integration.md` §2.1); mỗi track MotionPlan render bằng `<Sequence from={ms→frames} durationInFrames layout="none">` (bắt buộc `layout="none"` — mặc định Sequence bọc AbsoluteFill phá preset flex); primitives cơ bản `Heading/Body/Media(kenburns)/Subtitle/Watermark` (`**bold**` → highlight); `motion/Animated` wrapper dùng `interpolate()`/`spring()` thật + bảng preset khởi điểm; `ThemeProvider` + theme mặc định; **5 preset json** Hero/TextFocus/MediaFull/MediaText/Comparison (mỗi preset × 2 format); `supportedSchemaRange`; render CLI; render test class×format + golden-frame.
**Out:** primitives dữ liệu + 6 preset + motion đặc thù (2-6); theme 2-3 (10-2); transition ngoài enum v1; watermark/intro-outro tuỳ chỉnh (v1.1).

## Business Rules
1. Template không fetch mạng — mọi media là đường dẫn cục bộ trong props (see [anti-patterns/render-worker-external-fetch.md](../anti-patterns/render-worker-external-fetch.md)).
2. Text tràn → auto-shrink tới 60% cỡ gốc rồi ellipsis — không bao giờ vỡ khung.
3. Scene ngoài schema range → throw mã `SCHEMA_RANGE`, không render-sai-lặng-lẽ.
4. Font nhúng trong package (Inter + font Việt fallback) — render không phụ thuộc font hệ thống.
5. Mỗi layout = constraint preset flexbox dạng data (slots/gap/padding), không toạ độ tuyệt đối; thêm class mới = thêm preset json — SceneRenderer không đổi.
6. Primitive không biết layout — chỉ render nội dung + motion trong slot; mọi animation qua `Animated` wrapper.
7. Ease mặc định `cubic-bezier(0.16,1,0.3,1)`; duration entrance 450–600ms (dial 4-7 mặc định); theme khai `motion_intensity`/`visual_density` — `Animated` đọc dial để scale duration.

## Acceptance Criteria
1. **(happy)** Fixture mỗi layout render 2 format: đúng resolution, duration ±100ms; PO duyệt visual (10 ảnh trong PR).
2. **(biên/BR-2)** Heading 200 ký tự → shrink+ellipsis không tràn (snapshot test).
3. **(biên)** Cùng scene 9:16 vs 16:9 → bố cục responsive đúng thiết kế từng layout.
4. **(lỗi/BR-3)** Scene 2.0.0 vào template ^1.0 → lỗi SCHEMA_RANGE.
5. **(BR-4)** Render trong container sạch không font hệ thống → chữ Việt đúng (có dấu).

## Decisions already locked
- ⏳ Đếm số cho `stat` chỉ khi content là số thuần — text lẫn số thì hiện tĩnh.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + render test CI 1 layout×1 format/PR (nhanh), đủ 10 tổ hợp nightly; baseline screenshot cho visual regression. PR states which Remotion Skill was invoked.
