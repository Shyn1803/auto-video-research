# Workflow: Write Documentation

**Inputs:** new fact, decision, or process worth preserving; or a request to author/update a `docs/` or `.claude/` file.

**Steps**
1. Decide which tree it belongs in: `docs/` (product/architecture, PO-owned) vs `.claude/` (AI operating knowledge — see [knowledge-curator agent](../agents/knowledge-curator.md) decision rule).
2. Check for an existing file covering this topic — extend, don't duplicate.
3. Write concisely; state Why/What/How/Tradeoffs/Limitations where relevant, not just implementation detail.
4. Cross-link related docs instead of restating facts.
5. If this is a `docs/` change, follow the existing project convention of proposing to the user before finalizing product/architecture facts.

**Quality Gates:** no contradiction with an existing doc; no duplicated fact; cross-references added both directions where useful.

**Outputs:** new/updated doc file(s), updated `docs/README.md` reading-order table if a new top-level doc was added.

**Success Criteria:** a future reader (human or Claude) finds one authoritative answer, not two conflicting ones.
