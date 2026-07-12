# ADR-0002: LangGraph Checkpoint Over Hand-Rolled Saga

**Status:** Accepted · **Date:** design phase (docs v1.0)

## Context
The pipeline needs resumable state after crashes, retry with backoff, and human-in-the-loop pausing (Mode 2 interrupts at every node) — all state-machine-adjacent concerns that are easy to get subtly wrong if hand-built.

## Decision
Use LangGraph with `langgraph-checkpoint-postgres` for pipeline orchestration — resume, retry, and human-gate interrupts come from the framework, checkpointed directly to the existing PostgreSQL instance.

## Alternatives Considered
1. Hand-written saga/state-machine — rejected: resume/retry/interrupt semantics are easy to get wrong, framework already solves this.
2. Temporal/other workflow engine — not chosen: adds a new piece of infrastructure vs. reusing PostgreSQL already in the stack.

## Tradeoffs
Gain: resume/retry/human-gate for free, matches existing Postgres infra. Give up: coupling to the LangChain ecosystem's release cadence and abstractions.

## Consequences
Every pipeline node must implement the fixed `run(input, ctx) -> output` interface (see [patterns/langgraph-pipeline-node.md](../patterns/langgraph-pipeline-node.md)) to stay compatible with checkpointing.

## Future Considerations
If LangGraph's abstractions become a limiting factor at Phase 3 scale, re-evaluate — but no signal of that yet.
