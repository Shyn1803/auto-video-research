# Workflow: Refactor

**Inputs:** identified duplication, oversized component/module, or coupling problem.

**Steps**
1. Confirm the refactor doesn't change external behavior/contract — if it does, this is an architecture-change workflow instead.
2. Confirm test coverage exists for the code being refactored before touching it; add characterization tests first if missing.
3. Refactor in small, independently-buildable commits.
4. Re-run full test suite after each meaningful step, not just at the end.
5. If the refactor extracts a genuinely reusable shape, document it in [patterns/](../patterns/).

**Quality Gates:** no behavior change (tests unchanged in intent, still pass); no new contract surface introduced silently.

**Outputs:** refactor PR, possibly a new pattern doc.

**Success Criteria:** code is measurably simpler/less duplicated; nothing external observes a difference.
