# Prompt: Architecture Review

```
Review this proposed change against docs/ARCHITECTURE.md and .claude/rules/architecture.md.
Specifically check:
1. Does it respect "tách theo đo đạc" (split by measured need, not speculation)?
2. Does every new module interface use a Pydantic model (Phase 1→2→3 extraction compatibility)?
3. Does any external capability access bypass the adapter pattern?
4. Does it preserve the Layout Engine boundary (AI never outputs layout/position/font/animation)?
5. Is a new ADR needed? Draft one using .claude/templates/adr.md if so.
Report: compliant / needs-ADR / violates-boundary, with specific line references.
```
