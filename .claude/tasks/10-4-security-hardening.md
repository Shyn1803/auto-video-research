# Task 10-4: Security hardening

**Points:** 4đ · **Epic:** 10 — Release · **Depends:** toàn hệ (all prior tasks) · **FR:** NFR-4
**State file:** [`state/10-4.json`](state/10-4.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/10-4-security-hardening` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
As an operator, I want hệ thống khoá chặt trước khi ra production, so that key người dùng, nội dung và hạ tầng không thành điểm yếu khi hệ chạy công khai 24/7.

## Why
NFR-4 tổng nghiệm thu. Nguyên tắc: kiểm soát bằng **test tự động** (RBAC từ OpenAPI, secret-in-log, dependency scan) — không bằng trí nhớ reviewer. See [rules/security.md](../rules/security.md) and [checklists/security-review.md](../checklists/security-review.md).

## Scope
**In:** rate limit toàn API (user+IP, config); security headers (CSP Next, HSTS); CORS prod allowlist; test tự động "log không chứa secret" (mở rộng pattern 3-4/9-4 toàn hệ); `make rotate-fernet` + drill staging; pip-audit/npm-audit CI fail-on-critical; images non-root + pin digest; RBAC test sinh từ OpenAPI (route thiếu khai báo quyền → CI fail).
**Out:** pentest ngoài (v1.1 nếu thương mại hoá); WAF; SSO.

## Business Rules
1. Route mới bắt buộc khai báo quyền — enforced bằng test sinh từ OpenAPI.
2. Rotation Fernet không downtime — 2-key giai đoạn chuyển, re-encrypt batch.
3. Rate limit trả 429 chuẩn error format + Retry-After.
4. CSP không unsafe-inline cho script (Next config phù hợp).

## Acceptance Criteria
1. **(happy)** Checklist Bảo mật `docs/plan.md` §6 tick đủ kèm bằng chứng (screenshot/log/CI link).
2. **(biên/BR-2)** Rotation trên staging: hệ hoạt động xuyên suốt; key cũ hết hiệu lực sau hoàn tất.
3. **(CI/BR-1)** Route demo không khai quyền → CI fail; dependency critical giả → fail.
4. **(BR-3)** Vượt rate limit → 429 + Retry-After; UI toast lịch sự.
5. **(secret-log)** Test toàn hệ grep secret pass (chạy trên log integration test đầy đủ).

## Data & API
Middleware + CI jobs. Contract change: không (429 đã trong spec).

## Decisions already locked
- ⏳ Rate limit mặc định 100 req/phút/user, 20 req/phút cho auth endpoints.

## Execution Steps

Work these in order. Update `state/10-4.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint; don't batch multiple steps into one commit. Every step below maps to one line of [rules/security.md](../rules/security.md) and one line of [checklists/security-review.md](../checklists/security-review.md) — verify each explicitly, don't summarize "hardened security" without evidence.

### Step 1: RBAC test generator from OpenAPI (BR-1, rules/security.md "RBAC middleware on every route, not opt-in")
- **Files:** `backend/app/scripts/gen_rbac_tests.py` (or wherever codegen scripts live per `rules/folder-structure.md`), `backend/tests/integration/security/test_rbac_coverage.py`.
- **Do:** Build a generator that reads the OpenAPI spec and asserts every route declares an explicit permission/role requirement; a route with no declared permission fails CI. This is BR-1's enforcement mechanism — "a route missing a permission declaration → CI fail" (AC3), not a manual audit.
- **Verify:** add one deliberately-undeclared demo route → generator/CI fails on it; remove the demo route → CI green. Run against the full current route set → passes (or lists genuine gaps to fix in this step).
- **On failure:** transient (spec fetch flake) → retry 3×; logic error in generator → `systematic-debugging`; still failing after 3 → block, log in `memory/project-memory.md`.
- **Commit:** `git add backend/app/scripts/gen_rbac_tests.py backend/tests/integration/security && git commit -m "feat(security): 10-4 RBAC test generator from OpenAPI, CI-fails on undeclared route (BR-1/AC3)" && git push`

### Step 2: Rate limiting — user+IP, 429 + Retry-After (BR-3, rules/security.md "Rate limiting by user + IP")
- **Files:** `app/middleware/rate_limit.py`, `app/config.py` (config-driven limits, not hardcoded), frontend toast handler for 429.
- **Do:** Add rate-limit middleware applied to all API routes, keyed by user+IP, configurable via env/settings (default 100 req/min/user general, 20 req/min for auth endpoints per Decisions already locked). Exceeding the limit returns `429` in the project's standard error format with a `Retry-After` header (BR-3). Frontend shows a polite toast on 429, not a raw error dump.
- **Verify:** integration test — burst >100 req/min from one user → subsequent requests return 429 with `Retry-After` header and standard error body; auth endpoint burst >20/min → same behavior at the lower threshold.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add app/middleware/rate_limit.py app/config.py tests/integration && git commit -m "feat(security): 10-4 rate limit user+IP, 429+Retry-After (BR-3)" && git push`

### Step 3: Security headers — CSP (no unsafe-inline script), HSTS (BR-4)
- **Files:** `next.config.js`/`next.config.ts` (frontend headers config), `app/middleware/security_headers.py` (backend, if API also serves any HTML).
- **Do:** Configure Next.js security headers: CSP without `unsafe-inline` for `script-src` (BR-4 — requires nonce-based or hashed inline scripts if any exist, not a blanket allow), HSTS enabled. This is the one item with no compromise per BR-4 wording ("CSP không unsafe-inline cho script").
- **Verify:** manual check — load the app, inspect response headers for `Content-Security-Policy` (no `unsafe-inline` in `script-src`) and `Strict-Transport-Security`; browser console shows no CSP violations on a normal page load.
- **On failure:** a script blocked by CSP → not transient, fix by moving to nonce/external file, don't loosen the policy to `unsafe-inline` as a shortcut (that's the exact anti-pattern BR-4 forbids).
- **Commit:** `git add next.config.ts app/middleware/security_headers.py && git commit -m "feat(security): 10-4 CSP (no unsafe-inline script) + HSTS headers (BR-4)" && git push`

### Step 4: CORS production allowlist (rules/security.md "CORS allowlist, not wildcard")
- **Files:** `app/main.py` or `app/config.py` CORS middleware config.
- **Do:** Replace any wildcard/dev-permissive CORS config with an explicit production allowlist driven by env config (never `os.environ` read directly inside a business module — through `ProviderSettings`/app config per `rules/code-style.md`).
- **Verify:** integration test — request from an allowlisted origin succeeds with correct CORS headers; request from a non-allowlisted origin is rejected.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add app/main.py app/config.py tests/integration && git commit -m "feat(security): 10-4 CORS production allowlist, no wildcard" && git push`

### Step 5: Secret-in-log test extended system-wide (AC5, extends 3-4/9-4 pattern)
- **Files:** `backend/tests/integration/security/test_no_secret_in_logs.py`.
- **Do:** Extend the existing secret-grep pattern from stories 3-4/9-4 to run across the *full* integration test suite's log output, not just the adapter/queue modules it originally covered — per `rules/logging.md` ("Never log a raw secret"). Grep for API key patterns, JWT structure, Fernet master key.
- **Verify:** run the full integration suite with logging captured, grep output for secret patterns → zero matches (AC5 "chạy trên log integration test đầy đủ").
- **On failure:** a match found → not transient, this is a real leak — locate the log call and fix to log identifiers only (provider name, key id, last-4) per `rules/logging.md`, not transient/retry.
- **Commit:** `git add backend/tests/integration/security/test_no_secret_in_logs.py && git commit -m "test(security): 10-4 system-wide secret-in-log grep test (AC5)" && git push`

### Step 6: `make rotate-fernet` + staging rotation drill (BR-2)
- **Files:** `Makefile` (`rotate-fernet` target), `app/security/fernet_rotation.py` (2-key transition logic).
- **Do:** Implement Fernet key rotation with a 2-key transition window (decrypt-with-old, encrypt-with-new, batch re-encrypt) so rotation has zero downtime per BR-2. Run the actual drill on staging (not just unit-test the logic) and record start/end time + any hiccups in the runbook.
- **Verify:** staging drill — system serves requests throughout rotation with no error spike; old key confirmed rejected for new encryptions after rotation completes; timing recorded in `docs/runbook.md`.
- **On failure:** rotation causing downtime → not transient, this is a design bug in the 2-key transition, not a flaky test — fix before re-attempting the drill.
- **Commit:** `git add Makefile app/security/fernet_rotation.py docs/runbook.md && git commit -m "feat(security): 10-4 make rotate-fernet + staging drill, zero-downtime (BR-2)" && git push`

### Step 7: Dependency scanning — pip-audit/npm-audit CI, fail-on-critical
- **Files:** CI workflow config (`.github/workflows/` or equivalent per `context/build-process.md`).
- **Do:** Add `pip-audit` and `npm-audit` (or equivalent) CI jobs that fail the build on any critical-severity finding.
- **Verify:** inject a known-vulnerable dependency version in a throwaway branch/test → CI job fails; revert → CI green (AC3 "dependency critical giả → fail").
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add .github/workflows && git commit -m "feat(ci): 10-4 pip-audit/npm-audit fail-on-critical" && git push`

### Step 8: Non-root images + pinned digests
- **Files:** `Dockerfile*` for all services (API, render-worker, voice/asset worker per Epic 9).
- **Do:** Ensure every Dockerfile runs as a non-root user and base images are pinned by digest (not floating tags) per this task's scope line.
- **Verify:** `docker run` each image → confirm process runs as non-root (`whoami` inside container ≠ root); `docker inspect` confirms digest-pinned base image.
- **On failure:** standard retry/debugging policy.
- **Commit:** `git add Dockerfile* docker-compose*.yml && git commit -m "feat(security): 10-4 non-root images + pinned base image digests" && git push`

### Step 9: Full Security Checklist evidence pass (AC1, DoD)
- **Files:** PR description, `docs/plan.md` §6 checklist (tick items), [checklists/security-review.md](../checklists/security-review.md).
- **Do:** Walk every line of `checklists/security-review.md` against the actual system and attach evidence (screenshot/log/CI link) per item: no raw secret logged, Render Worker cannot reach external URL (SSRF check per `rules/security.md`), `ALLOW_PAID=false` blocks paid providers even with a valid key, every asset has required license fields, RBAC enforced server-side not just UI-hidden, rate limit + CORS in place, admin mutations audit-logged. Tick `docs/plan.md` §6 Bảo mật items with evidence links.
- **Verify:** every checklist line has attached evidence; no item marked done without proof.
- **On failure:** any unverifiable item → not transient, this is exactly what `release-manager.md`'s decision rule blocks on ("a release blocks if any Release Checklist item is unverified") — do not tick it, leave it open and document why in the PR.
- **Commit:** `git add docs/plan.md && git commit -m "docs(security): 10-4 full security checklist evidence pass (AC1)" && git push`

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + [checklists/security-review.md](../checklists/security-review.md) + RBAC test generator là deliverable tái dùng vĩnh viễn; drill rotation ghi thời gian vào runbook.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/10-4.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/10-4.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
