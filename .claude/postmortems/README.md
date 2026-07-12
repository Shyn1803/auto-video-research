# Postmortems — Policy & Index

**Policy:** whenever a bug is fixed (once code exists) or a design/documentation defect with a real root cause is found, propose a postmortem using [templates/postmortem.md](../templates/postmortem.md). Not every fix needs one — reserve it for defects that reveal something generalizable (a missing rule, a recurring class of mistake, a gap in the review process), not one-off typos.

**Index**

| Date | Title | Risk |
|---|---|---|
| 2026-07 | [PascalCase layout-name drift](2026-07-pascalcase-layout-drift.md) | Medium — architecture-doc consistency |
| 2026-07 | [renderMedia() merge ambiguity](2026-07-rendermedia-merge-ambiguity.md) | Medium — would have caused a render-worker design bug if uncaught |

Both entries below happened during the documentation/design phase (pre-code) — they're about design artifacts, not runtime bugs, since no code exists yet. Once Phase 1 code ships, expect this index to fill with real runtime postmortems.
