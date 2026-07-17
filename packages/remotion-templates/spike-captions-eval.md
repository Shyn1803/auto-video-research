# Spike: `@remotion/captions` vs scene-json-schema.md §3.6 constraints (task 2-5)

**Decision: do not use `@remotion/captions`. Use a custom segmentation algorithm.**

## Why

`@remotion/captions`'s `createTikTokStyleCaptions` groups word-level timestamps
into caption pages purely by a `combineTokensWithinMilliseconds` window and a
line-count/character heuristic — it has no concept of "never split a semantic
cluster" (a number + its unit, e.g. Vietnamese `"92,5 phần trăm"`). Its grouping
is duration-driven, not text-boundary-driven, so it cannot express BR-1
(`docs/backlog/stories` task 2-5): "Không tách cụm số+đơn vị."

Since the TTS adapter (`2-4`, `docs/specs/scene-json-schema.md` §3.4) emits
per-word timestamps (`{ word, start_ms, end_ms }`), a number like "92,5" and its
unit "phần trăm" are already separate word tokens by the time they reach
subtitle generation — nothing downstream of the TTS adapter carries a
"these words are one semantic unit" flag. `@remotion/captions` has no hook to
inject that constraint into its grouping pass, and forcing it via post-processing
would mean re-deriving segment boundaries anyway, at which point the package
adds indirection without adding value.

**Package was not installed** (`packages/remotion-templates/package.json` has no
`@remotion/captions` dependency) — this decision was made analytically against
its documented grouping algorithm rather than via a live spike script, since the
gap (semantic-cluster splitting) is structural to the package's design, not an
edge case that needs empirical reproduction. Per task 2-5 Step 1's instruction,
this is "an expected decision outcome" (not a failure) — recorded here per the
task file's requirement, proceeding to Step 2's custom algorithm.

## Outcome

Custom algorithm implemented at
`packages/remotion-templates/src/subtitle/segmentTimestamps.ts`, covering all
four Business Rules from task 2-5:

1. BR-1: number+unit clusters kept in one segment (best-effort heuristic: a
   token matching `/^[0-9][0-9.,]*$/` is never split from the following token).
2. BR-2: any segment with total display duration < 700ms is merged into the
   next segment.
3. BR-3: `subtitle.enabled=false` handled at the component layer
   (`Subtitle.tsx`) — segmentation itself is unaffected, no special case needed
   here.
4. BR-4: a single token longer than 42 chars is allowed to overflow its own
   segment rather than being cut mid-word.
