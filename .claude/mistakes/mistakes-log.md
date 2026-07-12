# Mistakes Log

Each entry: concrete, generalizable mistake with prevention — not a diary of every typo. See [templates/postmortem.md](../templates/postmortem.md) for bugs with a fuller investigation; this log is for lighter-weight, quickly-recorded mistakes that don't warrant a full postmortem but shouldn't be forgotten either.

---

## M-001: Layout name drift (snake_case vs PascalCase)
**Symptoms:** layout class names inconsistent across docs (9 locations).
**Root Cause:** principle updated in one place, not propagated everywhere it was referenced.
**Fix:** exhaustive grep + standardize.
**Prevention:** [anti-patterns/layout-name-drift.md](../anti-patterns/layout-name-drift.md), [rules/naming.md](../rules/naming.md).
**Related:** [postmortems/2026-07-pascalcase-layout-drift.md](../postmortems/2026-07-pascalcase-layout-drift.md).

## M-002: Ambiguous renderMedia() merge wording
**Symptoms:** spec implied merge might be a second Remotion render call.
**Root Cause:** the Scene/Video composition split was never explicitly defined anywhere.
**Fix:** defined the split explicitly, fixed the wording, formalized as ADR-0009.
**Prevention:** [patterns/scene-video-composition-split.md](../patterns/scene-video-composition-split.md).
**Related:** [postmortems/2026-07-rendermedia-merge-ambiguity.md](../postmortems/2026-07-rendermedia-merge-ambiguity.md).

## M-003: Duplicated "Out:" line in epic-06-render.md story 6.2
**Symptoms:** an edit accidentally produced two identical lines in a story's Scope section.
**Root Cause:** editing tool string-match replaced content in a way that duplicated rather than replaced.
**Fix:** re-read the file section, removed the duplicate.
**Prevention:** always re-read the exact target text before a string-replace edit on Vietnamese/Unicode-heavy content — exact whitespace/escape mismatches are the common failure mode in this repo's docs.
**Related:** none (caught and fixed same session, no standalone postmortem needed).

## M-004: Vague, unenforceable "invoke skill X" guidance
**Symptoms:** early dev-guide.md notes said "invoke skill X when doing Y" at story level, with no verification mechanism.
**Root Cause:** guidance was written at the wrong granularity (story-level, not task-level) and had no Definition-of-Done tie-in.
**Fix:** added a task-level trigger table + PR-description Definition of Done requirement (dev-guide.md §2.1).
**Prevention:** [rules/pull-requests.md](../rules/pull-requests.md) states the DoD requirement explicitly.
**Related:** none (design-phase correction, no code existed yet).
