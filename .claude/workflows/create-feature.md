# Workflow: Create Feature

**Inputs:** a request mapped (or mappable) to a story in `docs/backlog/epic-XX-*.md`.

**Steps**
1. Planner agent maps request → story ID. If no story fits, draft one with `docs/backlog/story-template.md` and flag ⏳ for PO confirmation.
2. Confirm story's "Scope In/Out" boundary — don't silently expand.
3. Check [rules/architecture.md](../rules/architecture.md) — does this touch a contract (schema/API/event/DB/env)? If yes, plan the doc update alongside the code.
4. Implement per the matching engineer agent (backend/frontend/database) and [rules/code-style.md](../rules/code-style.md).
5. Write tests covering every AC in the story (happy/edge/error/permission).
6. Update `docs/` if a contract changed, in the same PR.
7. Self-review against [checklists/before-commit.md](../checklists/before-commit.md).

**Quality Gates:** all story ACs have tests; CI green (once CI exists); docs updated for any contract change; no AI-chooses-layout violation if touching storyboard/scene code.

**Outputs:** merged PR, updated story status in `docs/backlog/`, doc updates if applicable.

**Success Criteria:** the feature matches the story's AC exactly — no more, no less scope than what was agreed.
