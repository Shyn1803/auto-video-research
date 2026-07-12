# Remotion Integration — API thật & Agent Skills

**Version:** 1.0 · Neo [layout-engine.md](layout-engine.md) vào đúng API của Remotion (docs chính thức) + cài đặt Remotion Agent Skills cho giai đoạn code.
**Khác với video-taste.md:** file đó là "gu thẩm mỹ" (số liệu motion/theme); file này là "cách gọi đúng API Remotion" + công cụ hỗ trợ agent lúc implement.

---

## 0. Phạm vi: Dev-time, KHÔNG phải Runtime

**Toàn bộ tài liệu này nói về lúc VIẾT CODE (dev-time)** — người hoặc coding agent (Claude Code, Cursor...) đang tạo `SceneRenderer.tsx`, render-worker, primitives. Skill (`SKILL.md`) chỉ có ý nghĩa ở đây vì cần **tool access** để agent tự đọc file và quyết invoke.

**Không liên quan tới Runtime** — lúc hệ thống thật sự chạy, các LLM node (research/factcheck/storyboard...) gọi provider (Ollama/Gemini/Groq/OpenRouter) qua **HTTP API + key thuần tuý** (FR-18/FR-21, [CONFIGURATION.md](../CONFIGURATION.md)). Một API call chat/completion **không có tool access** — không thể đọc `SKILL.md`, không thể "invoke skill" dù cấu hình thế nào. Prompt storyboard ([prompts.md](prompts.md) §7) là text thuần render qua Jinja2 gửi qua HTTP, không hề biết Remotion Agent Skills tồn tại.

Điều này **củng cố** chứ không mâu thuẫn với nguyên tắc "AI không quyết layout" (SRS §10): LLM runtime không có khả năng kỹ thuật để chạm vào code/layout dù muốn — Layout Engine (Classifier + preset resolver, code deterministic, layout-engine.md) là thứ duy nhất quyết bố cục, viết ra đúng 1 lần lúc dev-time (có hoặc không có skill hỗ trợ).

---

# 1. Remotion Agent Skills — cài lúc code, không chỉ đọc lúc viết spec

Remotion duy trì bộ **Claude/Codex/Cursor Agent Skills** chính thức tại `remotion-dev/skills` (dùng chuẩn `npx skills add` — cùng cơ chế phân phối như `taste-skill`, nhưng đây là skill **chính chủ Remotion**, không phải chuyển thể).

```bash
npx skills add remotion-dev/skills
```

**Cài vào lúc nào:** story 1.1 (khởi tạo monorepo) — thêm vào Task, chạy trong `packages/remotion-templates/`.

**Cơ chế & bảng trigger mức-task (không phải mức-story):** đây là file `SKILL.md` thuần — agent tự đọc `description`, nạp nội dung nếu khớp việc đang làm, **trước khi viết code**; không có API, không tự động chạy qua CI. Bảng trigger chính thức + Definition of Done kiểm chứng được: [dev-guide.md](../dev-guide.md) §2.1 (nguồn duy nhất — không lặp lại bảng ở đây để tránh lệch khi sửa).

`mediabunny` (xử lý multimedia browser-based, metadata video/audio) — cân nhắc dùng ở 6.1 (asset resolve) thay ffmpeg tay ở vài chỗ; chưa đưa vào bảng trigger chính vì cần đánh giá trước khi cam kết.

# 2. Map kiến trúc Layout Engine → API Remotion thật

## 2.1 SceneRenderer = `<Composition>` + `calculateMetadata` (không phải 11 composition cứng)

```tsx
// Root.tsx
<Composition
  id="Scene"
  component={SceneRenderer}
  schema={sceneJsonSchema}          // Zod — CHÍNH LÀ cơ chế input-props chuẩn của Remotion (docs "Schemas"),
                                     // không phải lựa chọn tuỳ ý của ta — scene-json-schema.md đã đúng hướng
  calculateMetadata={async ({props}) => ({
    durationInFrames: msToFrames(props.duration_ms, FPS),
    fps: FPS,
    width:  props.format === 'vertical_1080x1920' ? 1080 : 1920,
    height: props.format === 'vertical_1080x1920' ? 1920 : 1080,
  })}
/>
```

