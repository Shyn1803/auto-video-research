# Workflow: Hotfix

**Inputs:** a production-impacting bug needing an out-of-cycle fix.

**Steps**
1. Confirm severity actually warrants bypassing the normal release cadence — not every urgent-feeling bug is a hotfix.
2. Root-cause per [workflows/bug-fix.md](bug-fix.md) — a hotfix still needs a real fix, not a band-aid that reintroduces the bug later.
3. Minimal-diff fix, scoped only to the incident — no opportunistic refactoring in a hotfix branch.
4. Regression test required even under time pressure — skip only with explicit user acknowledgment of the risk.
5. Deploy, verify in production, then backport the fix to the normal trunk if branches diverged.
6. Write a postmortem ([templates/postmortem.md](../templates/postmortem.md)) — hotfixes almost always reveal a process or detection gap worth recording.

**Quality Gates:** minimal diff; regression test exists or risk is explicitly accepted by the user.

**Outputs:** hotfix deploy, postmortem.

**Success Criteria:** incident resolved with the smallest safe change; the same failure is now caught earlier next time.
