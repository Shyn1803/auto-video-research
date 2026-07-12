# Prompt: Database Design

```
Design this schema change against docs/specs/database-schema.md.
Confirm:
- No overwrite of versioned content — new step_versions row, not an update, for any content edit.
- scene_id remains immutable if scenes are involved.
- High-volume tables get monthly partitioning from the first migration (llm_usage/schedule_runs/metrics pattern).
- JSONB used for content that changes structure often; typed columns for queryable/indexed fields.
Produce: Alembic migration outline, updated ERD snippet, rollback plan if the migration is risky (large table lock).
```
