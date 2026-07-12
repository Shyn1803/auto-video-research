# Rule: Performance

- Per-scene render caching is load-bearing: `cache_key = sha256(canonical_scene_json + template_version + format)`. A cache-key computation bug silently defeats the entire caching architecture — treat changes to cache-key logic as high-risk.
- `bundle()` (Remotion) is called once per render-worker replica at startup and the `serveUrl` cached in memory — never re-bundle per job. This was a real design gap caught before implementation (see [postmortems/](../postmortems/)) — don't reintroduce it.
- Final render only ever renders the `Scene` composition, per scene, in parallel across the worker pool. Never call `renderMedia()` on a whole-video composition — that defeats per-scene caching (see [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md)).
- LLM calls declare a `tier` (`cheap`/`strong`/`embedding`) — routing cheap tasks (dedupe, ranking, claim extraction) through a strong-tier chain wastes cost/latency budget.
- High-volume tables (`llm_usage`, `schedule_runs`, `metrics`) are partitioned by month from the first migration, not retrofitted later.
- Scale render/voice/asset workers horizontally via replica count before optimizing single-worker throughput.
