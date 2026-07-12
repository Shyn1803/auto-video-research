# ADR-0003: NATS JetStream Over Kafka/RabbitMQ

**Status:** Accepted · **Date:** design phase (docs v1.0)

## Context
Phase 2+ needs a work queue for Render/Voice/Asset/Publish jobs with dedupe, retry, and DLQ — but the team is small and self-hosting complexity has a real cost.

## Decision
NATS JetStream — single binary, WorkQueue streams, built-in dedupe (`Nats-Msg-Id`), sufficient for this system's throughput needs.

## Alternatives Considered
1. Kafka — rejected: heavier operational footprint (ZooKeeper/KRaft, partitioning complexity) than this system's scale currently justifies.
2. RabbitMQ — not chosen: NATS JetStream's WorkQueue + dedupe covers the same need with a lighter footprint.

## Tradeoffs
Gain: minimal operational overhead, one binary to run/monitor. Give up: smaller ecosystem/tooling than Kafka if very advanced streaming semantics are ever needed.

## Consequences
Event subjects/streams defined in `docs/ARCHITECTURE.md` §3; every event carries `event_id` for dedupe and a `schema_version` for the same semver discipline as Scene JSON.

## Future Considerations
Revisit only if a specific workload demonstrably needs Kafka-class throughput/ordering guarantees NATS JetStream can't provide — no such signal expected at this project's scale.
