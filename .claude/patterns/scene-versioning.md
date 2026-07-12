# Pattern: Scene / Step Versioning

**Problem:** users need to edit, regenerate, restore, and compare content at every pipeline step without ever losing prior state, while keeping downstream data correctly flagged when an upstream step is restored.

**Solution (SRS §6, glossary.md rules 1-2):**
- Every step (`research/outline/script/storyboard/scene_set/produce/render/publish`) stores versions in `step_versions(project_id, step, version, parent_version, content_jsonb, stale, created_by, created_at)`.
- **Never overwrite** — every edit creates a new version row. The latest non-stale version is "current."
- Restoring an older version doesn't delete newer versions — it creates a new current state; anything downstream that was derived from a now-superseded version gets marked `stale` (still usable, UI warns).
- `scenes` carry their own immutable `scene_id` — reordering only changes `scene_number`; diff/cache both key off `scene_id`/`content_hash`, never position.
- Comparison: text diff for outline/script; `scene_id`-keyed diff for storyboard/scene; visual side-by-side diff is a later-phase enhancement, not a Phase 1 requirement.

**When to use:** any content-bearing table where a user can edit/regenerate/restore. Don't add a table that stores "the current value" with in-place UPDATE for anything user-editable and pipeline-derived — that's how stale-detection and restore become impossible.
