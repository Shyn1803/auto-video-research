# Rule: Git

- Trunk-based development. Branches: `feat/{story-id}-mo-ta`, `fix/{description}`.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Story ID referenced in the commit subject when applicable: `feat(scene): S1.3-04 validate layout constraints`.
- Never force-push a shared branch, never amend a pushed commit without explicit agreement, never skip hooks (`--no-verify`) to get past a failing check — fix the underlying issue.
- Prefer small, reviewable commits over one large commit per story; each commit should build/lint clean on its own where feasible.
