# ADR-0009: Two Remotion Compositions — Scene vs Video

**Status:** Accepted · **Date:** surfaced during runtime-integration deep-dive, formalized here

## Context
The editor needs three different things from the same Scene JSON: instant per-scene preview while editing, a "preview the whole thing" view before finalizing, and the actual server-side render. Per-scene render caching (`cache_key` on scene hash) is central to this system's performance model — if the final render were one `renderMedia()` call over a whole-video composition, editing one scene would force re-rendering the entire video, defeating that cache.

## Decision
Define exactly two compositions in `packages/remotion-templates`' `Root.tsx`:
- **`Scene`** — one scene. Used by the browser `<Player>` (Phân cảnh screen) for live per-scene preview, and by the render-worker — this is the only composition ever passed to `renderMedia()`.
- **`Video`** — all scenes nested via `<Sequence>` + a BGM `<Audio>` track. Used only by the browser `<Player>` on the Hoàn thiện (Finishing) screen for "preview all." Never rendered server-side.

Final video assembly is ffmpeg's job (concat the independently-rendered per-scene MP4s + mix BGM + encode) — not a second Remotion render pass.

## Alternatives Considered
1. One `Video` composition rendered whole via `renderMedia()` — rejected: destroys per-scene cache, forces full re-render on any single-scene edit.
2. No `Video` composition at all, whole-video preview stitched client-side from N separate `<Player>` instances — rejected: significantly more complex client-side sequencing/audio-sync logic for no caching benefit, since it's preview-only anyway.

## Tradeoffs
Gain: per-scene cache stays intact at render time; "preview all" still available without extra render cost (it's just the Player interpreting the same Scene JSONs). Give up: two composition definitions to maintain, and Player-preview of the whole video is only an approximation of the true final output (true output requires the ffmpeg merge step) — acceptable since Player preview was already approximate pre-render (audio/timing finalized only after `produce`).

## Consequences
See [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md). Story 2.3 (Player integration) and 6.2 (render orchestrator) both reference this split explicitly.

## Future Considerations
None currently — this directly follows from the pre-existing "each scene is an independent unit: preview, cache, render" principle (SRS §10), just made explicit at the Remotion-composition level.
