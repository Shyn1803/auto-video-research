# ADR-0008: Layout Engine — AI Generates Semantic Only

**Status:** Accepted · **Date:** design phase (docs v1.0), reaffirmed via explicit self-audit

## Context
Letting the AI directly choose layout/position/font/animation makes visual output non-deterministic and expensive to regenerate for format/theme changes, untestable, and prone to repetitive "mass-produced" output that risks platform reach penalties.

## Decision
AI produces only a Semantic Storyboard (content + intent: `purpose`, `narration`, `components` by `kind`, plus `beat`/`narration_anchor` signal fields). A deterministic pipeline — Scene Tree → Semantic Analysis → Layout Classifier → Constraint Resolver → Responsive Solver → Theme Engine → Motion Planner — resolves everything visual, with zero further LLM calls.

## Alternatives Considered
1. Single LLM call producing full Scene JSON incl. layout — rejected: the core problem this ADR solves; considered and explicitly ruled out.
2. LLM chooses from a small fixed template list — rejected: still non-deterministic, still can't cheaply adapt to format/theme changes, still caps visual variety artificially.
3. Constraint solver where components declare needs and a general solver places them (Figma Auto-Layout style) — accepted as the v1.1+ roadmap item once the fixed preset-per-class approach (v1) proves insufficient for >~15 classes/variants.

## Tradeoffs
Gain: deterministic, testable, cheap format/theme changes, engine-level anti-repetition guarantees. Give up: v1's preset-per-class Constraint Resolver is less flexible than a general solver — accepted as a deliberate scope boundary, not an oversight.

## Consequences
See [patterns/layout-engine-resolution.md](../patterns/layout-engine-resolution.md) and [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md). This is the single most-enforced architectural rule in the project — violated once during design (documentation drift, not code) and caught via explicit self-audit.

## Future Considerations
Move to a general constraint solver (v1.1+) once the fixed-preset catalog (11 classes) becomes a demonstrated bottleneck to visual variety, not before.
