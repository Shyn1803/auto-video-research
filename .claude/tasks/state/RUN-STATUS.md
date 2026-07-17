# Run Status — Rollup

Human-scannable snapshot of every task's current state. Generated/maintained by whichever agent updates a `state/{id}.json` — update this file's matching row in the same commit as the state-file change. This is a rollup for quick scanning; `state/{id}.json` is always the source of truth if the two ever disagree.

**Legend:** ⬜ not-started · 🔵 in-progress · 🔴 blocked · 🟡 review · ✅ done

**Audited:** 2026-07-17, reconciliation pass against actual git history — `git branch -a`, `git diff main...<branch> --stat` for every local/origin `feat/*` branch, and `git diff main...worktree-agent-a3b47cc427c4448c4 --stat` for worker-B's unpushed worktree (9 bundled commits touching 1-3, 1-7, 2-3, 2-4, 3-1, 3-2, 3-3, 3-4, 3-5, 5-1). Main HEAD at audit time: `6827f6b` (feat(auth): 1-7 must_change_password login flow), plus one untracked file (`backend/app/api/users.py`) not yet committed. Previous rollup (2026-07-15, HEAD `d937b44`) was stale: it had 1-7 as not-started (main has since gained real 1-7 backend work) and did not account for real, uncommitted/unmerged work sitting in local branches and worker-B's worktree for 1-3, 1-5, 3-3, 3-4, 3-5, 5-1.

