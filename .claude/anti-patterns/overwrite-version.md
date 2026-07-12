# Anti-pattern: Overwriting a Version

**Problem:** updating a `step_versions` or `scenes` row in place (UPDATE) instead of inserting a new version row, when the content is user-editable/pipeline-derived.

**Symptoms**
- `UPDATE step_versions SET content_jsonb = ... WHERE id = ...` instead of inserting a new row with `parent_version` set.
- A "quick fix" edit endpoint that mutates the current version rather than creating version N+1.
- Restore implemented as "copy old content back into the current row" instead of creating a new current state and marking downstream `stale`.

**Impact:** destroys the audit/restore/compare capability that's a stated non-negotiable design principle (SRS §10, glossary.md rule 1); breaks diffing; breaks the `stale` flagging mechanism that warns users when upstream data changed under them.

**Correct Solution:** [patterns/scene-versioning.md](../patterns/scene-versioning.md) — every edit is a new version; restore creates new state; downstream marked `stale`, never deleted.

**Detection:** any UPDATE statement (or ORM `.save()` on an existing instance) touching `content_jsonb`/`scene_json` in `step_versions`/`scenes` outside of non-content metadata fields (like `stale` flag itself).

**How to Avoid:** Database Engineer agent reviews any migration or service code touching these tables for in-place content mutation; service layer should expose `create_version()`, never `update_version_content()`.
