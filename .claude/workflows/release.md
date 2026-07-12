# Workflow: Release

**Inputs:** approaching a milestone or v1.0 per `docs/plan.md`'s continuous 18-week timeline.

**Steps**
1. Release Manager agent runs the full [checklists/before-release.md](../checklists/before-release.md).
2. Verify local-first 0-key run still works end-to-end (this is the system's core promise — regressions here are release-blocking).
3. Verify `ALLOW_PAID` defaults false, `MODE1_AUTOPUBLISH` defaults `off` in shipped `.env.example`.
4. Verify provider failover actually triggers under a simulated failure for at least one capability.
5. Security review sign-off (see [agents/security-engineer.md](../agents/security-engineer.md)).
6. Write release notes via [templates/release-note.md](../templates/release-note.md).
7. Update `docs/plan.md` milestone status.

**Quality Gates:** every Release Checklist item verified — no exceptions without explicit user sign-off.

**Outputs:** release notes, tagged release, updated plan.md.

**Success Criteria:** a fresh clone with `.env.example` and 0 API keys produces a working video end-to-end.
