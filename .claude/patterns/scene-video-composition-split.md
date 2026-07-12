# Pattern: Scene / Video Composition Split

**Problem:** the system needs three different Remotion use-cases from one Scene JSON contract — live per-scene preview in the editor, live whole-video preview for "xem thử toàn bộ," and the actual server-side render — but per-scene render caching requires each scene to be rendered independently, so a single whole-video `renderMedia()` call would defeat that cache on every single-scene edit.

**Solution (`docs/specs/remotion-integration.md` §4.1):** define exactly two Remotion compositions in `Root.tsx`:

| Composition | Contains | Used by | Ever rendered via `renderMedia()`? |
|---|---|---|---|
| `Scene` | 1 scene | Browser `<Player>` (Phân cảnh screen) **and** render-worker | **Yes — the only composition ever actually rendered to file** |
| `Video` | all scenes via `<Sequence>` + `<Audio>` BGM track | Browser `<Player>` only (Hoàn thiện screen, "preview all") | **No, never** |

**Rules:**
- Final render always renders `Scene`, once per scene, in parallel across the worker pool. Merging into the final video is ffmpeg's job (concat + BGM mix + encode), not a second Remotion render.
- `<Sequence>` wrapping flex-preset content must set `layout="none"` — the default wraps content in `AbsoluteFill`, which breaks the Constraint Resolver's flex presets.
- There are exactly two Remotion runtime touchpoints: browser `<Player>` (preview only, no file output) and server `renderMedia()` (real file output). An LLM call is never a Remotion touchpoint — it only produces Scene JSON draft data via plain HTTP.

**When to use:** any time you're deciding which composition a new UI surface or render job should target. If it's a real file output, it's `Scene`. If it's "show the user roughly what this will look like end to end," it's `Video`, browser-only.

**Origin:** this split wasn't in the initial design — it was defined explicitly after a review found the runtime integration doc had never stated it, and an ambiguous phrase ("renderMedia() — 1 lần/job scene hoặc merge") implied merge might also be a Remotion call. See [postmortems/2026-07-rendermedia-merge-ambiguity.md](../postmortems/2026-07-rendermedia-merge-ambiguity.md).
