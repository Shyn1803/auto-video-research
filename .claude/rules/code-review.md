# Rule: Code Review

See [agents/reviewer.md](../agents/reviewer.md) for the review agent's mission; this is the checklist reviewers apply.

- Reject any AI/LLM-produced output that includes a layout, position, font, animation, camera, or transition field — that's a Layout Engine violation, not a nitpick (see [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md)).
- Reject a schema/contract change without a semver bump + migration note.
- Reject a new provider integration that bypasses the adapter pattern (direct API call from business logic).
- Reject a Remotion `<Sequence>` wrapping flex-preset content without `layout="none"` — silently breaks the constraint layout (patterns/scene-video-composition-split.md).
- A review comment that recurs across 2+ PRs gets promoted to a rule or checklist item, not repeated manually forever — see [knowledge-curator agent](../agents/knowledge-curator.md).