`calculateMetadata` là cơ chế **chính thức** cho "1 scene JSON → resolve ra kích thước/độ dài khác theo format" (Responsive Solver §7 layout-engine) — không cần tự chế logic ngoài Remotion.

## 2.2 MotionPlan tracks = `<Sequence from durationInFrames layout="none">`

```tsx
function SceneRenderer({layout, background, elements, motion_plan}: SceneJSON) {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={PRESETS[layout].container}>
      <Background {...background} />
      {motion_plan.tracks.map(track => (
        <Sequence key={track.component_id}
          from={msToFrames(track.enter_at_ms, fps)}
          durationInFrames={Infinity}   // ở lại tới hết cảnh trừ khi có exit riêng
          layout="none">                 {/* preset flex tự định vị, không dùng AbsoluteFill mặc định của Sequence */}
          <Animated track={track}>
            <PrimitiveFor kind={...} />
          </Animated>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
```

`layout="none"` là bắt buộc — mặc định Sequence bọc `AbsoluteFill` (chồng đè), trong khi preset flex (layout-engine §6) cần tự kiểm soát vị trí trong slot.

## 2.3 `Animated` wrapper = `interpolate()` + `spring()` — video-taste.md số liệu cắm thẳng vào

```tsx
function Animated({track, children}: {track: MotionTrack; children: ReactNode}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (track.preset === 'countUp' || track.preset === 'pulse') {
    const s = spring({frame, fps, config: {stiffness: 100, damping: 20}}); // video-taste.md §3, khớp thẳng API spring()
    return <div style={{transform: `scale(${s})`}}>{children}</div>;
  }
  const opacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'}); // ease cubic-bezier(0.16,1,.3,1) qua Easing.bezier
  return <div style={{opacity}}>{children}</div>;
}
```

`spring({config:{stiffness, damping}})` **là chính API Remotion** — con số `stiffness:100 damping:20` từ video-taste.md (gốc taste-skill/GSAP) cắm thẳng vào, không cần dịch.

## 2.4 Player (Story 2.3) — props/API thật thay mô tả chung chung trước đây

```tsx
<Player
  component={SceneRenderer}
  inputProps={sceneJson}            // = props hiện tại trong editor state
  durationInFrames={durationFrames}
  fps={FPS}
  compositionWidth={format === 'vertical_1080x1920' ? 1080 : 1920}
  compositionHeight={...}
  controls
  ref={playerRef}                   // imperative: playerRef.current.seekTo(frame), .play(), .pause()
/>
```

`playerRef.addEventListener('frameupdate', ...)` thay cho việc tự viết cơ chế theo dõi tiến độ play trong 2.3/5.5 — dùng thẳng event system của Player.

## 2.5 Render Worker (Story 6.2, 9.2) — pipeline 3 bước chính thức, sửa 1 giả định quan trọng

```
bundle()            — build 1 lần, CACHE lại (không bundle mỗi job — sai giả định cũ)
   ↓
selectComposition() — lấy metadata đã resolve (calculateMetadata chạy ở đây)
   ↓
renderMedia()        — 1 lần/CẢNH (composition "Scene"), nhận inputProps = Scene JSON đã resolve
                        KHÔNG dùng cho bước merge — merge là ffmpeg (§4.3), không phải renderMedia() lần 2
```

**Sửa quan trọng cho story 6.2/9.2:** `bundle()` tốn vài giây — worker phải **bundle 1 lần lúc khởi động, cache serveUrl, tái dùng cho mọi job** sau đó (không bundle lại mỗi render). Thiết kế cũ (6.2 Scope) chưa nói rõ điều này — bổ sung ở §3.

