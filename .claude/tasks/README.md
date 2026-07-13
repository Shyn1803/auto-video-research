# Tasks — Agent-Team Execution Manifest

**Purpose:** every file in this folder is a **self-contained, dev-ready task** an agent (or agent team) can pick up and implement without needing to open `docs/backlog/epic-XX-*.md` first. Source of truth for the underlying product decisions remains `docs/backlog/` — these files are a derived, execution-optimized view. If the two ever disagree, `docs/backlog/` wins; fix this folder to match (see [rules/documentation.md](../rules/documentation.md)).

Filenames match the keys in [docs/backlog/stories/sprint-status.yaml](../../docs/backlog/stories/sprint-status.yaml) exactly — update status there as tasks move, not in these files.

**Do not stop and wait for confirmation between tasks.** This manifest exists specifically so an agent team can work through the backlog in one pass, for long unattended stretches — see [rules/autonomy-policy.md](../rules/autonomy-policy.md): decide and continue on anything reversible/locally-scoped; escalate only per the bounded criteria there, and prefer flagging + continuing over blocking.

## Quick orientation (read this before opening any individual task)

- Every task now follows [TASK-TEMPLATE.md](TASK-TEMPLATE.md): Scope/BR/AC/Data/DoD (unchanged, from `docs/backlog/`) **plus** a numbered **Execution Steps** checklist detailed enough for a smaller model to follow without improvising, a mandatory **Retrospective**, and a **Resuming after interruption** section.
- Progress is tracked outside the task file, in [`state/{task-id}.json`](state/README.md) — this is the "where am I if something errors" mechanism. Check [`state/RUN-STATUS.md`](state/RUN-STATUS.md) first for a one-glance rollup of every task's status before diving into individual files.
- The full claim → branch → execute → retry → commit/push → retrospective loop is documented once, in [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — read it once per run, not per task.
- **Git automation is pre-authorized for this project**: auto branch-checkout, auto-commit, and auto-push to feature branches (`feat/*`) happen with no per-action confirmation (see `workflows/autonomous-task-execution.md` "Git automation scope"). Pushing to `main`, force-push, and opening a PR remain gated.
- **Retry policy**: up to 3 attempts per Execution Step before a step (and its task) is marked `blocked` and the run moves on to a different unblocked task — never a hard stop. Full policy in the workflow doc.

## How an agent team should consume this folder

1. **Read [rules/autonomy-policy.md](../rules/autonomy-policy.md), [CLAUDE.md](../CLAUDE.md), and [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) once**, at the start of the run — not per task.
2. **Respect the dependency graph below.** A task's `Depends` line lists other task files (by filename stem) that must be `done` first. Tasks with no unmet dependencies can run in parallel.
3. **Claim a task**: update its status in `sprint-status.yaml` to `in-progress`, and read/initialize `state/{task-id}.json` (avoids two agents claiming the same task, and tells you immediately if this task already has partial progress to resume).
4. **Work the task**: every task file has Scope In/Out, Business Rules, Acceptance Criteria, Data & API impact, Execution Steps, and a Definition of Done — implement to that, not beyond (no silent scope expansion; see [rules/pull-requests.md](../rules/pull-requests.md)). Update the state file after every step.
5. **Before marking done**: run [checklists/before-merge.md](../checklists/before-merge.md) and the task's Retrospective section. If the task is a "đổi contract" change (flagged in the task file), update the matching `docs/specs/*` file in the same change.
6. **Mark done** in `sprint-status.yaml` and `state/{task-id}.json`, move to the next unblocked task — do not pause for confirmation.
7. **If genuinely blocked** (contract ambiguity, missing precedent, product decision, or 3 failed retries on a step): mark the task `blocked` in its state file with a specific reason, flag it in `memory/project-memory.md` Open Questions, and move to a different unblocked task rather than halting the whole run — per the async-escalation rule in autonomy-policy.md and the retry policy in the workflow doc.

## Task → agent ownership

Every task in this folder maps to one primary agent role from [agents/](../agents/). A task may need a second agent for review (Reviewer always) or a specialist pass (Security Engineer on auth/keys/RBAC tasks) — those are noted per-epic below, not per-task, to avoid drift.

| Epic | Primary agent | Notes |
|---|---|---|
| 1. Nền tảng + người dùng | [backend-engineer](../agents/backend-engineer.md) | 1-1 needs [devops-engineer](../agents/devops-engineer.md) too (compose/CI); 1-2/1-7 need [security-engineer](../agents/security-engineer.md) review (auth/RBAC). |
| 2. Scene JSON + Remotion | [frontend-engineer](../agents/frontend-engineer.md) for 2-2/2-3 (Remotion/Player); [backend-engineer](../agents/backend-engineer.md) for 2-1 (schema)/2-4 (TTS adapter). 2-5/2-6 split both. | Invoke the Remotion Agent Skill named in the task before writing (dev-guide.md §2.1). |
| 3. Provider framework | [backend-engineer](../agents/backend-engineer.md) | 3-4 (key encryption) gets [security-engineer](../agents/security-engineer.md) review. |
| 4. Pipeline AI + Layout Engine core | [backend-engineer](../agents/backend-engineer.md) | 4-6 is the highest-scrutiny task in the backlog — [architect](../agents/architect.md) reviews for Layout Engine boundary compliance before merge, not just Reviewer. |
| 5. Workspace UI | [frontend-engineer](../agents/frontend-engineer.md) | Every task in this epic requires the real-browser exercise rule (`rules/testing.md`) before being called done — type-checks are not sufficient. |
| 6. Produce, Render & Download | [backend-engineer](../agents/backend-engineer.md) + [frontend-engineer](../agents/frontend-engineer.md) for 6-3 (Xuất bản UI) | 6-2/6-4 get [performance-engineer](../agents/performance-engineer.md) review (caching, benchmark numbers). |
| 7. Mode 1 + Scheduler + hàng đợi duyệt | [backend-engineer](../agents/backend-engineer.md) | 7-5 gets [frontend-engineer](../agents/frontend-engineer.md) for the dashboard UI half. |
| 8. Publish & Analytics + Insights | [backend-engineer](../agents/backend-engineer.md) | 8-2 (OAuth) gets [security-engineer](../agents/security-engineer.md) review; 8-6/8-7 get [frontend-engineer](../agents/frontend-engineer.md) for the dashboard/insights UI half. |
| 9. NATS, Workers & Observability | [devops-engineer](../agents/devops-engineer.md) + [backend-engineer](../agents/backend-engineer.md) | Do not start before Epic 6 is done (see below). |
| 10. Multi-platform, Hardening & Release | [security-engineer](../agents/security-engineer.md) owns 10-4; [release-manager](../agents/release-manager.md) owns 10-6; [performance-engineer](../agents/performance-engineer.md) owns 10-5; [backend-engineer](../agents/backend-engineer.md) owns 10-1/10-2/10-3. |

[database-engineer](../agents/database-engineer.md) is a cross-cutting reviewer for any task whose Data & API section adds/changes a table or migration (most tasks) — not listed per-row to avoid duplicating every task's contract-change flag. [qa-engineer](../agents/qa-engineer.md) and [reviewer](../agents/reviewer.md) apply to every task per the standard DoD below. [knowledge-curator](../agents/knowledge-curator.md) runs the retrospective after each task per `CLAUDE.md` §8 — not per-epic, after every completed task.

## Parallel execution tracks (per docs/plan.md)

Two independent starting points, designed to run on separate agents/dev from week 1:

- **Track A (backend foundation):** `1-1` → `1-2` → `1-3` → `1-4` → `1-5` → `1-6` (with `1-7` branching off `1-2` in parallel with `1-3`) → `3-1` → `3-2` → `3-3`/`3-4`/`3-5` → `4-1` → `4-2` → `4-3` → `4-4` → `4-5` → `4-6` → `4-7`/`4-8`
  - Corrected 2026-07-13: task files' actual `Depends:` lines show `1-4` depends on `1-3` (not `1-2` as previously listed here), and `1-3` depends on `1-2` — `.claude/tasks/*.md` is the derived-but-verified view; this line was stale against it.
- **Track B (Scene/Remotion foundation):** `1-1` → `2-1` → `2-2` → `2-3`/`2-4` → `2-5` → `2-6`
- **Milestone M1** (end of Track B core + hand-written fixture): `2-1`, `2-2`, `2-3`, `2-4`, `2-5` done → hand-assembled 30s 9:16 Vietnamese-voice video with synced subtitle.
- Tracks converge at **Epic 5 (Workspace UI)**, which depends on both `2.x` (Player/schema) and `4.x` (pipeline) outputs; `5-6` is the template exemplar and already `ready-for-dev` (see `docs/backlog/stories/story-5.6-research-review.md`).
- **Epic 6 (Render/Produce)** depends on `4-6` (storyboard/scene resolution) and `2-2`/`2-6` (Remotion templates) — this is Milestone M4, first true topic→MP4 path.
- **Epic 7 (Mode 1 automation)** depends on `6-2`/`6-3` (render + publish-download) and `4-7` (run control).
- **Epic 8 (Publish/Analytics)** depends on `6-3`; `8.7` (Insights) depends on `8-5`/`8-6`.
- **Epic 9 (NATS/Workers/Observability)** is deliberately sequenced *after* M4 (epic 6) — contract stability before extraction, per ADR-0001. Don't start these early even if capacity is free.
- **Epic 10 (Multi-platform/Hardening/Release)** is the closing epic — most items depend on nearly everything before them; `10-4` (security hardening) explicitly depends on "toàn hệ" (the whole system).

## Full task index (65 tasks across 10 epics)

| Epic | Points | Weeks | Tasks |
|---|---|---|---|
| 1. Nền tảng + người dùng | 25 | 1–3 | [1-1](1-1-khoi-tao-monorepo-moi-truong-dev.md) [1-2](1-2-auth-jwt-rbac.md) [1-3](1-3-project-crud-dashboard-nhom-vong-doi.md) [1-4](1-4-state-machine-status-history.md) [1-5](1-5-versioning-engine.md) [1-6](1-6-event-bus-noi-bo-sse.md) [1-7](1-7-quan-ly-nguoi-dung-admin.md) |
| 2. Scene JSON + Remotion + TTS + 11 layout | 26 | 1–3 (2.6: 4–6) | [2-1](2-1-scene-json-schema-v1.md) [2-2](2-2-remotion-base-layer.md) [2-3](2-3-remotion-player-preview.md) [2-4](2-4-tts-adapter-edge-tts.md) [2-5](2-5-subtitle-tu-timestamps.md) [2-6](2-6-layout-class-du-lieu-cau-truc.md) |
| 3. Provider framework | 18 | 3–5 | [3-1](3-1-adapter-base-registry-config-layer.md) [3-2](3-2-chain-router-failover-allow-paid.md) [3-3](3-3-llm-adapters.md) [3-4](3-4-api-key-management.md) [3-5](3-5-cost-tracking-daily-cap-man-providers.md) |
| 4. Pipeline AI + Layout Engine core | 33 | 5–8 | [4-1](4-1-langgraph-skeleton-checkpoint-human-gate.md) [4-2](4-2-prompt-management-seed.md) [4-3](4-3-node-research.md) [4-4](4-4-node-ranking-factcheck.md) [4-5](4-5-node-write-outline-script.md) [4-6](4-6-semantic-storyboard-layout-engine-core.md) [4-7](4-7-dieu-khien-run-huy-ngam-resume.md) [4-8](4-8-diem-vao-co-san-kich-ban.md) |
| 5. Workspace UI | 28 | 4–8 | [5-1](5-1-project-workspace-topbar-stepper.md) [5-2](5-2-edit-controls.md) [5-3](5-3-assetpicker.md) [5-4](5-4-scene-ops.md) [5-5](5-5-man-hoan-thien.md) [5-6](5-6-man-nghien-cuu.md) [5-7](5-7-man-noi-dung.md) [5-8](5-8-runningstate-component.md) [5-9](5-9-versionswitcher-so-sanh-history.md) [5-10](5-10-projectdrawer.md) |
| 6. Produce, Render & Download | 18 | 9–10 | [6-1](6-1-node-produce.md) [6-2](6-2-render-orchestrator.md) [6-3](6-3-man-xuat-ban-video-download.md) [6-4](6-4-benchmark-chot-nfr.md) [6-5](6-5-thu-vien-nhac-nen.md) |
| 7. Mode 1 + Scheduler + hàng đợi duyệt | 19 | 11–13 | [7-1](7-1-scheduler-service.md) [7-2](7-2-mode-1-pipeline-tu-hanh.md) [7-3](7-3-gate-config-thong-ke.md) [7-4](7-4-notification-telegram-email.md) [7-5](7-5-dashboard-cho-duyet-hom-nay.md) |
| 8. Publish & Analytics + Insights | 24 | 12–15 | [8-1](8-1-publish-adapter-interface.md) [8-2](8-2-youtube-oauth-flow.md) [8-3](8-3-youtube-upload-ai-disclosure.md) [8-4](8-4-publish-theo-lich.md) [8-5](8-5-analytics-collector.md) [8-6](8-6-analytics-dashboard.md) [8-7](8-7-analytics-insights.md) |
| 9. NATS, Workers & Observability | 21 | 14–16 | [9-1](9-1-nats-jetstream-event-library.md) [9-2](9-2-render-worker-container-rieng.md) [9-3](9-3-voice-asset-worker.md) [9-4](9-4-dlq-quan-tri-hang-doi.md) [9-5](9-5-prometheus-grafana-alerts.md) [9-6](9-6-langfuse-sentry-self-host.md) |
| 10. Multi-platform, Hardening & Release | 18 | 15–18 | [10-1](10-1-multi-format-render-production.md) [10-2](10-2-bo-template-2-3.md) [10-3](10-3-tiktok-facebook-linkedin-adapters.md) [10-4](10-4-security-hardening.md) [10-5](10-5-load-test-backup-drill.md) [10-6](10-6-release-docs-checklist-go-live.md) |

**Total: 230 points, 18-week continuous timeline (docs/plan.md) — Phases are sequencing, not scope cuts.**

## Definition of Done (applies to every task unless the task overrides it)

1. Code + tests per `docs/test-plan.md`; CI green (once CI exists).
2. Every Acceptance Criterion in the task is verifiable — note how in the PR.
3. Contract change → matching `docs/specs/*` updated in the same change ([dev-guide.md](../../docs/dev-guide.md) §5).
4. UI task → matches [design/wireframe.html](../../docs/design/wireframe.html) + all 5 UI states ([design-system.md](../../docs/design/design-system.md) §3).
5. Run [checklists/before-merge.md](../checklists/before-merge.md) before marking done.
