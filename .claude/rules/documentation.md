# Rule: Documentation

- Any change to `app/schemas/scene.py`, `app/events/`, API request/response schema, a DB table, or an env var is a "đổi contract" change (dev-guide.md §5) and must update the matching `docs/` spec **in the same PR**, plus a **Contract changes** note in the PR description.
- Never restate a fact that already lives in `docs/` inside `.claude/` — link to it. `.claude/context/` is a summary + pointer layer, not a fork.
- `docs/glossary.md` is the single source of terminology — a new domain term gets added there, not invented ad hoc in a docstring or comment.
- `docs/README.md`'s reading-order table gets updated whenever a new doc file is added to `docs/`.
- Comments in code explain *why*, not *what* — see this project's own default (no comment unless it captures a non-obvious constraint, workaround, or invariant).