---

# 4. Luồng runtime end-to-end — Remotion cắm vào đâu khi hệ thống tự generate video

Đây là câu trả lời trực tiếp cho "tích hợp Remotion khi hệ thống tự generate video và animation": ghép layout-engine.md (đã thiết kế) + API thật (§2) thành **một luồng liền mạch**, chỉ rõ 2 điểm chạm Remotion runtime — không có điểm thứ ba nào khác.

```
[LLM qua API — HTTP+key, KHÔNG Remotion, KHÔNG skill — §0]
  storyboard.generate → Semantic Storyboard (purpose/narration/components, KHÔNG layout/animation)
        │
        ▼
[Layout Engine — code deterministic, KHÔNG LLM — layout-engine.md §4.6]
  Scene Tree → Semantic Analysis → Classifier → Constraint Resolver → Motion Planner PASS-1
  (duration ước lượng từ tốc độ đọc trung bình — CHƯA có timestamps thật)
        │
        ▼ Scene JSON (draft) lưu step_versions.scene_set
        │
        ├──────────────► ĐIỂM CHẠM REMOTION #1: <Player> trong browser (story 2.3)
        │                 User mở màn Phân cảnh/Hoàn thiện → Player load composition "Scene"
        │                 (hoặc "Video" khi xem cả video) với inputProps = Scene JSON hiện tại.
        │                 KHÔNG render file — chỉ playback trong browser. Sửa 1 field → Player
        │                 nhận props mới → hiện ngay (<100ms). Đây là "preview tức thì" NFR-1.
        │
        ▼ user duyệt từng cảnh (5.1) → sang Hoàn thiện
        │
[Produce node — TTS + asset, story 6.1]
  Word timestamps thật từ TTS → Motion Planner PASS-2 (§9.4 layout-engine)
  re-resolve motion_plan bằng timestamps thật — layout KHÔNG đổi, chỉ motion_plan cập nhật
        │
        ▼ Scene JSON (final) — cache_key tính trên JSON này
        │
        ▼ user bấm "Tạo video" (story 6.2)
        │
[Render Worker — Node.js, story 6.2/9.2]
  bundle() 1 lần lúc khởi động (cache serveUrl) ─── ĐIỂM CHẠM REMOTION #2 (server-side, thật sự render)
        │
        ▼ với MỖI cảnh dirty (cache miss):
        selectComposition("Scene", inputProps=sceneJSON) → renderMedia() → {cache_key}.mp4 vào MinIO
        (cảnh cache hit: bỏ qua, dùng file cũ — glossary "mỗi Scene là đơn vị render độc lập")
        │
        ▼ khi 100% cảnh done (renders bảng — story 6.2 BR-3)
[ffmpeg — KHÔNG phải Remotion]
  concat N file mp4 theo thứ tự + mix BGM (volume/fade) + encode CRF → video hoàn chỉnh
        │
        ▼
  videos/{project}/{version}/{format}.mp4 → user tải/xem (story 6.3) / publish (8.x)
```

## 4.1 Hai composition trong `Root.tsx`, hai mục đích khác nhau (chưa từng nói rõ — bổ sung ở đây)

```tsx
<Composition id="Scene" component={SceneRenderer} schema={sceneJsonSchema} calculateMetadata={...} />
<Composition id="Video" component={VideoRenderer} schema={videoProjectSchema} calculateMetadata={...} />
// VideoRenderer = nhiều <Sequence from={cumulativeMs}> mỗi cái bọc <SceneRenderer scene={...}/> + <Audio src={bgm}/>
```

