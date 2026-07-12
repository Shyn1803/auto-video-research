# Workflow: Database Migration

**Inputs:** a schema change need (new table, column, index, partitioning change).

**Steps**
1. Database Engineer agent checks `docs/specs/database-schema.md` ERD for consistency with the proposed change.
2. Write an Alembic migration — never edit an already-applied migration.
3. If the table is high-volume (`llm_usage`, `schedule_runs`, `metrics`-like), plan monthly partitioning from the start.
4. Check for the "never overwrite a version" and "`scene_id` immutable" invariants if the migration touches `step_versions` or `scenes`.
5. Write a rollback plan for any migration that locks a large table or is otherwise risky.
6. Update `docs/specs/database-schema.md` ERD + this file's "đổi contract" note in the PR.

**Quality Gates:** migration is reversible or has an explicit accepted-risk note; ERD doc updated same-PR.

**Outputs:** migration file, ERD update, PR with Contract changes section.

**Success Criteria:** schema change ships without a manual out-of-band DB fix later.
