# Workflow: Incident Response

**Inputs:** an active production incident (pipeline FAILED spike, DLQ backlog, cost cap breach, worker down, disk >80%) — these are this project's defined minimum alert conditions (ARCHITECTURE.md §9).

**Steps**
1. Identify blast radius: one project or system-wide? Check `docs/dev-guide.md` §6 debug surfaces to localize.
2. Stabilize first (pause the scheduler / pipeline / cost cap trip) before root-causing — stop the bleeding.
3. Root-cause using the same surfaces as [workflows/bug-fix.md](bug-fix.md).
4. Communicate status — this project treats Telegram/email notification (`TELEGRAM_BOT_TOKEN`, `SMTP_URL`) as the existing channel for FAIL/cost-cap/DLQ alerts; use it, don't invent a new channel silently.
5. Fix, verify, resume normal operation.
6. Write an incident report via [templates/incident-report.md](../templates/incident-report.md) and a postmortem if it reveals a systemic gap.

**Quality Gates:** incident stabilized before deep investigation; report written within a reasonable window after resolution.

**Outputs:** incident report, postmortem, possibly new alert rule or rule/pattern update.

**Success Criteria:** system back to healthy state; the detection/response gap that let it happen is closed or explicitly accepted.