| Composition | Dùng bởi | Mục đích | Render thật (renderMedia) không? |
|---|---|---|---|
| `Scene` | `<Player>` trong editor (per-cảnh) **và** Render Worker | Preview 1 cảnh; render-worker render **từng cảnh riêng** để cache theo `cache_key` | **Có** — đây là composition duy nhất render-worker gọi |
| `Video` | `<Player>` trong màn Hoàn thiện, nút "Xem thử toàn bộ" (story 5.5) | Preview cả video nối cảnh trong browser — xem transition/nhịp tổng thể | **Không** — chỉ dùng cho Player; final render vẫn là N lần `Scene` + ffmpeg concat, không phải 1 lần `Video` |

**Vì sao không render thẳng bằng composition `Video`** (dù kỹ thuật làm được, gọn hơn): sẽ mất khả năng cache từng cảnh (ADR #4/#3 — "mỗi Scene là đơn vị độc lập để preview, cache, render riêng"). Nếu render cả video trong 1 lần `renderMedia()`, sửa 1 cảnh giữa video buộc render lại toàn bộ timeline. Việc `Video` chỉ tồn tại cho Player là đánh đổi có chủ đích: browser preview chấp nhận xấp xỉ (transition không hoàn hảo 100%, đã ghi "quyết định đã chốt" ở story 2.3), đổi lại giữ được cache per-scene cho bước render thật — nơi thời gian/chi phí mới thực sự quan trọng.

## 4.2 Hai điểm chạm Remotion runtime — không có điểm thứ ba

1. **Browser (`<Player>`)** — mọi lần user sửa scene trong editor. Không sinh file, không tốn compute server, không liên quan render-worker.
2. **Server (`renderMedia()` trong render-worker)** — chỉ khi user bấm "Tạo video" (hoặc Mode 1 tự động tới bước Render). Đây là nơi Remotion thật sự "generate" ra file MP4.

LLM (research/factcheck/storyboard/script) **không phải điểm chạm Remotion** — nó dừng ở việc tạo Scene JSON draft (chưa có video, chỉ có dữ liệu). Layout Engine (deterministic, không LLM) mới là cầu nối biến dữ liệu đó thành thứ Remotion hiểu được (props đúng schema).

## 4.3 Vai trò ffmpeg — bổ trợ Remotion, không thay thế

Remotion render **từng cảnh** (có audio/subtitle/animation trong cảnh đó). ffmpeg chỉ làm 2 việc Remotion không làm trong kiến trúc này: **nối N file mp4** theo thứ tự và **mix nhạc nền xuyên suốt video** (BGM không thuộc về 1 cảnh cụ thể). Không dùng ffmpeg để render animation hay xử lý nội dung — việc đó 100% là Remotion.

# 5. Sửa backlog theo phát hiện (bao gồm §4)

| Story | Sửa |
|---|---|
| 1.1 | +Task: cài `npx skills add remotion-dev/skills` trong `packages/remotion-templates/` |
| 2.1 | Ghi rõ Zod ở đây = schema prop của `<Composition>` (Remotion-native), không phải lựa chọn tuỳ ý |
| 2.2 | SceneRenderer dùng `calculateMetadata` (không tự viết logic resolve size/duration ngoài Remotion) |
| 2.3 | Player props/ref/event đúng API thật; scrub dùng `seekTo`, progress dùng `addEventListener('frameupdate')` |
| 2.5 | Kiểm tra `@remotion/captions` trước khi tự viết thuật toán nhóm segment (BR-1/2/4 giữ nếu package không khớp) |
| 6.2 | **+BR mới: worker bundle() 1 lần lúc khởi động, cache serveUrl** — không bundle mỗi job (perf quan trọng, ảnh hưởng benchmark 6.4); render-worker chỉ gọi composition `Scene`, không bao giờ gọi `Video` (§4.1) |
| 9.2 | Worker replicas mỗi cái tự bundle 1 lần khi container start (không share bundle qua network — mỗi worker instance độc lập) |
| 2.3 | +Task: định nghĩa 2 composition `Scene`/`Video` trong `Root.tsx` (§4.1); Player màn Hoàn thiện (5.5) dùng `Video`, Player màn Phân cảnh (5.1) dùng `Scene` |
