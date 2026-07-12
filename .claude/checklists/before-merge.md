# Checklist: Before Merge

- [ ] All items in [before-commit.md](before-commit.md) hold
- [ ] CI green (once CI exists)
- [ ] ≥1 review approval
- [ ] Every story AC (happy/edge/error/permission) has a test
- [ ] Contract changes (schema/API/event/DB/env) have a semver note + matching `docs/` update + "Contract changes" PR section
- [ ] Remotion Agent Skill usage stated in PR description if touching `packages/remotion-templates/` or `render-worker/`, and spot-checked against actual code patterns
- [ ] No adapter reads env directly or logs usage itself
- [ ] Scope matches the story's Scope In/Out — no silent expansion
