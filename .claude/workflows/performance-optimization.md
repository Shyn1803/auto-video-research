# Workflow: Performance Optimization

**Inputs:** a measured performance problem (not a guess) — benchmark, dashboard alert, or user-reported latency.

**Steps**
1. Performance Engineer agent measures before touching anything — establish baseline against the NFR targets in `docs/SRS.md` §8.
2. Check the cheap levers first: cache hit rate (`cache_key` logic), worker replica count, LLM tier routing correctness — before algorithmic rewrites.
3. Verify `bundle()` caching and per-scene render caching aren't silently defeated (common failure modes for this system — see [rules/performance.md](../rules/performance.md)).
4. Apply the fix, re-measure against the same baseline.
5. Update the NFR number in `docs/SRS.md` §8 if the real, benchmarked number diverges — with user sign-off, don't let the doc go stale.

**Quality Gates:** before/after measurement exists; fix targets the actual bottleneck, not a guessed one.

**Outputs:** optimization PR + benchmark notes.

**Success Criteria:** measured improvement against the specific NFR target, not just "feels faster."
