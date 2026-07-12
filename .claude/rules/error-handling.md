# Rule: Error Handling

- Adapters wrap every external exception into `ProviderError(retryable: bool)` — callers never see raw HTTP/SDK exceptions (dev-guide.md §3).
- LLM routing: `QuotaError` → rotate key or move to next provider in chain; `TimeoutError`/5xx → move to next provider; chain exhausted → `AllProvidersFailed` → node retries with backoff → `FAILED` status if retries exhausted (ARCHITECTURE.md §2.2).
- Pipeline nodes resume from LangGraph checkpoint after a crash — don't design a node that can't be safely re-run (idempotency matters more than try/except cleverness).
- Render jobs are idempotent by `cache_key` (scene hash + template version + format) — a redelivered NATS message must not double-render or double-charge.
- FactCheck `FAIL` doesn't hard-block forever — human override is a first-class path (with reason + audit trail), not an escape hatch to bypass with a hack.
- Never swallow an exception to "make the pipeline green" — a silently-skipped step is worse than a visible `FAILED` state with a resumable checkpoint.
