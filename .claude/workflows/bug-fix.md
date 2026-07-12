# Workflow: Bug Fix

**Inputs:** bug report ([templates/bug-report.md](../templates/bug-report.md)) or a repro.

**Steps**
1. Debugger agent root-causes using `docs/dev-guide.md` §6 debug surfaces (checkpoints table, Langfuse/llm_usage, `/admin/providers`, `renders.error` + worker logs, NATS DLQ).
2. Confirm root cause, not just symptom — check whether an invariant broke (e.g. `content_hash` not recomputed) vs. surface-level exception.
3. Write a regression test that fails before the fix and passes after.
4. Apply the fix.
5. If the bug reveals a systemic gap (missing rule, recurring class of mistake), file a postmortem via [templates/postmortem.md](../templates/postmortem.md) and update [rules/](../rules/) or [anti-patterns/](../anti-patterns/) as needed.

**Quality Gates:** regression test exists and fails without the fix; root cause documented, not just "it works now."

**Outputs:** fix PR + regression test + optional postmortem.

**Success Criteria:** the same class of bug is now either impossible or caught immediately by the new test.
