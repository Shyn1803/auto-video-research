# Run Status — Rollup

Human-scannable snapshot of every task's current state. Generated/maintained by whichever agent updates a `state/{id}.json` — update this file's matching row in the same commit as the state-file change. This is a rollup for quick scanning; `state/{id}.json` is always the source of truth if the two ever disagree.

**Legend:** ⬜ not-started · 🔵 in-progress · 🔴 blocked · 🟡 review · ✅ done

**Audited:** 2026-07-17, reconciliation pass against actual git history — `git branch -a`, `git diff main...<branch> --stat` for every local/origin `feat/*` branch, and `git diff main...worktree-agent-a3b47cc427c4448c4 --stat` for worker-B's unpushed worktree (9 bundled commits touching 1-3, 1-7, 2-3, 2-4, 3-1, 3-2, 3-3, 3-4, 3-5, 5-1). Main HEAD at audit time: `6827f6b` (feat(auth): 1-7 must_change_password login flow), plus one untracked file (`backend/app/api/users.py`) not yet committed. Previous rollup (2026-07-15, HEAD `d937b44`) was stale: it had 1-7 as not-started (main has since gained real 1-7 backend work) and did not account for real, uncommitted/unmerged work sitting in local branches and worker-B's worktree for 1-3, 1-5, 3-3, 3-4, 3-5, 5-1.

