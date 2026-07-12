# Prompt: Performance Analysis

```
Analyze this component against docs/SRS.md §8 NFR-Performance targets.
Check the cheap levers first, in this order:
1. Cache hit rate — is cache_key (scene_json + template_version + format) computed correctly and consistently?
2. bundle() caching — is Remotion bundle() re-run per job instead of once per worker replica at startup?
3. LLM tier routing — is a cheap task (dedupe/ranking/claim-extraction) routed through a strong-tier chain?
4. Worker replica count vs. queue depth.
Only after ruling these out, look for algorithmic bottlenecks.
Report baseline measurement, proposed fix, expected measured improvement.
```
