# Rule: Pull Requests

- PR requires: CI green (once CI exists) + 1 review + docs updated if a contract changed (dev-guide.md §4).
- PR description must state, for any change under `packages/remotion-templates/` or `render-worker/`, which Remotion Agent Skill was invoked and for what part (dev-guide.md §2.1 Definition of Done) — reviewer verifies against actual code patterns, not just the claim.
- Contract-changing PRs need an explicit **Contract changes** section: what changed, semver impact, migration needed.
- Keep PRs scoped to one story or one clearly-bounded fix — don't bundle unrelated refactors into a feature PR (see [checklists/before-merge.md](../checklists/before-merge.md)).
