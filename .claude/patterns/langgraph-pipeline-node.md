# Pattern: LangGraph Pipeline Node

**Problem:** the pipeline (research→fact_check→write→storyboard→produce→render→publish) needs nodes that checkpoint, resume after crash, support human-gate interrupts (Mode 2), and can later become NATS-consumed microservices (Phase 2-3) without a rewrite.

**Solution:** every node implements one fixed interface:

```python
def run(input: NodeInput, ctx: RunContext) -> NodeOutput: ...
```

Both `NodeInput` and `NodeOutput` are Pydantic models — this is deliberate: the exact same schema becomes an event payload when the node is extracted to a NATS consumer in Phase 2/3, so extraction is a deployment change, not an interface change (ARCHITECTURE.md §2.1, ADR ref: modular-monolith-first).

**Rules:**
- Node state is checkpointed to PostgreSQL via `langgraph-checkpoint-postgres` — a crash resumes at the right node, don't design a node that can't be safely re-entered.
- Mode 2 pauses at every node for human approval (LangGraph interrupt). Mode 1 runs through except the Fact Check gate. A node shouldn't assume which mode it's running under — the gate behavior is orchestration, not node logic.
- LLM-calling nodes declare a `tier` (`cheap`/`strong`/`embedding`) per call — this is what the router uses to pick a chain.
- The `storyboard` node internally runs the layered Layout Engine pipeline (see [layout-engine-resolution.md](layout-engine-resolution.md)) — but externally still honors the same `run(input, ctx) -> output` contract as any other node.

**When to use:** any new pipeline step. Don't bypass LangGraph's checkpoint/interrupt machinery with custom control flow inside a node.

**Gotcha (found in task 4-1):** LangGraph's `RetryPolicy` default `retry_on` (`langgraph.types.default_retry_on`) explicitly does **not** retry `ValueError`, `TypeError`, `RuntimeError`, `LookupError`, `OSError`, and several other common builtin exception types — only `ConnectionError`, HTTP 5xx, and anything *not* in that exclusion list. A node that raises a plain `RuntimeError`/`ValueError` (easy to do before an adapter wraps it as `ProviderError`) will **not** retry at all, silently defeating BR-4's "retry 3 lần" requirement. `app/pipeline/graph.py`'s `RETRY_POLICY` overrides this with `retry_on=lambda _exc: True` until every node's exceptions are typed `ProviderError(retryable=...)` (rules/error-handling.md) — narrow it back down once that's true everywhere, but don't drop the override before then or BR-4 quietly stops working for whole exception classes.
