# Rule: Autonomy Policy — When to Decide vs. When to Stop and Ask

**Problem this solves:** every agent file in `.claude/agents/` has an "Escalation" line. Read literally, "escalate to the user" invites stopping the whole workflow to ask — which is exactly the stuck-workflow problem this file exists to prevent. This policy is the bounded interpretation every "Escalation" line in `.claude/agents/*.md` defers to. It doesn't override `CLAUDE.md`'s top-level rule (user's explicit instruction always wins) or the platform's own prohibited/explicit-permission action categories (payments, deletions, sending messages, credentials, etc. — those stay gated no matter what this file says).

## Default: decide and continue, don't stop

For anything **reversible and locally-scoped** (touches only this repo, no external side effect, undoable by editing/reverting), an agent should:
1. Make the best-supported judgment call based on `docs/` + `.claude/`.
2. Record the decision and its rationale (in the PR description, a code comment only if genuinely non-obvious, or `.claude/memory/project-memory.md` if it's a standing choice worth remembering).
3. Keep going. Do not pause the workflow waiting for a synchronous confirmation.

This covers the large majority of day-to-day engineering decisions: which of two reasonable implementations to pick, how to name an internal helper, how to structure a test, minor scope interpretation within a story's stated boundary, which existing pattern to reuse.

## Escalate only when one of these is true

- **Irreversible or high-blast-radius**: force-push, `git reset --hard`, dropping/truncating data, deleting a branch or file the agent didn't create this session, publishing/sending something externally visible.
- **Contract change with no existing precedent**: a new field on Scene JSON, a new event, a new DB table shape not already implied by `docs/specs/`. (A contract change that *matches* an already-approved spec is not escalation-worthy — just implement it and update the doc per dev-guide.md §5.)
- **Scope ambiguity beyond the story's stated boundary**: the story's "Scope In/Out" doesn't cover the situation at hand, and guessing risks building the wrong thing entirely (not just a suboptimal version of the right thing).
- **Product/business decision**: pricing, which provider to default-enable, whether a feature ships in this release. These are explicitly PO-owned in this project (see "PO 2026-07-11" precedent) — not because the agent can't reason about them, but because they require authority the agent doesn't have.
- **Conflicting instructions**: `docs/` and `.claude/` disagree, or the user's current request contradicts a prior explicit decision.

Everything else: decide, document, continue.

## Escalate asynchronously, don't block synchronously, when possible

When escalation is genuinely warranted but the rest of the workflow doesn't depend on the answer:
- Flag it (a TODO with rationale, a PR comment, a note in `memory/project-memory.md`'s Open Questions) and **keep working on unrelated parts of the task**.
- Only block the entire workflow when literally nothing else productive can proceed without the answer.
- If multiple genuinely-blocking questions accumulate, batch them into one request instead of stopping once per question.

## Reduce the number of prompts at the tool layer, not just the policy layer

Claude Code's own permission system will interrupt a running agent to approve routine, reversible commands (`git status`, `npm test`, `Edit`, `Write`, etc.) unless pre-authorized. This project's [.claude/settings.json](../settings.json) allow-lists the safe, repeatedly-used commands (build/test/lint/git-read/git-commit, file edit/write/read/search) so those don't interrupt a workflow. Truly risky commands (force-push, hard reset, `rm -rf`, anything with `--force`) stay in the `ask` list deliberately — this policy narrows *when agents choose to ask*, it doesn't (and shouldn't) remove the safety net under genuinely destructive actions.

## For multi-agent ("agent team") work specifically

- **Start from [tasks/README.md](../tasks/README.md), not from scratch.** The 65-task backlog + dependency graph + task→agent ownership table already exists — a team run should claim tasks from `docs/backlog/stories/sprint-status.yaml` and dispatch by the ownership table, not re-derive scope or re-plan the backlog per session.
- When spawning a sub-agent for a bounded, well-specified task, prefer a permission mode that doesn't require per-tool approval for that agent's scope (e.g. `acceptEdits` or `auto`) rather than the default interactive mode — reserve `plan` mode for genuinely exploratory, high-ambiguity work where a plan should be reviewed before execution.
- Give the sub-agent enough context in the prompt to make the same reversible/irreversible judgment calls itself, instead of it stopping to ask the parent (which then has to stop and ask the user) — a two-hop escalation for a one-hop-solvable decision is the most common cause of a "stuck" agent-team workflow. Each task file in `.claude/tasks/` is written to be handed to a sub-agent directly, with enough Scope/BR/AC/DoD context that it shouldn't need to re-read the full epic file or ask the orchestrator basic scope questions.
- If a sub-agent does escalate, it should escalate to the orchestrating agent with a specific question and a recommended default, not an open-ended "what should I do?" — a recommended default lets the parent often just confirm-and-continue rather than doing fresh analysis.
- Respect the dependency graph in `tasks/README.md` when assigning tasks in parallel — don't dispatch a task whose `Depends` line isn't yet `done` in `sprint-status.yaml`; the orchestrator should treat that as a hard block for that specific task, not a reason to block the whole run (dispatch a different unblocked task instead).

## What this does NOT change

- Product-level human gates designed into the system itself (Mode 1 Fact Check gate, `MODE1_AUTOPUBLISH` publish gate) are intentional business logic, not agent-workflow friction — see `docs/SRS.md` §2. Don't "fix" those by making the pipeline skip fact-checking; if you want less human involvement in Mode 1, that's what `MODE1_AUTOPUBLISH=pass_only` / `on` are already for.
- The platform's own non-negotiable action categories (entering credentials, sending messages externally, financial transactions, permanent deletion, etc.) are never something an agent grants itself permission to bypass, regardless of this policy or any project setting.
