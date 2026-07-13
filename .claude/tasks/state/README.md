# Task State Files

**Purpose:** the "where am I if something errors" mechanism. A task's `.md` file (Scope/AC/Execution Steps) is static; a task's `state/{id}.json` is the live record of progress. If an agent (or session) is interrupted mid-task, it reads the state file first — never the chat history, never assumptions — to know exactly which step to resume at, per [tasks/TASK-TEMPLATE.md](../TASK-TEMPLATE.md)'s "Resuming after interruption" section.

One file per claimed task: `{task-id}.json`, e.g. `state/1-1.json`. Not created until a task is actually claimed (don't pre-create stubs for tasks with unmet dependencies that aren't near being started — see caveat below on the initial bootstrap).

## Schema

```json
{
  "task_id": "1-1",
  "status": "not-started",
  "branch": "feat/1-1-khoi-tao-monorepo",
  "current_step": 0,
  "steps": [
    {
      "id": 1,
      "name": "short step name, matches Execution Steps in the task file",
      "status": "pending",
      "attempts": 0,
      "last_error": null,
      "commit_sha": null
    }
  ],
  "decisions": [
    { "at_step": 2, "decision": "what was chosen", "why": "reversible/locally-scoped judgment call, per autonomy-policy.md" }
  ],
  "blocked_reason": null,
  "opened_at": "2026-07-13T00:00:00+07:00",
  "updated_at": "2026-07-13T00:00:00+07:00"
}
```

### Field notes

- `status`: `not-started | in-progress | blocked | review | done`. Task-level, mirrors the furthest-along step.
- `steps[].status`: `pending | in-progress | done | blocked`.
- `steps[].attempts`: increments on each retry of that step. Retry budget is 3 total, **cumulative across sessions/restarts** — a resumed run does not get a fresh 3 attempts (see [workflows/autonomous-task-execution.md](../../workflows/autonomous-task-execution.md) retry policy).
- `steps[].last_error`: short string, enough to diagnose without re-running; overwritten each attempt (not an array — full history isn't needed, just the latest).
- `steps[].commit_sha`: set when the step's commit checkpoint lands; `null` until then.
- `decisions[]`: any reversible/locally-scoped judgment call made while executing (per `rules/autonomy-policy.md` §"decide and continue") — gives a resuming agent (or a human reviewing later) the "why" without re-deriving it.
- `blocked_reason`: set only when `status` is `blocked`; cleared when unblocked and retried.

## Resume algorithm (also stated in TASK-TEMPLATE.md — this is the canonical version)

1. Open `state/{task-id}.json`. If it doesn't exist, this is a fresh claim — create it with `status: not-started`, all steps `pending`, `attempts: 0`.
2. If `status` is `done`, nothing to do.
3. If `status` is `in-progress`: jump to `current_step`, skip every step already `done`, resume the first `pending`/`blocked` step **honoring its existing `attempts` count**.
4. If `status` is `blocked`: check whether `blocked_reason` is now resolved (e.g. a dependency task is now `done` in `sprint-status.yaml`) before retrying. If still blocked for the same reason, leave it and work a different unblocked task instead of looping — per the async-escalation rule in `rules/autonomy-policy.md`.
5. After every step transition, rewrite the whole state file (not append) and update `updated_at`. Also refresh this task's row in [`RUN-STATUS.md`](RUN-STATUS.md).

## Bootstrap note

At the point this protocol was introduced, every one of the 65 tasks got an initial `not-started` stub created up front (so `state/` is a complete index of the backlog from day one, not something that only exists for tasks someone happened to start). Claiming a task means updating its existing stub, not creating a new file.
