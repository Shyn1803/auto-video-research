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

**Open design tension (found in task 4-3, unresolved — read before wiring a real node into `app/pipeline/graph.py`):** a LangGraph node function's signature is `state -> dict`, no extra parameters. 4-1's tests build a real compiled graph and run the stub nodes (including `NodeName.RESEARCH`) with no DB/router mocking at all — that's how the happy-path tests stay fast and DB-less. But real node logic (4-3's `research_node`) needs a DB session (prompt cache, source cache) and a `ProviderRouter`. 4-3 resolved this by keeping the real logic in `app/pipeline/nodes/research/node.py::research_node` (self-contained: opens its own `Database`/`ProviderRouter`, fully unit-tested via mocking those imports) but **did not** swap it into `graph.py`'s live `NODE_FNS[NodeName.RESEARCH]`, because doing so would make every one of 4-1's existing happy-path tests try to open a real Postgres connection and fail in this DB-less sandbox. Whoever wires nodes 4-4/4-5/4-6 into the real graph (or does the eventual "make research_node the real NODE_FNS entry" swap) needs one of: (a) a live-DB CI/test environment so the existing 4-1 tests can inject a fake DB at the graph level too, or (b) a structural change so nodes receive session/router via LangGraph's `config`/context mechanism instead of importing their own — pick one deliberately, don't let each node re-invent its own self-contained-infra workaround.

**Connectors are not chain-failover (found in task 4-3):** `ProviderRouter.call()` implements "try providers in chain order, stop at first success" semantics — correct for LLM/TTS/etc. where providers are *alternatives*. Research's 5 connectors (arXiv/HN/GitHub/RSS/SearXNG) are *complementary* sources queried on every run (BR-1: "1 connector lỗi → skip; run fail chỉ khi MỌI connector lỗi") — using `ProviderRouter.call("search", ...)` here would be wrong, since it would stop after the first connector succeeds instead of querying all of them. `app/pipeline/nodes/research/node.py::collect_sources` calls each registered adapter directly via `get_adapter_class()` instead. Any future "run every source, tolerate individual failures" step (e.g. a multi-platform asset search in 6-1) should follow this same direct-call pattern, not force it through the router.