| Task | Status | Current step | Branch | Blocked reason |
|---|---|---|---|---|
| 1-1 | ✅ done | 8 | feat/1-1-khoi-tao-monorepo | — |
| 1-2 | ✅ done | 6 | feat/1-2-auth-jwt-rbac | — |
| 1-3 | ✅ done | 7 | feat/1-3-project-crud-dashboard-nhom-vong-doi | Merged to main 2026-07-17. Prior rollup row was stale (commits 68b24e4/cba4fb3 didn't exist anywhere). Fixed real bugs blocking Project entirely (indentation error, missing imports, missing FKs, circular import) — see state/1-3.json decisions[]. Wired projects_router into main.py, completed project_service (get_any/unarchive/clone_step_versions), added schemas/project.py, dashboard UI (page.tsx/ProjectCard/CreateProjectModal). Integration/e2e tests deferred (no live Postgres/browser in sandbox) — unit tests (15, all green) cover BR-1/2/3/4/6. |
| 1-4 | ✅ done | 4 | feat/1-4-state-machine | — |
| 1-5 | ✅ done | 6 | feat/1-5-versioning-engine | Merged to main 2026-07-17 (8aae243). Merged origin/feat/1-5-versioning-engine's real service; fixed a broken `Depends(get_session)` (didn't exist) in the router by switching to this codebase's actual `request.app.state.database.session()` pattern; added missing create/current endpoints + 409 running-guard on restore; updated api-spec.md §3. Property-test (Step 6 back half) deferred — no live Postgres in sandbox; 11 unit tests cover AC 1-5. |
| 1-6 | ✅ done | 6 | feat/1-6-event-bus-sse | Merged d937b44 |
| 1-7 | ✅ done | 6 | feat/1-7-quan-ly-nguoi-dung-admin | Merged to main 2026-07-17 (bca3b1b/051c247): reconciled HEAD's tested UserAdminService/users.py with origin/main's worker-B version (kept HEAD's API since it had passing tests, folded in email/password validation); frontend admin/users/page.tsx (430 lines) merged from worker-B worktree |
| 2-1 | ✅ done | 7 | feat/2-1-scene-json-schema-v1 | — |
| 2-2 | ✅ done | 8 | feat/2-2-remotion-base-layer | — |
| 2-3 | ✅ done | 7 | feat/2-3-remotion-player-preview | — |
| 2-4 | ✅ done | 4 | feat/2-4-tts-adapter-edge-tts | Merged to main via 3-1 bundle commit 56d32e3 |
| 2-5 | ✅ done | 5 | feat/2-5-subtitle-tu-timestamps | Merged to main 2026-07-17. Built from scratch: evaluated `@remotion/captions` (rejected — time-window grouping only, no BR-1 number+unit awareness), custom `segmentTimestamps.ts` (BR-1/2/4), `Subtitle.tsx` line-style + enabled/disabled (BR-3), wired into `SceneRenderer` via useMemo. 49/49 vitest green incl. no-text-lost property test. |
| 2-6 | ✅ done | 7 | feat/2-6-layout-class-du-lieu | In 10-2 bundle |
| 3-1 | ✅ done | 8 | feat/3-1-adapter-base-registry-config-layer | — |
| 3-2 | ✅ done | 6 | feat/3-2-router-settings-fix | Merged. 2026-07-17 (later): fixed real test-blocking bugs found by a full-suite run — `ProviderRouter.__init__()` didn't accept `settings=`; module referenced undefined `_cache_key`/`_now_iso` helpers; AC5 circuit-breaker gap (call() never invoked `adapter.available()` as a health pre-flight). All 9 tests/unit/core/test_router.py green. |
| 3-3 | ✅ done | 9 | feat/3-3-gemini-schema-embedding-fix | Merged to main 2026-07-17 (commit 3f12241): fixed the remaining red spots flagged by the prior pass — Gemini `_build_gemini_body()` schema normalization/recursion + description/title stripping; `embedding_gemini._parse_embed_response` float32→float64 precision; `embedding_bge_m3.available()` live-import check instead of cached-only flag; `test_embedding.py` missing `@respx.mock` decorator + replaced a mathematically-invalid char-trigram cosine helper with a synonym-canonicalized word-token cosine for the AC4 same/different-topic tests. `pytest tests/unit/adapters/llm/test_gemini.py tests/unit/adapters/llm/test_embedding.py` → 35 passed, 0 failed. |
| 3-4 | 🔵 in-progress | 0 | feat/3-4-fernet-key-mask-fix | Merged to main 2026-07-17 (later): backend (steps 1-6,8-9) was already on main; fixed invalid FERNET_MASTER_KEY test fixture (not a real 32-byte key), mask() edge cases, get_plaintext() wrongly-async signature, a real `ApiKey.usage_count` class-vs-instance bug in track_usage(), api_keys.py's function-local imports silently breaking every `@patch("app.api.admin.api_keys.X")` (moved to module level), and `_get_session(request)` passed as an already-invoked CM where KeyService expects a callable (`KeyService(lambda: _get_session(request))`). Still red: 1 RBAC integration test blocked on a shared conftest.py gap (FakeDatabase always resolves ADMIN_USER regardless of JWT role — test-fixture bug, not a real RBAC hole); Step 7 (Admin UI) unverified in a browser. |
| 3-5 | 🔵 in-progress | 0 | feat/3-5-cost-service-provider-status-fix | Merged to main 2026-07-17 (later): cost_service.py/provider_status_service.py were already on main; fixed test mocks using AsyncMock where real SQLAlchemy Result methods (`.all()`/`.one_or_none()`) are sync, an eager `r.get(...)` call on a plain Row double, missing `.ti/.to/.provider/.calls` aliases on that Row double, `CostService(session_factory=cm)` passing an already-invoked CM instead of a factory callable, a stale `_REGISTRY` import (real name `_registry`), an unsupported-magic-method MagicMock `__getattr__` assignment, and `register_llm(name, cls)` called as a 2-arg function instead of `register_llm(name)(cls)` (it's a decorator factory). Still red/unverified: cost_guard.py/cap_guard.py (Step 2) have zero test coverage; Step 6 (Admin UI) unverified in a browser. |
| 4-1 | ✅ done | 9 | feat/4-1-langgraph-skeleton-checkpoint-human-gate | Merged to main 2026-07-18: real langgraph StateGraph (postgres checkpointer + InMemorySaver fallback), interrupt-after-every-node, RunService (BR-1/2/4), atomic StepVersion+run write (BR-3), run/approve/get-run API, 21 new tests. See state/4-1.json decisions for scope simplifications flagged for 4-3..4-6 |
| 4-2 | ✅ done | 10 | feat/4-2-prompt-management-seed | Merged to main 2026-07-18: prompts/prompt_versions schema (partial-unique-active index), 8 prompts seeded verbatim from docs/specs/prompts.md, Jinja2 render+validation (BR-3), invalidate-on-activate cache (AC1), CI hardcoded-prompt guard, activate/rollback+audit (BR-2/5), RBAC (AC3), admin UI, prompt-eval CLI+fixture (AC4), BR-1 race test (AC5). See state/4-2.json decisions |
| 4-3 | ✅ done | 8 | feat/4-3-node-research | Merged to main 2026-07-18: sources/source_embeddings schema, 5 connector adapters (arxiv/hn_algolia/github/rss/searxng), trafilatura crawl+paywall, dedupe (url_hash+embedding similarity), content_hash cache+max-N cap, bounded-parallel summarize, node orchestration (BR-1)+SSE, full AC1/AC3 fixture tests. research_node NOT yet wired into graph.py's live NODE_FNS -- see state/4-3.json decisions + patterns/langgraph-pipeline-node.md |
| 4-4 | ✅ done | 8 | feat/4-4-node-ranking-factcheck | Merged to main 2026-07-18: claims schema + api-spec §5 contract update, ranking node (configurable weights), claim extraction, evidence gathering + verify_claim (BR-1/2/4 gates), overall verdict + NEED_REVIEW gate, override endpoint (BR-3, audit), source disable cascade (BR-5), reusable factcheck_conflict.json fixture. Found cross-cutting `/api` prefix mismatch on non-admin routers -- see state/4-4.json decisions + project-memory.md |
| 4-5 | ⬜ not-started | — | feat/4-5-node-write | — |
| 4-6 | ⬜ not-started | — | feat/4-6-semantic-storyboard | — |
| 4-7 | ⬜ not-started | — | feat/4-7-dieu-khien-run | — |
| 4-8 | ⬜ not-started | — | feat/4-8-diem-vao-co-san | — |
| 5-1 | ✅ done | 8 | feat/5-1-project-workspace-topbar-stepper | Re-verified 2026-07-17 (later): workspace UI was already on main (d37a9ab) but had real bugs (Rules-of-Hooks violation, wrong import path, default/named export mismatch, Next 15 `params` Promise, dead zustand file, disabled-attribute hover bug) and zero backend (no scenes API at all). Fixed all, added scenes API + approve endpoint + tests, fixed repo-wide broken vitest config, verified via real dev server |
| 5-2 | ⬜ not-started | — | feat/5-2-edit-controls | — |
| 5-3 | ⬜ not-started | — | feat/5-3-assetpicker | — |
| 5-4 | ⬜ not-started | — | feat/5-4-scene-ops | — |
| 5-5 | ⬜ not-started | — | feat/5-5-man-hoan-thien | — |
| 5-6 | ⬜ not-started | — | feat/5-6-man-nghien-cuu | ready-for-dev in sprint-status.yaml |
| 5-7 | ⬜ not-started | — | feat/5-7-man-noi-dung | — |
| 5-8 | ⬜ not-started | — | feat/5-8-runningstate-component | — |
| 5-9 | ✅ done | 6 | feat/5-9-versionswitcher-so-sanh-history | Built on this session's shared worktree branch (worktree-agent-a656b3c581babad19), not a separate checked-out feat/* branch — matches sibling tasks 4-1..4-4 in this same worktree. VersionSwitcher dropdown (list+stale badge+tooltip+empty-state), readonly Xem overlay, So sánh (text side-by-side + scene-diff list, BR-4 prefix+color a11y), Khôi phục via the single 1-5 service + real staled_steps-driven stale cascade (new `StepStatus="stale"` + `STATION_VERSIONING_STEPS` mapping on PipelineStepper), restore disabled while RUNNING (AC-5), History audit route. Contract change (additive): `GET .../versions/{version}` returning content, since VersionOut/compare never expose raw content for the 4 content-bearing steps — see api-spec.md §3 + state/5-9.json decisions. Also fixed the 4-4-flagged cross-cutting bug for just this router: added `prefix="/api"` (projects/runs/scenes/claims/sources still need the same fix). 48/48 frontend vitest + 13/13 backend pytest (versioning) + 2/2 new Playwright e2e green; pre-existing unrelated login.spec.ts flake confirmed (fails alone, untouched by this task) and logged rather than fixed. |
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

## 2026-07-17 (later) — merge reconciliation + full test run findings

1-7 merged to main. While reconciling, discovered worker-B's worktree content (3-1..3-5, 5-1, 4-1, 1-3 partial) had *already* been merged into main by a prior session (commits `760d0de`..`d37a9ab`..`24ac6b2`, then `d937b44`/`0d33718`/`be4699a`) — this file and `sprint-status.yaml` were stale relative to main's actual git history at the point this session started. Fixed several pre-existing bugs blocking the whole backend test suite from even collecting: `TTSResult.cache_key` slots/method name collision (`app/adapters/base.py`), missing `DateTime` import (`app/models/api_key.py`), missing `TransitionError`/`validate` exports (`app/services/state_machine_edges.py`), missing `LLMAdapter` import (`app/adapters/llm/embedding_bge_m3.py`), missing `registry.unregister` (`app/adapters/registry.py`).

**After those fixes, full `pytest` run: 102 failed / 122 passed / 3 errors.** These failures are real, pre-existing gaps in the 3-3/3-4/3-5/1-5/event-bus work that landed via the worktree merge — NOT caused by the 1-7 merge itself (isolated `test_user_admin_service.py` run is 9/9 green). Whoever picks up these tasks needs to fix, in roughly this order of blast radius:
- `tests/unit/core/test_router.py` (3-2): `ProviderRouter.__init__()` doesn't accept a `settings=` kwarg the tests expect — signature drift.
- `tests/unit/services/test_api_key_service.py` + `tests/security/test_api_key_plaintext.py` (3-4): Fernet key fixture/config isn't a valid 32-byte urlsafe-base64 key; `mask()` helper behavior doesn't match test expectations.
- `tests/unit/services/test_cost_service.py` (3-5): code accesses `.get()` on a SQLAlchemy `Row` (should use `Row._mapping` or a dict conversion); one method returns an unawaited coroutine subscripted directly.
- `tests/unit/services/test_provider_status_service.py` (3-5/3-2 boundary): imports `_REGISTRY` from `app.adapters.registry` — that name doesn't exist (registry's private dict is `_registry`, lowercase) — likely a stale import from before a rename.
- `tests/unit/adapters/tts/test_mock_adapter.py` (2-4/3-3 boundary): `MockTts` methods (`available`, `synthesize`) appear to be `async def` when the adapter base/tests expect sync, or vice versa — coroutines returned instead of results.
- `tests/unit/test_event_envelope.py` + `state_machine.py` (1-4/1-5 boundary): `ProjectStateMachine.transition()` signature mismatch with what the event-envelope tests call it with; a test also expects `EDGES` to have an `.edges` attribute (looks like EDGES was expected to be an object, not a plain dict, in that test file — reconcile which shape is canonical, this file's `EDGES: dict[...]` predates that test).
- `tests/unit/test_health.py`: `asyncpg` not installed in the dev environment — either add it to `pyproject.toml` deps or confirm it's already there and only missing from this sandbox's installed packages.

None of this blocks other unrelated tasks (4.x, 5.x, 6.x etc. don't import these modules), so the run should continue in parallel rather than stopping for it — flagged here per `rules/autonomy-policy.md` async-escalation guidance. Whichever agent resumes 3-2/3-3/3-4/3-5/1-5 should treat this list as its starting DoD checklist rather than re-discovering it.

## Follow-up required from worker-B (not done in this reconciliation pass)

Worker-B's worktree (`.claude/worktrees/agent-a3b47cc427c4448c4`, branch `worktree-agent-a3b47cc427c4448c4`) has 9 unpushed commits with real, substantive work bundled together across tasks **1-3, 1-7, 2-3, 2-4, 3-1, 3-2, 3-3, 3-4, 3-5, 5-1**. Most of that content (1-3's projects API, 1-7's users.py+admin UI, 2-3, 2-4, 3-1, 3-2) is *already superseded* by what's on main or on other feat/* branches — but **3-3 (LLM adapters), 3-4 (API key management), 3-5 (cost tracking)** have no other home: this worktree is the only place that work exists. Worker-B needs to split those 3 tasks' commits onto their own `feat/3-3-llm-adapters`, `feat/3-4-api-key-management`, `feat/3-5-cost-tracking-daily-cap-man-providers` branches and push, before those tasks can be marked done or built upon further. (5-1's workspace UI has since been re-verified, fixed, and completed on `feat/5-1-project-workspace-topbar-stepper` — see below.)

## 2026-07-17 (later still) — 5-1 re-verification + repo-wide vitest fix

5-1 was marked "blocked, needs worker-B" above, but the workspace UI files were actually already on `main` (commit `d37a9ab`). Re-verified against the task's Scope/AC/DoD instead of trusting the file-existence check, and found the code did not actually work:

- **Rules-of-Hooks violation**: `SceneFormPanel.tsx` called `useMemo` at module scope, not inside the component.
- **Wrong import path**: `Topbar.tsx` imported `StatusBadge` from `./ui/status-badge` (would resolve to a nonexistent `components/workspace/ui/status-badge`) instead of `@/components/ui/status-badge`.
- **Export/prop mismatch**: `layout.tsx` imported `Topbar`/`PipelineStepper` as named exports when both are `export default`, and passed `initialState={{projectId}}` instead of the required `projectId` prop — this would never have typechecked clean.
- **Next.js 15 API**: `layout.tsx` destructured `params` synchronously; Next 15 makes `params` a Promise even for Client Components — fixed via `use(params)`.
- **Dead code**: an unused `workspace-store.ts` (zustand) duplicated `workspace-context.tsx` (the actually-wired React Context) and was never imported by anything — deleted rather than adding the missing zustand dependency for a file nothing uses.
- **Real a11y/UX bug caught by a test**: `PipelineStepper.tsx` used the native `disabled` attribute on locked stations. Disabled elements don't fire hover/focus events in real browsers, which silently broke the BR-2 "hover a locked station to see why" tooltip. Switched to `aria-disabled` only.
- **Zero backend**: no `GET/PUT/POST .../approve` scenes API existed at all, despite the task depending on it. Added `app/api/scenes.py` + `app/services/scene_service.py` (scenes live in the existing `step_versions` step='scene_set' insert-only rows; approval is a separate `scene_approvals` table, never added to the `Scene` render contract itself — see task `state/5-1.json` decisions for the full rationale) + `docs/specs/api-spec.md` §6 contract update.
- **Repo-wide, not just 5-1**: `npm test` was completely broken for the *entire* frontend — `vitest.config.ts` imported `@vitejs/plugin-react` and tests imported `@testing-library/react`, neither declared in `package.json`; no `@/*` alias resolution in `vitest.config.ts`. Fixed once, unblocks every other frontend task's test verification step, not just 5-1's.
- Also fixed, while touching the model registry to make the new scenes API importable at all: `app/models/__init__.py` was empty (SQLAlchemy `relationship()` string lookups like `"Project"` silently fail until something forces full mapper configuration — nothing had, until the scenes API's query did); `status_history.py` was missing the `relationship` import; `project.py` had an indentation bug that broke Python parsing entirely; `step_versions.project_id` had no `ForeignKey` at the ORM *or* DB level despite a `relationship()` assuming one existed (added migration `007_add_step_versions_fk`).

**Lesson for future reconciliation passes**: "the files exist on main" is not the same as "the task is done" — always re-run typecheck/lint/test and a real dev-server hit before trusting a prior file-existence audit, per `rules/testing.md`'s browser-verification rule. This is the second time in this run a from-worktree merge landed code that never actually compiled/ran (see the 1-7 backend bug list above) — worth promoting to a standing checklist item in `checklists/before-merge.md` if it recurs a third time.
