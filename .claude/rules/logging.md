# Rule: Logging

- Never log a raw secret: API keys, JWTs, Fernet master key, refresh tokens. Log key **identifiers** (provider name, key id, last-4) only.
- Usage/cost logging (`llm_usage` writes) happens in the router/service layer, never inside an adapter — adapters are usage-agnostic by design (glossary.md rule 5).
- Every event and log line tied to a pipeline run should carry `correlation_id` so a run is traceable end-to-end across nodes/workers (ARCHITECTURE.md §3.2, glossary.md).
- Provider failover must emit a `provider_failover` event/log, not fail silently — this is how the cost/reliability dashboards stay accurate.
- Structured logs preferred over string interpolation for anything that will be queried later (task tier, provider, project_id, cost_estimate).
