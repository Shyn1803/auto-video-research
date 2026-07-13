# Workflow: Autonomous Task Execution

**When to use:** every time an agent (or agent team) picks up work from [tasks/](../tasks/). This is the mechanics layer — claim, branch, execute, retry, commit/push, retrospective — referenced from every [tasks/TASK-TEMPLATE.md](../tasks/TASK-TEMPLATE.md)-shaped task file instead of being repeated 65 times.

Builds directly on [rules/autonomy-policy.md](../rules/autonomy-policy.md) (decide-and-continue, async escalation) and [rules/git.md](../rules/git.md) (branch/commit conventions) — read those first if unfamiliar; this file adds the retry/resume/state-tracking/git-automation specifics that make **long, unattended runs** possible.

## The loop

1. **Claim.** Pick the highest-priority unblocked task per the dependency graph in [tasks/README.md](../tasks/README.md#parallel-execution-tracks-per-docsplanmd). Set it `in-progress` in `docs/backlog/stories/sprint-status.yaml`. Read (or create) `tasks/state/{task-id}.json` — see [tasks/state/README.md](../tasks/state/README.md) for the resume algorithm if a state file already shows progress.
2. **Branch.** `git checkout -b feat/{task-id}-{slug}` from latest `main` (skip if resuming an existing branch — check `state.branch` first). Record `branch` in the state file.
3. **Execute.** Work the task file's Execution Steps in order. After every step:
   - Run its `Verify` command.
   - On success: commit + push (see "Git automation" below), set that step `done` with `commit_sha`, advance `current_step`, update `updated_at`.
   - On failure: apply the **Retry policy** below.
   - Refresh the matching row in [tasks/state/RUN-STATUS.md](../tasks/state/RUN-STATUS.md) in the same commit as the state-file change.
4. **Definition of Done.** Once all steps are `done`, run [checklists/before-merge.md](../checklists/before-merge.md) + the task's own DoD line.
5. **Retrospective.** Mandatory, not optional — see "Self-learning" below.
6. **Close out.** Set `state.status = done`, mark the task `done` in `sprint-status.yaml`, commit+push the final state, and **move directly to the next unblocked task** — do not stop to ask "should I continue?". This is the entire point of the manifest (per `tasks/README.md` line 7: "do not stop and wait for confirmation between tasks").

## Retry policy

Applied per Execution Step, tracked in `state.steps[].attempts` (cumulative across restarts — a resumed session does not reset the budget):

| Failure type | Action |
|---|---|
| Transient (network blip, port-in-use, flaky test, rate-limit) | Retry the **same step** immediately, up to **3 attempts total**, short backoff between (a few seconds — this isn't a service, no need for long exponential waits). Log each attempt's error in `steps[].last_error`. |
| Non-transient (logic bug, wrong assumption, failing assertion that isn't flaky) | Do **not** blind-retry. Invoke the `systematic-debugging` skill (if available) or apply first-principles root-cause analysis before trying again — a 4th identical attempt without a change in approach is not a retry, it's a stall. |
| Still failing after 3 attempts on a step | Mark the step **and** the task `blocked` in the state file with a specific `blocked_reason` (not "failed" — say *why*). Log it in `memory/project-memory.md` Open Questions so a human or a later session sees it without re-discovering it. **Move to a different unblocked task** — per the async-escalation rule in `rules/autonomy-policy.md`, a blocked task never halts the whole run. |

A task/step that comes back into scope later (e.g. a dependency that was blocking it just went `done`) gets picked up again by re-running the resume algorithm — the attempt counter does **not** reset just because time passed, only if the actual blocking condition changed (e.g. a different root cause is now being fixed, worth a fresh 3 attempts; same root cause, no).

## Git automation scope (durable, pre-authorized — see `CLAUDE.md` §3)

Per explicit user decision, the following are pre-authorized for this project's autonomous task runs and require **no per-action confirmation**:

- `git checkout -b feat/{task-id}-{slug}`
- `git add` + `git commit` (Conventional Commits + task ID in the subject, per `rules/git.md`) — after every Execution Step, not just at task end.
- `git push` / `git push -u origin feat/{task-id}-{slug}` — **feature branches only.**

**Still gated (unchanged, ask first or don't do it at all):**
- Push to `main`/`master` directly.
- Force-push (`--force`, `--force-with-lease`), `git reset --hard`, `git rebase` on a shared branch, `--no-verify`.
- Opening/merging a pull request — pushing a branch makes it visible on the remote, but opening a PR is a "publish" action per the platform's own action categories; that step still gets flagged for the user (or a `release-manager`-owned step) rather than done silently. If the user separately authorizes auto-PR for a given run, note that explicitly in `memory/project-memory.md` so it's not re-litigated per task.

Pushing a feature branch is reversible (delete the branch, force-push is still blocked so history on it is append-only from this agent's side) and does not affect `main` — that's what makes it safe to pre-authorize per the safety-rule carve-out for "durable instructions."

## Self-learning (mandatory, ties into existing mechanism — doesn't duplicate it)

Every task's Retrospective section (see `TASK-TEMPLATE.md`) is not a suggestion — it's Step "last" of the loop above, gated by DoD passing. It uses the **existing** [knowledge-curator](../agents/knowledge-curator.md) decision rules (repeated code-style correction → rule; reusable solution used twice → pattern; generalizable failure → anti-pattern; structural tradeoff → ADR; fixed bug with root cause → postmortem; sprint-level state → `memory/project-memory.md`; one-off feedback → wait for a 2nd occurrence). Do not invent a second learning mechanism — file through this one, per `CLAUDE.md` §8.

## Resuming a long-running or interrupted run

Starting (or restarting) a session against this backlog:
1. Read `tasks/state/RUN-STATUS.md` for the rollup — this answers "where are we" in one glance without opening 65 files.
2. For any task showing `in-progress`/`blocked`, read its `tasks/state/{id}.json` and resume per the algorithm in `tasks/state/README.md` — never restart a task from Step 1 if its state file shows prior progress.
3. Continue the loop above from step 3 (Execute) for resumed tasks, or step 1 (Claim) for fresh ones.
