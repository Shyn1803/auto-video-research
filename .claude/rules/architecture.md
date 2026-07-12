# Rule: Architecture

- Services split only when a measured bottleneck exists (queue depth, latency data) — "tách theo đo đạc, không tách trước" (ARCHITECTURE.md ADR #1). Don't pre-split speculatively.
- Every module/node interface is a Pydantic model from day one, even in the Phase 1 monolith — this is what makes Phase 2/3 extraction to NATS events a non-breaking change (ARCHITECTURE.md §2.1, §7).
- All external capability access goes through an adapter (`app/adapters/{capability}/{provider}.py`) — see [patterns/provider-adapter.md](../patterns/provider-adapter.md). No business-logic module calls a provider SDK/HTTP API directly.
- The Layout Engine boundary is architectural law, not a style preference: AI produces Semantic Storyboard only; everything from Scene Tree onward is deterministic. See [context/architecture.md](../context/architecture.md).
- New architectural decisions get an ADR in [decisions/](../decisions/) using [templates/adr.md](../templates/adr.md) — don't let a significant tradeoff live only in a PR description or chat log.
