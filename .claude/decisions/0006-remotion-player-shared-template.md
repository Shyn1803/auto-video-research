# ADR-0006: Remotion Player Shares Template Package with Render Worker

**Status:** Accepted · **Date:** design phase (docs v1.0)

## Context
If the browser preview and the server render use different template implementations, they will eventually drift pixel-for-pixel, and users will see a preview that doesn't match the final render — a trust-breaking bug class.

## Decision
`packages/remotion-templates/` is a shared monorepo package imported by both the Next.js frontend (`<Player>`) and the Node.js `render-worker` (`renderMedia()`). Same composition code renders what was previewed.

## Alternatives Considered
1. Separate preview renderer (e.g., a simplified CSS-based preview) vs. full Remotion render — rejected: guarantees preview/render mismatch.
2. Duplicate the template code in both frontend and worker repos — rejected: guaranteed drift over time, double maintenance.

## Tradeoffs
Gain: preview literally equals render, no separate QA burden for "does preview match reality." Give up: introduces a JS/TS monorepo package alongside the Python backend — one more thing to version/build.

## Consequences
Any primitive/preset/motion change is made once in `packages/remotion-templates/` and both consumers pick it up.

## Future Considerations
None currently — this is a stable structural choice underpinning the whole preview/render trust model.
