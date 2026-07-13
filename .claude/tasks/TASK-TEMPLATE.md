# Task {id}: {title}

**Points:** {n}đ · **Epic:** {n} — {epic name} · **Depends:** {task ids or —} · **FR:** {FR ids}
**State file:** [`state/{id}.json`](state/{id}.json) — create on first claim, `status: not-started` → `in-progress` → `blocked`/`done`. Read it FIRST if resuming (see "Resuming after interruption" below).
**Branch:** `feat/{id}-{slug}` (checkout from latest `main`)

> Protocol reference: [workflows/autonomous-task-execution.md](../workflows/autonomous-task-execution.md) — claim/branch/retry/git/retrospective mechanics live there, not repeated per task.

## User story
{As a ..., I want ..., so that ...}

## Why
{one paragraph, from docs/backlog}

## Scope
**In:** {...}
**Out:** {...}

## Business Rules
{numbered list, from docs/backlog}

## Acceptance Criteria
{numbered, tagged happy/biên/lỗi/CI, from docs/backlog — unchanged, this is the contract}

## Data & API
{tables, endpoints, contract-change flag — from docs/backlog}

## Decisions already locked
{from docs/backlog, if any}

## Execution Steps

Work these in order. Update `state/{id}.json` after **every** step (mark it `done` with the commit SHA, or `blocked` with a reason) before moving to the next — this is what makes the task resumable. Each step ends with a commit + push checkpoint (branch is already pre-authorized for push, see workflow doc); don't batch multiple steps into one commit.

### Step 1: {short name}
- **Files:** {exact paths, from context/folder-structure.md conventions}
- **Do:** {concrete instruction — literal function/class/file names, which pattern to follow (link patterns/*.md), no "implement X" hand-waving}
- **Verify:** `{exact command}` → expect {exact success signal: exit 0 / specific output / test name passing}
- **On failure:** transient (network/port/flaky) → retry same step up to 3× with short backoff, log each attempt in state file; logic/config error → stop retrying, invoke the `systematic-debugging` skill; still failing after 3 attempts → mark step + task `blocked` in state file with `blocked_reason`, note it in `memory/project-memory.md` Open Questions, move to a different unblocked task per `rules/autonomy-policy.md`.
- **Commit:** `git add {paths} && git commit -m "{type}({scope}): {id} {step summary}"` → `git push` (feature branch; pre-authorized, no confirmation needed)

### Step 2: {short name}
{same shape as Step 1}

{... as many steps as needed to cover every Acceptance Criterion and Business Rule above; a step should be small enough that "on failure" leaves a clean, resumable checkpoint — avoid one giant step that does the whole task}

### Step N: Wire up tests + verify all Acceptance Criteria
- **Files:** `tests/unit/...`, `tests/integration/...` (mirror module under test, per `rules/folder-structure.md`)
- **Do:** one test per Acceptance Criterion tagged above (happy/biên/lỗi/CI); mock HTTP with `respx` for adapters per `rules/testing.md`.
- **Verify:** `{test command}` → all AC-mapped tests pass.
- **On failure:** same policy as above.
- **Commit:** as above.

## Definition of Done
Standard DoD ([tasks/README.md](README.md)) + [checklists/before-merge.md](../checklists/before-merge.md) + this task's own DoD line above if present.

## Retrospective (mandatory — CLAUDE.md §8, run once DoD passes, before marking task `done`)

Answer inline, then act on it — don't leave it only in the state file:
1. What changed? (one line)
2. What was learned that isn't already written down? (new constraint, gotcha, hidden dependency, framework limitation)
3. Where does it belong? Apply the [knowledge-curator](../agents/knowledge-curator.md) decision rule (rule / pattern / anti-pattern / ADR / postmortem / `memory/project-memory.md`) — pick the narrowest fitting type, don't create a new file if an existing one already covers it.
4. File it. Then set `state/{id}.json` → `status: done`, mark `done` in `sprint-status.yaml`, and move to the next unblocked task without waiting for confirmation.

## Resuming after interruption

If `state/{id}.json` exists and `status` is `in-progress` or `blocked`:
1. Read `current_step` and `steps[]` — do **not** restart from Step 1.
2. Skip every step already `done`.
3. Resume at the first `pending` or `blocked` step, and **respect its existing `attempts` count** (don't reset the retry budget — 3 attempts total per step, across restarts, not per session).
4. If `status` is `blocked`, first check whether `blocked_reason` is now resolved (e.g. an earlier dependency task is now `done`, an env issue was fixed by another task) before retrying; if still blocked for the same reason, leave it blocked and pick a different unblocked task instead of looping.
