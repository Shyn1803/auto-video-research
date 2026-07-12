# Postmortem: `renderMedia()` Merge Ambiguity

**Date:** 2026-07 · **Files affected:** docs/specs/remotion-integration.md §2.5 · **Risk level:** medium

## Issue
While answering a question about how Remotion integrates into the runtime auto-generation flow, a re-read of the existing spec found the wording "`renderMedia()` — 1 lần/job (scene hoặc merge)" ("once per job — scene or merge") — ambiguously implying that the video-merge step might also be implemented as a Remotion `renderMedia()` call, when the actual intended design uses ffmpeg for merging (concat + BGM mix + encode), never a second Remotion render.

## Impact
Had this ambiguity survived into implementation without clarification, a developer could plausibly have built a whole-video `renderMedia()` path for the merge step — which would silently defeat the per-scene render caching architecture (any single-scene edit would force a full-video re-render).

## Root Cause
No document had ever explicitly defined that there are two distinct Remotion compositions (`Scene`, one rendered; `Video`, preview-only) — the ambiguous phrase was a symptom of that missing definition, not the root problem itself.

## Fix
Defined the `Scene`/`Video` composition split explicitly in a new §4 of remotion-integration.md, fixed the ambiguous §2.5 line to state final render only ever targets the `Scene` composition, and formalized the decision as [ADR-0009](../decisions/0009-scene-video-two-compositions.md).

## Lessons Learned
An ambiguous sentence in a spec is often a symptom of an undefined concept, not just a wording problem — fixing the sentence without defining the missing concept would have left the same ambiguity latent elsewhere.

## Prevention
[patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md) makes the split explicit and reusable. [rules/performance.md](../rules/performance.md) states the "never call renderMedia() on the whole-video composition" rule directly.

## Regression Test
N/A (documentation, pre-code). Once code exists: an integration test asserting the render-worker's render call always targets the `Scene` composition id, never `Video`.
