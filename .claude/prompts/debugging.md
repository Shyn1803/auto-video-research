# Prompt: Debugging

```
Root-cause this bug using docs/dev-guide.md §6 debug surfaces:
- Pipeline stuck? Check langgraph_checkpoints table / GET /projects/{id}/runs/{run_id}.
- Wrong LLM output? Check Langfuse or llm_usage + DEBUG logs, note prompt_id + version.
- Provider issue? Check GET /admin/providers for active/excluded reasons.
- Render failure? Check renders.error + render-worker logs + saved props JSON.
- Event stuck? Check NATS DLQ via /admin/queue.
Distinguish symptom from root cause. State the broken invariant (e.g. "content_hash not recomputed after X").
Propose a regression test that fails before the fix.
```
