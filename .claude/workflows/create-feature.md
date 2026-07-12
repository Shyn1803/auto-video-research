# Workflow: Create Feature

**Inputs:** a request mapped (or mappable) to a task in [tasks/](../tasks/) / `docs/backlog/epic-XX-*.md`.

**Steps**
1. Planner agent maps request → task ID in `.claude/tasks/` (check there first — 65 tasks already exist, see [tasks/README.md](../tasks/README.md)). If no task fits, draft a story with `docs/backlog/story-template.md` + matching task file, flag ⏳ for PO confirmation.
2. Claim the task: set `in-progress` in `docs/backlog/stories/sprint-status.yaml`. Confirm the task's "Scope In/Out" boundary — don't silently expand.
3. Check [rules/architecture.md](../rules/architecture.md) — does this touch a contract (schema/API/event/DB/env)? If yes, plan the doc update alongside the code.
4. Implement per the matching engineer agent (backend/frontend/database) and [rules/code-style.md](../rules/code-style.md).
5. Write tests covering every AC in the story (happy/edge/error/permission).
6. Update `docs/` if a contract changed, in the same PR.
7. Self-review against [checklists/before-commit.md](../checklists/before-commit.md).
8. Mark the task `done` in `sprint-status.yaml`.

**Quality Gates:** all task ACs have tests; CI green (once CI exists); docs updated for any contract change; no AI-chooses-layout violation if touching storyboard/scene code.

**Outputs:** merged PR, updated task status in `sprint-status.yaml`, doc updates if applicable.

**Success Criteria:** the feature matches the story's AC exactly — no more, no less scope than what was agreed.
