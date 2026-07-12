# ADR-0005: Provider Adapter + Env Chain (Local-First)

**Status:** Accepted · **Date:** design phase (docs v1.0)

## Context
The system must run at $0 for testing/validation before any paid investment, per explicit user (PO) direction — and must be able to activate paid providers later purely by supplying credentials, without code changes or redeploys.

## Decision
Every external capability sits behind an adapter interface, selected by an env-declared priority chain (`LLM_CHAIN_CHEAP`, `TTS_CHAIN`, etc.). A provider is "available" only if present in the chain AND its activation condition holds (key present or local service reachable) AND (free OR `ALLOW_PAID=true`).

## Alternatives Considered
1. Hardcode one provider per capability, swap via code+redeploy when upgrading — rejected: contradicts the explicit "test free first, invest later without code change" requirement.
2. Feature flags instead of adapter+chain — rejected: doesn't give automatic failover on provider error/quota exhaustion.

## Tradeoffs
Gain: $0 operation is real, not aspirational; failover is automatic; no lock-in to any single vendor. Give up: every capability needs ≥2 adapters written (local + at least one cloud option) to realize the benefit.

## Consequences
See [patterns/provider-adapter.md](../patterns/provider-adapter.md) for the concrete skeleton. `docs/CONFIGURATION.md` is the single source of truth for chain defaults and activation conditions.

## Future Considerations
As paid providers prove out (quality/cost data), `ALLOW_PAID` flips per-environment with a documented decision, not silently.
