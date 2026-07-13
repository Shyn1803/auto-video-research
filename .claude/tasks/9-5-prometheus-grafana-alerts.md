# Task 9-5: Prometheus + Grafana + alerts

**Points:** 3đ · **Epic:** 9 — NATS, Workers & Observability · **Depends:** 9-2, 7-4 · **FR:** NFR-5
**State file:** [`state/9-5.json`](state/9-5.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/9-5-prometheus-grafana-alerts` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

> **Sequencing note:** part of Epic 9, started only after Epic 6 (M4) is `done` (ADR-0001, see `tasks/README.md`). Depends on `9-2` (worker metrics source) and `7-4` (notification channel) — verify both `done` before claiming.

## User story
As an operator, I want metrics và alert cho API, queue, worker, tài nguyên, so that biết hệ thống ốm trước khi user biết.

## Why
NFR-5. Nguyên tắc "alert phải actionable" (BR-2): mỗi alert trỏ mục runbook — chống alert fatigue từ ngày đầu.

## Scope
**In:** FastAPI instrumentator; exporters NATS/postgres/node; Grafana provisioned-as-code (API latency/error, queue depth, worker throughput, GPU/disk); alert rules (FAILED rate, DLQ>0, disk>80%, worker down, cost cap) → notification 7-4; compose profile monitoring.
**Out:** Langfuse/Sentry (9-6); SLO chính thức (v1.1); log aggregation tập trung (docker logs đủ v1).

## Business Rules
1. Dashboards là code trong repo — dựng lại container về nguyên trạng.
2. Mỗi alert rule kèm annotation link mục runbook xử lý.
3. Alert có cooldown — không lặp <15' cùng rule.

## Acceptance Criteria
1. **(happy)** `--profile monitoring up` → dashboards có data thật từ hệ đang chạy.
2. **(diễn tập)** Giết worker / đổ FAIL / vượt cap → 3 alert đến kèm link runbook đúng mục.
3. **(BR-1)** Xoá container Grafana dựng lại → dashboards nguyên vẹn.
4. **(BR-3)** Rule nổ liên tục → tin cách nhau ≥15'.

## Data & API
Hạ tầng thuần. Contract change: không.

## Decisions already locked
- ⏳ Retention Prometheus 30 ngày.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + diễn tập 3 alert ghi thành script (`make drill-alerts`) — tái dùng ở Release Checklist (10-6).

## Execution Steps

Work these in order. Update `state/9-5.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: FastAPI instrumentator + exporters
- **Files:** `backend/app/core/metrics.py`, `docker/docker-compose.prod.yml`
- **Do:** Wire a Prometheus instrumentator into the FastAPI app (`backend/app/core/metrics.py`, mounted at `/metrics`) exposing API latency + error-rate histograms per route. Add exporter services to the `monitoring` compose profile: `nats-exporter` (queue depth from `9-1`/`9-2` streams), `postgres-exporter`, `node-exporter` (disk/CPU/GPU host metrics). No business logic reads these directly — this step only exposes metrics, alert rules come in Step 3.
- **Verify:** `docker compose --profile monitoring up -d && curl localhost:8000/metrics` → Prometheus-format output includes API latency histogram; `curl` against each exporter's port returns metrics.
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add backend/app/core/metrics.py docker/docker-compose.prod.yml && git commit -m "feat(observability): 9-5 FastAPI instrumentator + NATS/postgres/node exporters"` → `git push`

### Step 2: Prometheus scrape config + 30-day retention
- **Files:** `docker/monitoring/prometheus/prometheus.yml`, `docker/docker-compose.prod.yml`
- **Do:** Prometheus service in the `monitoring` compose profile scraping the API `/metrics` endpoint and all three exporters from Step 1, on a fixed interval. Retention set to 30 days per "Decisions already locked" (`--storage.tsdb.retention.time=30d`). Config lives as a file in the repo, not typed into the container by hand (ties to BR-1: dashboards/config are code).
- **Verify:** `docker compose --profile monitoring up -d prometheus && curl localhost:9090/api/v1/targets` → all 4 targets (API + 3 exporters) show `health: up`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add docker/monitoring/prometheus/ docker/docker-compose.prod.yml && git commit -m "feat(observability): 9-5 Prometheus scrape config, 30-day retention"` → `git push`

### Step 3: Grafana provisioned-as-code dashboards (BR-1)
- **Files:** `docker/monitoring/grafana/provisioning/datasources/`, `docker/monitoring/grafana/provisioning/dashboards/`, `docker/monitoring/grafana/dashboards/*.json`
- **Do:** Grafana service added to the `monitoring` compose profile with datasource + dashboard provisioning pointed at files under `docker/monitoring/grafana/` (per Grafana's provisioning-as-code convention) — never a dashboard created by hand in the Grafana UI and left un-exported, per BR-1 ("dashboards là code trong repo — dựng lại container về nguyên trạng"). Four dashboards: API latency/error, queue depth (per stream, from `9-1`/`9-4`), worker throughput (from `9-2`/`9-3`), GPU/disk (from node-exporter).
- **Verify:** `docker compose --profile monitoring up -d grafana` → dashboards visible at `localhost:3001` (or documented port) immediately on first boot, no manual import step.
- **On failure:** same policy as Step 1.
- **Commit:** `git add docker/monitoring/grafana/ && git commit -m "feat(observability): 9-5 Grafana provisioned-as-code dashboards (BR-1)"` → `git push`

### Step 4: Alert rules with runbook annotations + cooldown (BR-2, BR-3)
- **Files:** `docker/monitoring/prometheus/alert-rules.yml`, `docker/docker-compose.prod.yml`
- **Do:** Alert rules for: FAILED pipeline-run rate, DLQ>0 (ties to `9-4`'s aggregated alert — this rule feeds the same 7-4 channel, don't build a second alert path for DLQ), disk>80%, worker down (no successful heartbeat/render in window), cost cap exceeded (`DAILY_COST_CAP` from `rules/configuration-env.md`). Every rule carries an `annotations.runbook_url` pointing at the specific `docs/runbook.md` section for that failure mode (BR-2 — "alert phải actionable"). Set `for:`/repeat-interval so no rule re-fires more than once per 15 minutes (BR-3). Wire alert delivery through the existing `7-4` notification channel — no second notification path.
- **Verify:** `pytest backend/tests/unit/observability/test_alert_rules.py -k runbook_links` → every alert rule's `runbook_url` resolves to an existing anchor in `docs/runbook.md`; rule config lints with `promtool check rules docker/monitoring/prometheus/alert-rules.yml`.
- **On failure:** same policy as Step 1.
- **Commit:** `git add docker/monitoring/prometheus/alert-rules.yml docker/docker-compose.prod.yml && git commit -m "feat(observability): 9-5 alert rules with runbook annotations + 15min cooldown (BR-2, BR-3)"` → `git push`

### Step 5: `make drill-alerts` script + persistence check (BR-1)
- **Files:** `Makefile`, `scripts/drill-alerts.sh` (or equivalent per `context/build-process.md` tooling convention)
- **Do:** Script that drills exactly the three AC-2 scenarios in sequence — kill a worker, force a FAILED pipeline run, exceed the cost cap — and asserts each produces a notification via the 7-4 channel with a working runbook link (AC-2). This script is what Definition of Done and the future Release Checklist (10-6) reuse — write it generically enough (documented exit codes, no interactive prompts) that 10-6 can call it unchanged. Also verify BR-1 here: delete and recreate the Grafana container → dashboards return intact (AC-3), since this is the natural place to check it alongside the other drills.
- **Verify:** `make drill-alerts` → exits 0, prints 3/3 alerts confirmed delivered with valid runbook links; manual Grafana container delete/recreate → dashboards unchanged.
- **On failure:** same policy as Step 1.
- **Commit:** `git add Makefile scripts/drill-alerts.sh && git commit -m "feat(observability): 9-5 make drill-alerts script (AC-2 3-alert drill, BR-1 recreate check)"` → `git push`

### Step 6: Full AC coverage tests
- **Files:** `backend/tests/integration/observability/test_monitoring.py`
- **Do:** One test/check per Acceptance Criterion: `--profile monitoring up` yields dashboards with live data from a running system (AC-1); the 3-alert drill from Step 5 delivers with runbook links (AC-2); Grafana container recreate preserves dashboards (AC-3); a rule firing repeatedly is throttled to ≥15 minutes apart (AC-4, use a fast-forwarded/mocked clock rather than a real 15-minute wait).
- **Verify:** `pytest backend/tests/integration/observability/ -v` → all AC-tagged tests pass.
- **On failure:** same policy as Step 1.
- **Commit:** `git add backend/tests/integration/observability/ && git commit -m "test(observability): 9-5 full AC coverage for Prometheus/Grafana/alerts"` → `git push`

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/9-5.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/9-5.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
