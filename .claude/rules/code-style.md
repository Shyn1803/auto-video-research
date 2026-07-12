# Rule: Code Style

See [context/coding-style.md](../context/coding-style.md) for the full summary; this file is the enforceable checklist version.

- Python: ruff format/lint clean, mypy strict on new `app/` code, `select()` not `.query()`, async by default.
- No business logic in FastAPI routers — router calls a service function, service contains the logic.
- TypeScript: eslint + prettier clean, no `any` without a comment justifying it.
- Never hand-write a TS interface duplicating a backend Pydantic model — regenerate via `make gen-api-client`.
- No adapter reads `os.environ`/`process.env` directly — config arrives via `ProviderSettings` (backend) or equivalent typed config object.
- No inline magic strings for layout class names, provider names, or status values — use the shared enum/constant matching `docs/glossary.md`.
