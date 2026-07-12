# Workflow: Review Pull Request

**Inputs:** an open PR.

**Steps**
1. Run through [checklists/before-merge.md](../checklists/before-merge.md).
2. Check for Layout Engine boundary violations if the diff touches storyboard/scene/prompt code (see [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md)).
3. Check contract changes have a semver/migration note and matching `docs/` update.
4. Check Remotion Agent Skill usage is stated (if applicable) and spot-check the code actually follows the pattern.
5. Leave specific, actionable comments — not vague "looks off" feedback.
6. If a comment type recurs across 2+ PRs, propose a new rule/checklist item instead of repeating it manually forever.

**Quality Gates:** every item in before-merge.md checked; contract changes verified against docs.

**Outputs:** approve / request-changes with comments; possible new rule/checklist entry.

**Success Criteria:** merged code matches this project's conventions without requiring a second cleanup pass.
