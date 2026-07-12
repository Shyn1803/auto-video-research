# Prompt: General Code Review

```
Review this diff against .claude/rules/code-style.md, .claude/rules/code-review.md, and .claude/checklists/before-merge.md.
Flag, in order of severity:
1. Layout Engine boundary violations (AI output containing layout/position/font/animation fields).
2. Contract changes (schema/API/event/DB/env) missing a semver note or docs/ update.
3. Adapter-pattern bypasses (direct provider SDK/HTTP call from business logic).
4. Style/convention deviations from .claude/rules/code-style.md.
For each finding: file, line, concrete failure scenario — not just "this looks off."
```
