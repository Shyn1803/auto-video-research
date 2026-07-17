# Run Status — Rollup

Human-scannable snapshot of every task's current state. Generated/maintained by whichever agent updates a `state/{id}.json` — update this file's matching row in the same commit as the state-file change. This is a rollup for quick scanning; `state/{id}.json` is always the source of truth if the two ever disagree.

**Legend:** ⬜ not-started · 🔵 in-progress · 🔴 blocked · 🟡 review · ✅ done

**Audited:** 2026-07-15 against git main HEAD d937b44 (70 commits). State JSON files stale from prior runs; this rollup reflects actual codebase.

| Task | Status | Current step | Branch | Blocked reason |
|---|---|---|---|---|
| 1-1 | ✅ done | 8 | feat/1-1-khoi-tao-monorepo | — |
| 1-2 | ✅ done | 6 | feat/1-2-auth-jwt-rbac | — |
| 1-3 | 🔵 in-progress | 1 | feat/1-3-project-crud | Partial: model+migration done, no API routes yet |
| 1-4 | ✅ done | 4 | feat/1-4-state-machine | — |
| 1-5 | 🔵 in-progress | 1 | feat/1-5-versioning-engine | StepVersion model exists, service is stub (73b) |
| 1-6 | ✅ done | 6 | feat/1-6-event-bus-sse | Merged d937b44 |
| 1-7 | ⬜ not-started | — | feat/1-7-quan-ly-nguoi-dung-admin | — |
| 2-1 | ✅ done | 7 | feat/2-1-scene-json-schema-v1 | — |
| 2-2 | ✅ done | 8 | feat/2-2-remotion-base-layer | — |
| 2-3 | ✅ done | 7 | feat/2-3-remotion-player-preview | — |
| 2-4 | ✅ done | 4 | feat/2-4-tts-adapter-edge-tts | In 3-1 commit (56d32e3) |
| 2-5 | ⬜ not-started | — | feat/2-5-subtitle-tu-timestamps | — |
| 2-6 | ✅ done | 7 | feat/2-6-layout-class-du-lieu | In 10-2 bundle |
| 3-1 | ✅ done | 8 | feat/3-1-adapter-base-registry-config-layer | — |
| 3-2 | ✅ done | 6 | feat/3-2-chain-router-failover-allow-paid | — |
| 3-3 | ✅ done | 9/9 | feat/3-3-llm-adapters | pushed 2a2105a |
| 3-4 | ⬜ not-started | — | feat/3-4-api-key-management | — |
| 3-5 | ⬜ not-started | — | feat/3-5-cost-tracking | — |
| 4-1 | ⬜ not-started | — | feat/4-1-langgraph | — |
| 4-2 | ⬜ not-started | — | feat/4-2-prompt-management | — |
| 4-3 | ⬜ not-started | — | feat/4-3-node-research | — |
| 4-4 | ⬜ not-started | — | feat/4-4-node-ranking-factcheck | — |
| 4-5 | ⬜ not-started | — | feat/4-5-node-write | — |
| 4-6 | ⬜ not-started | — | feat/4-6-semantic-storyboard | — |
| 4-7 | ⬜ not-started | — | feat/4-7-dieu-khien-run | — |
| 4-8 | ⬜ not-started | — | feat/4-8-diem-vao-co-san | — |
| 5-1 | ⬜ not-started | — | feat/5-1-project-workspace | — |
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
