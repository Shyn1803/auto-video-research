# Rule: Configuration & Environment Variables

Full reference: `docs/CONFIGURATION.md` — this file states the rules, not the values (values live in exactly one place to avoid drift).

- Every capability is env-driven via a `*_CHAIN` variable (`LLM_CHAIN_CHEAP`, `TTS_CHAIN`, `SEARCH_CHAIN`, `IMAGE_GEN_CHAIN`, `PUBLISH_PLATFORMS`, `STORAGE_PROVIDER`...). A new provider is activated by adding it to the chain + supplying its key — never by a code change.
- Provider availability = in chain AND (key present OR local service reachable) AND (free OR `ALLOW_PAID=true`).
- Config precedence: `env` > `api_keys` table (DB, via Admin UI) > default. Env is for automated deploy; DB is for Admin runtime changes without restart.
- `.env.example` must stay a complete superset of every variable in `docs/CONFIGURATION.md` — no undocumented env var in code, no documented var missing from the example file.
- `ALLOW_PAID` and `DAILY_COST_CAP` default to the safest setting (`false` / `0`) — never flip these defaults without explicit user instruction.
- On startup, the system must log/expose which provider is active per capability and why others were excluded (missing key / health fail / paid blocked) — this is a design requirement (SRS FR-21 rule 4), not optional observability.