| Task | Status | Current step | Branch | Blocked reason |
|---|---|---|---|---|
| 1-1 | ✅ done | 8 | feat/1-1-khoi-tao-monorepo | — |
| 1-2 | ✅ done | 6 | feat/1-2-auth-jwt-rbac | — |
| 1-3 | 🔵 in-progress | 2 | feat/1-3-project-crud-dashboard-nhom-vong-doi | project_service.py merged to main; API router (projects.py) + dashboard UI committed on local branch feat/1-3-project-crud-dashboard-nhom-vong-doi (2 commits: 68b24e4, cba4fb3) but not merged/wired into main.py |
| 1-4 | ✅ done | 4 | feat/1-4-state-machine | — |
| 1-5 | 🔵 in-progress | 1 | feat/1-5-versioning-engine | Main's `versioning_service.py` is a 1-line stub. Real implementation (versions API router 116 lines, schemas/version.py, 160-line service) exists on origin/feat/1-5-versioning-engine — pushed but not merged into main |
| 1-6 | ✅ done | 6 | feat/1-6-event-bus-sse | Merged d937b44 |
| 1-7 | 🔵 in-progress | 3 | feat/1-7-quan-ly-nguoi-dung-admin | Migration + user_admin_service.py + must_change_password login flow committed to main (5ef3a50, 6827f6b). API router backend/app/api/users.py written but UNCOMMITTED (untracked) and not wired into main.py's include_router(). Frontend Admin › Users UI tab not built (frontend/src/app/admin/users/ is an empty dir on main). A more complete version of both users.py and admin/users/page.tsx (430 lines) exists in worker-B's unpushed worktree — see note below |
| 2-1 | ✅ done | 7 | feat/2-1-scene-json-schema-v1 | — |
| 2-2 | ✅ done | 8 | feat/2-2-remotion-base-layer | — |
| 2-3 | ✅ done | 7 | feat/2-3-remotion-player-preview | — |
| 2-4 | ✅ done | 4 | feat/2-4-tts-adapter-edge-tts | Merged to main via 3-1 bundle commit 56d32e3 |
| 2-5 | ⬜ not-started | — | feat/2-5-subtitle-tu-timestamps | Only the Subtitle.tsx display primitive (from 2-2) exists; no timestamp-segmentation algorithm found on main, local branch, or origin branch |
| 2-6 | ✅ done | 7 | feat/2-6-layout-class-du-lieu | In 10-2 bundle |
| 3-1 | ✅ done | 8 | feat/3-1-adapter-base-registry-config-layer | — |
| 3-2 | ✅ done | 6 | feat/3-2-chain-router-failover-allow-paid | Merged (core/router.py 413 lines on main) |
| 3-3 | 🔴 blocked | 0 | feat/3-3-llm-adapters (not yet created) | Real LLM adapter work (groq.py, mock.py, ollama.py, openrouter.py, helpers.py) exists only in worker-B's unpushed worktree (`.claude/worktrees/agent-a3b47cc427c4448c4`, branch `worktree-agent-a3b47cc427c4448c4`). No dedicated feat/3-3 branch exists yet. Needs worker-B to split this out and push |
| 3-4 | 🔴 blocked | 0 | feat/3-4-api-key-management | api_keys model + api_key_service.py + admin/api_keys.py + crypto.py (Fernet) exist only in worker-B's worktree. origin/feat/3-4-api-key-management exists but its diff against current main looks stale/reverted, not the real implementation — needs worker-B to split real work onto this branch and push |
| 3-5 | 🔴 blocked | 0 | feat/3-5-cost-tracking-daily-cap-man-providers | cost_service.py, cost_guard.py, cap_guard.py, events/cost.py, admin/costs.py exist only in worker-B's worktree. origin branch of the same name looks stale — needs worker-B to split and push |
| 4-1 | ⬜ not-started | — | feat/4-1-langgraph | — |
| 4-2 | ⬜ not-started | — | feat/4-2-prompt-management | — |
| 4-3 | ⬜ not-started | — | feat/4-3-node-research | origin/feat/4-3-node-research exists but its diff vs. current main is mostly deletions of already-merged layout presets/primitives — appears to be a stale/pre-merge snapshot, not real node-research work. Treat as not-started until re-verified |
| 4-4 | ⬜ not-started | — | feat/4-4-node-ranking-factcheck | — |
| 4-5 | ⬜ not-started | — | feat/4-5-node-write | — |
| 4-6 | ⬜ not-started | — | feat/4-6-semantic-storyboard | — |
| 4-7 | ⬜ not-started | — | feat/4-7-dieu-khien-run | — |
| 4-8 | ⬜ not-started | — | feat/4-8-diem-vao-co-san | — |
| 5-1 | 🔴 blocked | 0 | feat/5-1-project-workspace-topbar-stepper (not yet created) | Substantial workspace UI (Topbar.tsx, PipelineStepper.tsx, SceneFormPanel.tsx, ScenePlayerPanel.tsx, SceneSidebar.tsx, ApproveBar.tsx, useAutosave.ts, workspace-context.tsx, workspace-store.ts, schema-form/generate.ts) exists only in worker-B's unpushed worktree. No feat/5-1 branch exists. Needs worker-B to split and push |
| 5-2 | ⬜ not-started | — | feat/5-2-edit-controls | — |
| 5-3 | ⬜ not-started | — | feat/5-3-assetpicker | — |
| 5-4 | ⬜ not-started | — | feat/5-4-scene-ops | — |
| 5-5 | ⬜ not-started | — | feat/5-5-man-hoan-thien | — |
| 5-6 | ⬜ not-started | — | feat/5-6-man-nghien-cuu | ready-for-dev in sprint-status.yaml |
| 5-7 | ⬜ not-started | — | feat/5-7-man-noi-dung | — |
| 5-8 | ⬜ not-started | — | feat/5-8-runningstate-component | — |
| 5-9 | ⬜ not-started | — | feat/5-9-versionswitcher | — |
| 5-10 | ⬜ not-started | — | feat/5-10-projectdrawer | — |
| 6-1 | ⬜ not-started | — | feat/6-1-node-produce | — |
| 6-2 | ⬜ not-started | — | feat/6-2-render-orchestrator | — |
| 6-3 | ⬜ not-started | — | feat/6-3-man-xuat-ban | — |
| 6-4 | ⬜ not-started | — | feat/6-4-benchmark-chot-nfr | — |
| 6-5 | ⬜ not-started | — | feat/6-5-thu-vien-nhac-nen | — |
| 7-1 | ⬜ not-started | — | feat/7-1-scheduler-service | — |
| 7-2 | ⬜ not-started | — | feat/7-2-mode-1-pipeline | — |
| 7-3 | ⬜ not-started | — | feat/7-3-gate-config | — |
| 7-4 | ⬜ not-started | — | feat/7-4-notification | — |
| 7-5 | ⬜ not-started | — | feat/7-5-dashboard-cho-duyet | — |
| 8-1 | ⬜ not-started | — | feat/8-1-publish-adapter | — |
| 8-2 | ⬜ not-started | — | feat/8-2-youtube-oauth | — |
| 8-3 | ⬜ not-started | — | feat/8-3-youtube-upload | — |
| 8-4 | ⬜ not-started | — | feat/8-4-publish-theo-lich | — |
| 8-5 | ⬜ not-started | — | feat/8-5-analytics-collector | — |
| 8-6 | ⬜ not-started | — | feat/8-6-analytics-dashboard | — |
| 8-7 | ⬜ not-started | — | feat/8-7-analytics-insights | — |
| 9-1 | ⬜ not-started | — | feat/9-1-nats-jetstream | — |
| 9-2 | ⬜ not-started | — | feat/9-2-render-worker | — |
| 9-3 | ⬜ not-started | — | feat/9-3-voice-asset-worker | — |
| 9-4 | ⬜ not-started | — | feat/9-4-dlq-quan-tri | — |
| 9-5 | ⬜ not-started | — | feat/9-5-prometheus-grafana | — |
| 9-6 | ⬜ not-started | — | feat/9-6-langfuse-sentry | — |
| 10-1 | ⬜ not-started | — | feat/10-1-multi-format-render | — |
| 10-2 | ✅ done | 5 | feat/10-2-bo-template | — |
| 10-3 | ⬜ not-started | — | feat/10-3-tiktok-facebook-linkedin | — |
| 10-4 | ⬜ not-started | — | feat/10-4-security-hardening | — |
| 10-5 | ⬜ not-started | — | feat/10-5-load-test | — |
| 10-6 | ⬜ not-started | — | feat/10-6-release-docs | — |

## Follow-up required from worker-B (not done in this reconciliation pass)

Worker-B's worktree (`.claude/worktrees/agent-a3b47cc427c4448c4`, branch `worktree-agent-a3b47cc427c4448c4`) has 9 unpushed commits with real, substantive work bundled together across tasks **1-3, 1-7, 2-3, 2-4, 3-1, 3-2, 3-3, 3-4, 3-5, 5-1**. Most of that content (1-3's projects API, 1-7's users.py+admin UI, 2-3, 2-4, 3-1, 3-2) is *already superseded* by what's on main or on other feat/* branches — but **3-3 (LLM adapters), 3-4 (API key management), 3-5 (cost tracking), and 5-1 (workspace UI)** have no other home: this worktree is the only place that work exists. Worker-B needs to split those 4 tasks' commits onto their own `feat/3-3-llm-adapters`, `feat/3-4-api-key-management`, `feat/3-5-cost-tracking-daily-cap-man-providers`, and `feat/5-1-project-workspace-topbar-stepper` branches and push, before those tasks can be marked done or built upon further.
