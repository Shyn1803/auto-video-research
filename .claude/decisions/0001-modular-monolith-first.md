# ADR-0001: Modular Monolith Before Service Split

**Status:** Accepted · **Date:** design phase (docs v1.0)

## Context
The target architecture is multi-agent over NATS JetStream, but building that from day one means heavy infrastructure (message bus, per-agent deployment, distributed tracing) before there's any real load to justify it.

## Decision
Build Phase 1 as a modular monolith — every "agent" is a module in one FastAPI codebase, orchestrated by LangGraph. Every module interface is a Pydantic model from day one, which becomes the event payload schema when a module is extracted in Phase 2/3.

## Alternatives Considered
1. Full microservices from day one — rejected: infra overhead with no load to justify it, slower iteration.
2. No plan for splitting at all — rejected: would require an interface rewrite when scale eventually demands separation.

## Tradeoffs
Gain: development speed, low infra cost early. Give up: must maintain contract discipline between modules even though they're in one process — a shortcut here becomes a costly rewrite later.

## Consequences
Phase 2 extracts Render/Voice/Asset workers onto NATS without changing their interface. Phase 3 extracts any measurably-bottlenecked agent the same way.

## Future Considerations
Revisit if a specific module's resource needs (CPU/GPU/scaling profile) diverge sharply from the rest of the monolith before Phase 2's planned timeline — that's the "tách theo đo đạc" measured-need trigger, not a calendar trigger.
