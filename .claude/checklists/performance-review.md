# Checklist: Performance Review

- [ ] Cache-key logic (`sha256(canonical_scene_json + template_version + format)`) unaffected or correctly updated
- [ ] `bundle()` still called once per worker replica at startup, not per job
- [ ] Final render still targets only the `Scene` composition, per-scene — never whole-video `renderMedia()`
- [ ] LLM calls declare correct `tier` (`cheap`/`strong`/`embedding`)
- [ ] High-volume table changes include partitioning consideration
- [ ] Benchmark taken before/after for any claimed performance fix
