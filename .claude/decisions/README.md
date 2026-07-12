# Architecture Decision Records — Index

Source of truth for the original 8: `docs/ARCHITECTURE.md` §11 (summary table). These files expand each into full ADR form (Context/Decision/Alternatives/Tradeoffs/Consequences/Future Considerations) per [templates/adr.md](../templates/adr.md). ADR-0009 is new — it formalizes a decision made during the Remotion runtime-integration deep-dive that was implicit but never written down as a standalone ADR.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-modular-monolith-first.md) | Modular monolith before service split | Accepted |
| [0002](0002-langgraph-checkpointing.md) | LangGraph checkpoint over hand-rolled saga | Accepted |
| [0003](0003-nats-jetstream.md) | NATS JetStream over Kafka/RabbitMQ | Accepted |
| [0004](0004-scene-json-contract.md) | Scene JSON + schema_version as central contract | Accepted |
| [0005](0005-provider-adapter-env-chain.md) | Provider adapter + env chain (local-first) | Accepted |
| [0006](0006-remotion-player-shared-template.md) | Remotion Player shares template with worker | Accepted |
| [0007](0007-jsonb-version-content.md) | JSONB for version content | Accepted |
| [0008](0008-layout-engine-deterministic.md) | Layout Engine: AI generates semantic only | Accepted |
| [0009](0009-scene-video-two-compositions.md) | Two Remotion compositions: Scene vs Video | Accepted |

New ADRs: copy [templates/adr.md](../templates/adr.md), number sequentially, add a row here.
