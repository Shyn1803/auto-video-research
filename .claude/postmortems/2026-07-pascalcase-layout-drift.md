# Postmortem: PascalCase Layout-Name Drift

**Date:** 2026-07 · **Files affected:** SRS.md, scene-json-schema.md, prompts.md, glossary.md, layout-engine.md (9 locations total) · **Risk level:** medium

## Issue
The Layout Engine architecture (ADR-0008) mandates 11 canonical PascalCase layout class names. During iterative doc updates, 9 locations across the spec docs still referenced the older snake_case names (`title_card`, `full_text`, `image_full`, `image_text`, `split_compare`, `big_number`, `chart_bar`, `versus_table`, `bullet_list`, `code_snippet`), and `SRS.md` FR-07 literally listed "Camera, Transition, Animation" as AI-decided fields — a direct contradiction of the "AI never chooses layout" principle stated elsewhere in the same document set.

## Impact
Had this drift persisted into implementation, it would have produced code that string-matches inconsistent layout names against the Classifier's actual output enum, silently breaking preset lookups and the anti-repetition post-pass's "same class" counting.

## Root Cause
Documentation was updated in the direction of the new architecture in some files but not propagated everywhere the concept was mentioned — no single source of truth was checked exhaustively before considering the change "done."

## Fix
Explicit self-audit requested by the user ("did you actually implement 'AI doesn't choose layout' everywhere?") — grep'd exhaustively for all old names and the contradictory FR-07 wording, fixed all 9 occurrences, standardized on PascalCase everywhere, rewrote FR-07/FR-08.

## Lessons Learned
A principle stated in one prominent place (an ADR, a "nguyên tắc" section) is not automatically true everywhere else in the doc set — verify by exhaustive search, not by memory of "I think I updated that."

## Prevention
[anti-patterns/layout-name-drift.md](../anti-patterns/layout-name-drift.md) documents the detection grep. [rules/naming.md](../rules/naming.md) states the canonical names explicitly.

## Regression Test
N/A (documentation, pre-code). Once code exists: a lint rule or enum-exhaustiveness check that rejects any layout-class string literal not in the canonical set.
